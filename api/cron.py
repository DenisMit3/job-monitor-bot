"""
Vercel Cron Job - Парсинг каналов и отправка дайджеста
"""
import json
import asyncio
import os
import re
import hashlib
import aiohttp
import asyncpg
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from aiogram import Bot

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5171260626"))

print(f"[CRON DEBUG] BOT_TOKEN exists: {bool(BOT_TOKEN)}, DATABASE_URL exists: {bool(DATABASE_URL)}")

# Список каналов для парсинга
CHANNELS = [
    "devjobs", "fordev", "freelancetaverna", "remote_it", "web_work",
    "frontend_jobs", "backend_jobs_ru", "nodejs_jobs", "react_jobs",
    "python_jobs_ru", "fullstack_jobs", "geekjob", "javascript_jobs",
    "vuejs_jobs", "php_jobs", "telegram_bot_dev", "freelance_ru"
]

# Ключевые слова
KEYWORDS = {
    "web": ["сайт", "веб", "web", "frontend", "backend", "react", "vue", "node", "php", "laravel", "wordpress", "django", "html", "css", "javascript", "typescript", "верстка", "landing"],
    "bots": ["бот", "bot", "telegram", "телеграм", "discord", "aiogram", "pyrogram", "автоматизация"],
    "fullstack": ["fullstack", "фулстек", "разработчик", "developer", "программист"],
}

STOP_WORDS = ["менеджер", "manager", "hr", "recruiter", "продажи", "sales", "маркетолог"]

SIMILARITY_THRESHOLD = 0.7


async def parse_channel(session: aiohttp.ClientSession, channel: str):
    """Парсинг одного канала"""
    url = f"https://t.me/s/{channel}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
            return parse_html(html, channel)
    except Exception as e:
        print(f"[CRON] Error parsing {channel}: {e}")
        return []


def parse_html(html: str, channel: str):
    """Парсинг HTML"""
    messages = []
    text_pattern = r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>'
    post_pattern = r'data-post="([^"]+)"'
    
    posts = re.findall(post_pattern, html)
    texts = re.findall(text_pattern, html, re.DOTALL)
    
    for i, post_id in enumerate(posts[-15:]):
        if i < len(texts):
            text = clean_html(texts[i])
            if text and len(text) > 50:
                message_id = int(post_id.split('/')[-1]) if '/' in post_id else 0
                messages.append({
                    "message_id": message_id,
                    "channel": channel,
                    "text": text,
                    "url": f"https://t.me/{post_id}"
                })
    return messages


def clean_html(html: str) -> str:
    """Очистка HTML"""
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_job_posting(text: str):
    """Проверка на вакансию"""
    text_lower = text.lower()
    
    for stop in STOP_WORDS:
        if stop.lower() in text_lower:
            return False, []
    
    found = []
    for cat, words in KEYWORDS.items():
        for w in words:
            if w.lower() in text_lower:
                found.append(cat)
                break
    
    if not found:
        return False, []
    
    indicators = ["ищем", "ищу", "требуется", "нужен", "вакансия", "работа", "оплата", "бюджет", "удалённо", "remote", "фриланс", "проект", "заказ"]
    has_indicator = any(ind in text_lower for ind in indicators)
    
    return has_indicator, list(set(found))


def calc_hash(text: str) -> str:
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    normalized = re.sub(r'\d+', '', normalized)
    return hashlib.md5(normalized.encode()).hexdigest()


def is_similar(text1: str, text2: str) -> bool:
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() > SIMILARITY_THRESHOLD


async def run_parsing():
    """Основная функция парсинга"""
    print("[CRON] Starting parsing...")
    
    if not DATABASE_URL:
        return {"error": "DATABASE_URL not set", "parsed": 0, "new": 0}
    
    if not BOT_TOKEN:
        return {"error": "BOT_TOKEN not set", "parsed": 0, "new": 0}
    
    # Парсим каналы
    all_jobs = []
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for i in range(0, len(CHANNELS), 3):
            batch = CHANNELS[i:i+3]
            tasks = [parse_channel(session, ch) for ch in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    for msg in result:
                        is_job, keywords = is_job_posting(msg["text"])
                        if is_job:
                            msg["keywords"] = keywords
                            msg["text_hash"] = calc_hash(msg["text"])
                            all_jobs.append(msg)
            
            await asyncio.sleep(0.5)
    
    print(f"[CRON] Parsed {len(all_jobs)} potential jobs")
    
    if not all_jobs:
        return {"parsed": 0, "new": 0, "status": "no jobs found"}
    
    # Работа с БД
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Создаём таблицу если нет
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                message_id BIGINT,
                channel VARCHAR(255),
                text TEXT,
                text_hash VARCHAR(64),
                url VARCHAR(500),
                keywords TEXT[],
                created_at TIMESTAMP DEFAULT NOW(),
                sent BOOLEAN DEFAULT FALSE,
                UNIQUE(channel, message_id)
            )
        """)
        
        # Получаем существующие хеши
        existing = await conn.fetch("SELECT text_hash, text FROM jobs WHERE created_at > NOW() - INTERVAL '48 hours'")
        existing_hashes = {r['text_hash'] for r in existing}
        existing_texts = [r['text'] for r in existing]
        
        # Фильтруем и добавляем новые
        new_jobs = []
        for job in all_jobs:
            if job["text_hash"] in existing_hashes:
                continue
            
            if any(is_similar(job["text"], t) for t in existing_texts[:50]):
                continue
            
            try:
                result = await conn.fetchrow("""
                    INSERT INTO jobs (message_id, channel, text, text_hash, url, keywords)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (channel, message_id) DO NOTHING
                    RETURNING id
                """, job["message_id"], job["channel"], job["text"], job["text_hash"], job["url"], job["keywords"])
                
                if result:
                    job["id"] = result["id"]
                    new_jobs.append(job)
                    existing_hashes.add(job["text_hash"])
            except Exception as e:
                print(f"[CRON] DB insert error: {e}")
        
        await conn.close()
        
        print(f"[CRON] New jobs: {len(new_jobs)}")
        
        # Отправляем в Telegram
        if new_jobs:
            bot = Bot(token=BOT_TOKEN)
            
            # Отправляем заголовок
            header = f"📋 <b>Найдено {len(new_jobs)} новых вакансий</b>\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
            await bot.send_message(ADMIN_ID, header, parse_mode="HTML")
            
            # Отправляем вакансии (макс 10)
            for job in new_jobs[:10]:
                text = job["text"][:600] + "..." if len(job["text"]) > 600 else job["text"]
                msg = f"📌 {text}\n\n🏷 {', '.join(job['keywords'])}\n📢 <a href=\"{job['url']}\">Источник</a>"
                try:
                    await bot.send_message(ADMIN_ID, msg, parse_mode="HTML")
                except Exception as e:
                    print(f"[CRON] Send error: {e}")
            
            if len(new_jobs) > 10:
                await bot.send_message(ADMIN_ID, f"...и ещё {len(new_jobs) - 10} вакансий")
            
            await bot.session.close()
        
        return {"parsed": len(all_jobs), "new": len(new_jobs), "status": "success"}
    
    except Exception as e:
        print(f"[CRON] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "parsed": len(all_jobs), "new": 0}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("[CRON] GET request received")
        try:
            result = asyncio.run(run_parsing())
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            print(f"[CRON] Handler error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e), "parsed": 0, "new": 0}).encode())
    
    def do_POST(self):
        self.do_GET()
