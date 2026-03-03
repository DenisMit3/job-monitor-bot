"""
Vercel Serverless Function - Webhook для Telegram бота
"""
import json
import asyncio

from aiogram.types import Update
from http.server import BaseHTTPRequestHandler

from src.config import BOT_TOKEN, DATABASE_URL
from src.database import Database
from src.bot import create_bot, set_database


db: Database | None = None


async def process_update(update_data: dict):
    """Обработка входящего обновления через общий bot/dispatcher."""
    global db

    print(f"[DEBUG] process_update, keys: {list(update_data.keys())}")

    if not BOT_TOKEN:
        print("[DEBUG] ERROR: BOT_TOKEN is None!")
        return

    # Инициализируем базу данных один раз на «холодный старт»
    if DATABASE_URL and db is None:
        db = Database(DATABASE_URL)
        await db.init_tables()
        set_database(db)
        print("[DEBUG] Database initialized in webhook")

    bot, dp = create_bot()

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
