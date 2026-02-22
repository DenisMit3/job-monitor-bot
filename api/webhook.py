"""
Vercel Serverless Function - Webhook для Telegram бота
"""
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from aiogram import Bot
from aiogram.types import Update

import sys
sys.path.insert(0, '..')

from src.config import BOT_TOKEN, DATABASE_URL
from src.database import Database
from src.bot import create_bot, set_database, router


# Глобальные объекты
bot = Bot(token=BOT_TOKEN)
db = None


async def process_update(update_data: dict):
    """Обработка входящего обновления"""
    global db
    
    if DATABASE_URL:
        db = Database(DATABASE_URL)
        await db.init_tables()
        set_database(db)
    
    _, dp = create_bot()
    
    update = Update(**update_data)
    await dp.feed_update(bot, update)
    
    if db:
        await db.close()


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
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Bot webhook is active"}).encode())
