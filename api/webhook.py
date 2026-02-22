"""
Vercel Serverless Function - Webhook для Telegram бота
"""
import json
import asyncio
import os
import sys

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Update, Message
from aiogram.filters import Command

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "8566523315:AAGso2hEaVPX-kvjR40VDZvwk011vfRaUP0")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5171260626"))

# Создаём роутер
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
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
        "Бот автоматически парсит IT-каналы каждый день в 12:00 МСК "
        "и присылает дайджест новых вакансий.\n\n"
        "🔍 <b>Фильтрация:</b>\n"
        "- Веб-разработка (React, Vue, Node, PHP...)\n"
        "- Telegram боты\n"
        "- Fullstack разработка\n"
        "- DevOps, Mobile, ML/AI\n\n"
        "🔄 <b>Дедупликация:</b>\n"
        "Похожие вакансии из разных каналов объединяются.",
        parse_mode="HTML"
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📊 Статистика пока недоступна - база данных инициализируется")

@router.message(Command("digest"))
async def cmd_digest(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📋 Используйте /parse для запуска парсинга вакансий")

@router.message(Command("channels"))
async def cmd_channels(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    channels = [
        "devjobs", "fordev", "freelancetaverna", "remote_it", 
        "web_work", "frontend_jobs", "backend_jobs_ru", "nodejs_jobs",
        "react_jobs", "python_jobs_ru", "fullstack_jobs", "geekjob"
    ]
    
    channels_list = "\n".join([f"• @{ch}" for ch in channels])
    
    await message.answer(
        f"📢 <b>Каналы для мониторинга</b>\n\n{channels_list}\n\n...и другие (50+ каналов)",
        parse_mode="HTML"
    )

@router.message(Command("parse"))
async def cmd_parse(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer("🔄 Запускаю парсинг... Это может занять 1-2 минуты.")
    
    # Вызываем cron endpoint
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            base_url = os.getenv("VERCEL_URL", "botmonitorinaraboty.vercel.app")
            url = f"https://{base_url}/api/cron"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                result = await resp.json()
                await message.answer(
                    f"✅ Парсинг завершён!\n\n"
                    f"📊 Обработано: {result.get('parsed', 0)}\n"
                    f"🆕 Новых: {result.get('new', 0)}"
                )
    except Exception as e:
        await message.answer(f"❌ Ошибка парсинга: {str(e)[:200]}")

@router.message()
async def any_message(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Используйте /help для списка команд")


async def process_update(update_data: dict):
    """Обработка входящего обновления"""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    try:
        update = Update(**update_data)
        await dp.feed_update(bot, update)
    finally:
        await bot.session.close()


class handler:
    def __init__(self, request):
        self.request = request
    
    async def handle_post(self):
        try:
            body = await self.request.body()
            update_data = json.loads(body.decode('utf-8'))
            await process_update(update_data)
            return {"statusCode": 200, "body": json.dumps({"ok": True})}
        except Exception as e:
            print(f"Webhook error: {e}")
            return {"statusCode": 200, "body": json.dumps({"ok": True, "error": str(e)})}
    
    async def handle_get(self):
        return {"statusCode": 200, "body": json.dumps({"status": "Bot webhook is active"})}


# Vercel handler
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            update_data = json.loads(body.decode('utf-8'))
            asyncio.run(process_update(update_data))
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        except Exception as e:
            print(f"Webhook error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Bot webhook is active"}).encode())
