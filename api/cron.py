"""
Vercel Cron Job - Парсинг каналов и отправка дайджеста
Запускается каждый час
"""
import json
import asyncio
from http.server import BaseHTTPRequestHandler

import sys
sys.path.insert(0, '..')

from src.config import BOT_TOKEN, DATABASE_URL, ADMIN_ID
from src.database import Database
from src.parser import TelegramParser
from src.bot import send_digest_to_admin

from aiogram import Bot


async def run_parsing():
    """Запуск парсинга и отправка дайджеста"""
    if not DATABASE_URL:
        return {"error": "DATABASE_URL not configured"}
    
    db = Database(DATABASE_URL)
    await db.init_tables()
    
    parser = TelegramParser()
    
    try:
        # Парсим все каналы
        jobs = await parser.parse_all_channels()
        
        # Получаем существующие хеши для дедупликации
        existing = await db.get_similar_jobs(hours=48)
        existing_hashes = {j["text_hash"] for j in existing}
        existing_texts = [j["text"] for j in existing]
        
        # Фильтруем дубликаты
        new_jobs = []
        for job in jobs:
            # Проверяем точный дубликат
            if job["text_hash"] in existing_hashes:
                continue
            
            # Проверяем схожесть
            if parser.is_similar_to_existing(job["text"], existing_texts):
                continue
            
            # Добавляем в базу
            job_id = await db.add_job(
                message_id=job["message_id"],
                channel=job["channel"],
                text=job["text"],
                text_hash=job["text_hash"],
                url=job["url"],
                keywords=job["keywords"]
            )
            
            if job_id:
                job["id"] = job_id
                new_jobs.append(job)
                existing_hashes.add(job["text_hash"])
                existing_texts.append(job["text"])
        
        # Отправляем дайджест если есть новые вакансии
        if new_jobs:
            bot = Bot(token=BOT_TOKEN)
            await send_digest_to_admin(bot, new_jobs)
            
            # Отмечаем как отправленные
            job_ids = [j["id"] for j in new_jobs]
            await db.mark_jobs_sent(job_ids)
            
            await bot.session.close()
        
        return {
            "parsed": len(jobs),
            "new": len(new_jobs),
            "status": "success"
        }
    
    except Exception as e:
        return {"error": str(e)}
    
    finally:
        await parser.close()
        await db.close()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Проверяем авторизацию Vercel Cron
        auth_header = self.headers.get('Authorization')
        
        try:
            result = asyncio.run(run_parsing())
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_POST(self):
        # Также поддерживаем POST для ручного запуска
        self.do_GET()
