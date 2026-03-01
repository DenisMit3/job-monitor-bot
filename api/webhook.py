"""
Vercel Serverless Function - Webhook для Telegram бота
"""
import json
import asyncio
import os

import asyncpg
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message, Update
from http.server import BaseHTTPRequestHandler

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5171260626"))
DATABASE_URL = os.getenv("DATABASE_URL")
CRON_ENDPOINT = os.getenv("CRON_ENDPOINT", "https://botmonitorinaraboty.vercel.app/api/cron")
ALLOW_ALL_USERS = os.getenv("ALLOW_ALL_USERS", "1") == "1"

print(f"[DEBUG] BOT_TOKEN exists: {bool(BOT_TOKEN)}, ADMIN_ID: {ADMIN_ID}")


async def register_recipient(user_id: int):
    """Сохраняем пользователя как получателя уведомлений от cron."""
    if not DATABASE_URL:
        return

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
        await conn.execute(
            """
            INSERT INTO bot_recipients (user_id, active, updated_at)
            VALUES ($1, TRUE, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET active = TRUE, updated_at = NOW()
            """,
            user_id,
        )
    except Exception as exc:
        print(f"[DEBUG] register_recipient error: {exc}")
    finally:
        if conn:
            await conn.close()


def is_allowed(user_id: int) -> bool:
    return ALLOW_ALL_USERS or user_id == ADMIN_ID


def create_router() -> Router:
    """Создаём новый роутер для каждого запроса"""
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message):
        print(f"[DEBUG] cmd_start: user_id={message.from_user.id}")
        if not is_allowed(message.from_user.id):
            await message.answer("⛔ Бот доступен только администратору")
            return

        await register_recipient(message.from_user.id)
        await message.answer(
            "👋 <b>Job Monitor Bot</b>\n\n"
            "Бот для мониторинга IT-вакансий из Telegram каналов.\n\n"
            "📌 <b>Команды:</b>\n"
            "/parse - Запустить парсинг вручную\n"
            "/channels - Список каналов\n"
            "/help - Помощь\n\n"
            f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>",
            parse_mode="HTML",
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        if not is_allowed(message.from_user.id):
            return
        await register_recipient(message.from_user.id)
        await message.answer(
            "📖 <b>Справка</b>\n\n"
            "1) Нажмите /parse, чтобы сразу получить вакансии.\n"
            "2) Если используете DATABASE_URL — уведомления будут приходить автоматически из cron.",
            parse_mode="HTML",
        )

    @router.message(Command("channels"))
    async def cmd_channels(message: Message):
        if not is_allowed(message.from_user.id):
            return
        await register_recipient(message.from_user.id)
        await message.answer(
            "📢 <b>Каналы:</b>\n• @devjobs\n• @fordev\n• @freelancetaverna\n...и 100+ других",
            parse_mode="HTML",
        )

    @router.message(Command("parse"))
    async def cmd_parse(message: Message):
        if not is_allowed(message.from_user.id):
            return

        await register_recipient(message.from_user.id)
        await message.answer("🔄 Запускаю парсинг...")

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                trigger_url = f"{CRON_ENDPOINT}?recipient_id={message.from_user.id}"
                async with session.get(trigger_url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    result = await resp.json()
                    await message.answer(
                        "✅ <b>Парсинг завершён</b>\n\n"
                        f"📡 Источников: {result.get('sources', 'n/a')}\n"
                        f"🔍 Отфильтровано: {result.get('filtered', result.get('parsed', 0))}\n"
                        f"🆕 Новых: {result.get('new', 0)}\n"
                        f"📤 Отправлено карточек: {result.get('sent', 0)}\n"
                        f"👥 Получателей: {result.get('recipients', 1)}\n"
                        f"⚠️ Ошибки парсера: {result.get('parser_errors', {})}",
                        parse_mode="HTML",
                    )
                    if result.get("new", 0) == 0:
                        await message.answer(
                            "ℹ️ Новых вакансий нет — это значит, что найденные сообщения похожи на уже отправленные, "
                            "или в текущем запуске не было новых релевантных постов."
                        )
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:200]}")

    @router.message()
    async def any_message(message: Message):
        if not is_allowed(message.from_user.id):
            return
        await register_recipient(message.from_user.id)
        await message.answer("Напишите /parse чтобы получить вакансии прямо сейчас")

    return router


async def process_update(update_data: dict):
    """Обработка входящего обновления"""
    print(f"[DEBUG] process_update, keys: {list(update_data.keys())}")

    if not BOT_TOKEN:
        print("[DEBUG] ERROR: BOT_TOKEN is None!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    router = create_router()
    dp.include_router(router)

    try:
        update = Update(**update_data)
        print(f"[DEBUG] Update id={update.update_id}")
        await dp.feed_update(bot, update)
        print("[DEBUG] feed_update done")
    except Exception as e:
        print(f"[DEBUG] ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await bot.session.close()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        print("[DEBUG] POST received")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            update_data = json.loads(body.decode("utf-8"))
            print(f"[DEBUG] has_message: {'message' in update_data}")

            asyncio.run(process_update(update_data))

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception as e:
            print(f"[DEBUG] EXCEPTION: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"active"}')
