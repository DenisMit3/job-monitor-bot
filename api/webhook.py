"""
Vercel Serverless Function - Webhook для Telegram бота
"""
import json
import asyncio
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update, Message
from aiogram.filters import Command
from http.server import BaseHTTPRequestHandler

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5171260626"))

print(f"[DEBUG] BOT_TOKEN exists: {bool(BOT_TOKEN)}, ADMIN_ID: {ADMIN_ID}")


def create_router() -> Router:
    """Создаём новый роутер для каждого запроса"""
    router = Router()
    
    @router.message(Command("start"))
    async def cmd_start(message: Message):
        print(f"[DEBUG] cmd_start: user_id={message.from_user.id}")
        if message.from_user.id != ADMIN_ID:
            await message.answer("⛔ Бот доступен только администратору")
            return
        
        await message.answer(
            "👋 <b>Job Monitor Bot</b>\n\n"
            "Бот для мониторинга IT-вакансий из Telegram каналов.\n\n"
            "📌 <b>Команды:</b>\n"
            "/digest - Получить текущий дайджест\n"
            "/stats - Статистика\n"
            "/export - Экспорт в CSV\n"
            "/channels - Список каналов\n"
            "/parse - Запустить парсинг вручную\n"
            "/help - Помощь",
            parse_mode="HTML"
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer(
            "📖 <b>Справка</b>\n\n"
            "Бот автоматически парсит IT-каналы каждый день в 12:00 МСК.",
            parse_mode="HTML"
        )

    @router.message(Command("stats"))
    async def cmd_stats(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer("📊 Статистика: функция в разработке")

    @router.message(Command("digest"))
    async def cmd_digest(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer("📋 Используйте /parse для запуска парсинга")

    @router.message(Command("channels"))
    async def cmd_channels(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer(
            "📢 <b>Каналы:</b>\n• @devjobs\n• @fordev\n• @freelancetaverna\n...и 50+ других",
            parse_mode="HTML"
        )

    @router.message(Command("parse"))
    async def cmd_parse(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer("🔄 Запускаю парсинг...")
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = "https://botmonitorinaraboty.vercel.app/api/cron"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    result = await resp.json()
                    await message.answer(
                        f"✅ Парсинг завершён!\n\n"
                        f"📊 Обработано: {result.get('parsed', 0)}\n"
                        f"🆕 Новых: {result.get('new', 0)}"
                    )
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)[:200]}")

    @router.message()
    async def any_message(message: Message):
        if message.from_user.id != ADMIN_ID:
            return
        await message.answer("Используйте /help для списка команд")
    
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
        print(f"[DEBUG] POST received")
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            update_data = json.loads(body.decode('utf-8'))
            print(f"[DEBUG] has_message: {'message' in update_data}")
            
            asyncio.run(process_update(update_data))
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception as e:
            print(f"[DEBUG] EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"active"}')
