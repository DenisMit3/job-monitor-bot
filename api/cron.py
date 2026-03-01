"""
Vercel Cron Job - Парсинг каналов и отправка дайджеста
"""
import json
import asyncio
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import asyncpg
from aiogram import Bot

from src.config import BOT_TOKEN, DATABASE_URL, ADMIN_ID, SIMILARITY_THRESHOLD, CHANNELS
from src.database import Database
from src.parser import TelegramParser


async def get_recipients() -> list[int]:
    """Получаем список получателей уведомлений."""
    recipients = [ADMIN_ID]

    if not DATABASE_URL:
        return recipients

    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_recipients (
                user_id BIGINT PRIMARY KEY,
                active BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        rows = await conn.fetch(
            "SELECT user_id FROM bot_recipients WHERE active = TRUE ORDER BY updated_at DESC LIMIT 20"
        )
        ids = [int(r["user_id"]) for r in rows]
        if ids:
            recipients = ids
    except Exception as exc:
        print(f"[CRON] get_recipients error: {exc}")
    finally:
        if conn:
            await conn.close()

    # Удаляем дубликаты, сохраняем порядок
    unique = []
    for uid in recipients:
        if uid not in unique:
            unique.append(uid)
    return unique


async def notify_all(bot: Bot, recipients: list[int], text: str, parse_mode: str | None = None):
    for uid in recipients:
        try:
            await bot.send_message(uid, text, parse_mode=parse_mode)
        except Exception as exc:
            print(f"[CRON] send to {uid} failed: {exc}")


async def run_parsing(force_recipient_id: int | None = None):
    """Основная функция парсинга"""
    print("[CRON] Starting parsing...")

    if not BOT_TOKEN:
        return {"error": "BOT_TOKEN not set", "parsed": 0, "new": 0}

    parser = TelegramParser()
    db = Database(DATABASE_URL) if DATABASE_URL else None
    bot = None
    parse_run_id = None

    try:
        recipients = await get_recipients()
        if force_recipient_id and force_recipient_id not in recipients:
            recipients.insert(0, force_recipient_id)
        print(f"[CRON] Recipients: {recipients}")

        if db:
            await db.init_tables()
            print("[CRON] DB mode enabled")
        else:
            print("[CRON] DB mode disabled (DATABASE_URL missing)")

        total_sources = len(CHANNELS)
        if db:
            parse_run_id = await db.create_parse_run(
                sources_total=total_sources,
                recipients_total=len(recipients),
            )
        all_jobs = await parser.parse_all_channels(batch_size=8, per_channel_limit=30)
        total_filtered = len(all_jobs)
        print(f"[CRON] Filtered jobs: {total_filtered}")

        bot = Bot(token=BOT_TOKEN)

        if not all_jobs:
            await notify_all(bot, recipients, "📭 Подходящих заказов/вакансий не найдено")
            if db and parse_run_id:
                await db.finish_parse_run(
                    run_id=parse_run_id,
                    status="no_jobs",
                    filtered_total=0,
                    new_total=0,
                    sent_total=0,
                    parser_errors=parser.error_stats,
                )
            return {
                "status": "no jobs found",
                "sources": total_sources,
                "parsed": 0,
                "filtered": 0,
                "new": 0,
                "sent": 0,
                "recipients": len(recipients),
                "parser_errors": parser.error_stats,
            }

        new_jobs = []
        saved_job_ids = []

        if db:
            existing = await db.get_similar_jobs(hours=48)
            existing_hashes = {item["text_hash"] for item in existing}
            existing_texts = [item["text"] for item in existing]

            for job in all_jobs:
                if job["text_hash"] in existing_hashes:
                    continue

                is_similar = any(
                    parser.calculate_similarity(job["text"], old_text) > SIMILARITY_THRESHOLD
                    for old_text in existing_texts[:1500]
                )
                if is_similar:
                    continue

                job_id = await db.add_job(
                    message_id=job["message_id"],
                    channel=job["channel"],
                    text=job["text"],
                    text_hash=job["text_hash"],
                    url=job["url"],
                    keywords=job.get("keywords", []),
                    budget_min=job.get("budget_min"),
                    budget_max=job.get("budget_max"),
                    currency=job.get("currency"),
                    contact_raw=job.get("contact_raw"),
                    is_remote=job.get("is_remote"),
                    seniority=job.get("seniority"),
                    match_score=job.get("match_score"),
                )
                if job_id:
                    job["id"] = job_id
                    new_jobs.append(job)
                    saved_job_ids.append(job_id)
                    existing_hashes.add(job["text_hash"])
                    existing_texts.append(job["text"])
        else:
            seen_hashes = set()
            kept_texts = []
            for job in all_jobs:
                if job["text_hash"] in seen_hashes:
                    continue
                is_similar = any(
                    parser.calculate_similarity(job["text"], old_text) > SIMILARITY_THRESHOLD
                    for old_text in kept_texts[:1500]
                )
                if is_similar:
                    continue
                new_jobs.append(job)
                seen_hashes.add(job["text_hash"])
                kept_texts.append(job["text"])

        header = (
            "📋 <b>Парсинг завершён</b>\n"
            f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔍 После фильтрации: {total_filtered}\n"
            f"🆕 Новых: {len(new_jobs)}"
        )
        await notify_all(bot, recipients, header, parse_mode="HTML")

        jobs_to_send = new_jobs[:10] if new_jobs else all_jobs[:10]
        sent_count = 0

        for job in jobs_to_send:
            text = job["text"][:700] + "..." if len(job["text"]) > 700 else job["text"]
            msg = (
                f"📌 {text}\n\n"
                f"🏷 {', '.join(job.get('keywords', []))}\n"
                f"📢 <a href=\"{job['url']}\">Источник</a>"
            )
            await notify_all(bot, recipients, msg, parse_mode="HTML")
            sent_count += 1

        if db and parse_run_id:
            await db.add_jobs_to_parse_run(parse_run_id, saved_job_ids)
            await db.finish_parse_run(
                run_id=parse_run_id,
                status="success",
                filtered_total=total_filtered,
                new_total=len(new_jobs),
                sent_total=sent_count,
                parser_errors=parser.error_stats,
            )

        return {
            "status": "success",
            "sources": total_sources,
            "parsed": total_filtered,
            "filtered": total_filtered,
            "new": len(new_jobs),
            "sent": sent_count,
            "recipients": len(recipients),
            "parser_errors": parser.error_stats,
        }

    except Exception as e:
        print(f"[CRON] Error: {e}")
        if db and parse_run_id:
            try:
                await db.finish_parse_run(
                    run_id=parse_run_id,
                    status="error",
                    filtered_total=0,
                    new_total=0,
                    sent_total=0,
                    parser_errors=parser.error_stats,
                    error_text=str(e),
                )
            except Exception as run_exc:
                print(f"[CRON] parse_run finalize error: {run_exc}")
        return {"error": str(e), "status": "error", "parsed": 0, "new": 0}

    finally:
        try:
            await parser.close()
        except Exception:
            pass
        try:
            if bot:
                await bot.session.close()
        except Exception:
            pass
        try:
            if db:
                await db.close()
        except Exception:
            pass


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            recipient_raw = qs.get("recipient_id", [None])[0]
            force_recipient_id = int(recipient_raw) if recipient_raw and recipient_raw.isdigit() else None
            result = asyncio.run(run_parsing(force_recipient_id=force_recipient_id))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e), "parsed": 0, "new": 0}).encode())

    def do_POST(self):
        self.do_GET()
