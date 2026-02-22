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

print(f"[DEBUG H2] BOT_TOKEN exists: {bool(BOT_TOKEN)}, ADMIN_ID: {ADMIN_ID}")

# Создаём роутер
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    print(f"[DEBUG H2] cmd_start: user_id={message.from_user.id}, admin_id={ADMIN_ID}")
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
    print("[DEBUG H4] cmd_start: message sent successfully")

@router.message(Command("help"))
async def cmd_help(message: Message):
    print(f"[DEBUG] cmd_help called by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "📖 <b>Справка</b>\n\n"
        "Бот автоматически парсит IT-каналы каждый день в 12:00 МСК.",
        parse_mode="HTML"
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    print(f"[DEBUG] cmd_stats called by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📊 Статистика: функция в разработке")

@router.message(Command("digest"))
async def cmd_digest(message: Message):
    print(f"[DEBUG] cmd_digest called by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📋 Используйте /parse для запуска парсинга")

@router.message(Command("channels"))
async def cmd_channels(message: Message):
    print(f"[DEBUG] cmd_channels called by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "📢 <b>Каналы:</b>\n• @devjobs\n• @fordev\n• @freelancetaverna\n...и 50+ других",
        parse_mode="HTML"
    )

@router.message(Command("parse"))
async def cmd_parse(message: Message):
    print(f"[DEBUG] cmd_parse called by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔄 Парсинг временно недоступен. Функция в разработке.")

@router.message()
async def any_message(message: Message):
    print(f"[DEBUG] any_message called by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Используйте /help для списка команд")


async def process_update(update_data: dict):
    """Обработка входящего обновления"""
    print(f"[DEBUG H3] process_update started, keys: {list(update_data.keys())}")
    
    if not BOT_TOKEN:
        print("[DEBUG H1] ERROR: BOT_TOKEN is None!")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        update = Update(**update_data)
        print(f"[DEBUG H3] Update parsed: id={update.update_id}")
        await dp.feed_update(bot, update)
        print("[DEBUG H4] feed_update completed")
    except Exception as e:
        print(f"[DEBUG H1] ERROR in process_update: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"[DEBUG H5] POST received, path: {self.path}")
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            update_data = json.loads(body.decode('utf-8'))
            print(f"[DEBUG H5] Body parsed, has_message: {'message' in update_data}")
            
            asyncio.run(process_update(update_data))
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            print("[DEBUG] Response sent 200")
        except Exception as e:
            print(f"[DEBUG H1] EXCEPTION in do_POST: {type(e).__name__}: {e}")
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
