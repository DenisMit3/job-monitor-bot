"""
Vercel Cron Job - Парсинг каналов и отправка дайджеста
"""
import json
import asyncio
import os
import re
import hashlib
import aiohttp
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from aiogram import Bot

from src.database import Database
from src.config import SIMILARITY_THRESHOLD

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5171260626"))

print(f"[CRON DEBUG] BOT_TOKEN exists: {bool(BOT_TOKEN)}, DATABASE_URL exists: {bool(DATABASE_URL)}")

# Список каналов/чатов для парсинга (чаты с заказами и просьбами)
CHANNELS = [
    # Фриланс биржи и заказы
    "freelancetaverna",
    "fl_ru_chat", 
    "freelanceru",
    "zakazy_freelance",
    # Чаты разработчиков (где просят помощь)
    "webdev_ru",
    "frontend_ru", 
    "js_ru",
    "python_ru",
    "php_ru",
    # Telegram боты
    "botoid",
    # Заказы на разработку
    "it_orders",
    "dev_orders",
]

# Ключевые слова - что ищем
KEYWORDS = {
    "web": ["сайт", "веб", "web", "лендинг", "landing", "верстка", "страниц", "wordpress", "интернет-магазин"],
    "bots": ["бот", "bot", "телеграм", "telegram", "discord", "автоматизац", "парсер", "parser"],
    "dev": ["скрипт", "программ", "приложени", "доработ", "исправ", "функци", "api", "интеграц"],
}

STOP_WORDS = [
    "менеджер", "manager", "hr", "recruiter", "продажи", "sales", "маркетолог",
    # Игровая разработка - исключаем
    "игр", "game", "gaming", "unity", "unreal", "godot", "gamedev", "геймдев",
    "3d модел", "3d artist", "левел дизайн", "level design", "игровой движок",
    # Исключаем вакансии (ищем заказы, а не работу в штат)
    "вакансия", "vacancy", "в штат", "офис", "full-time", "трудоустройство"
]

# Индикаторы просьб о помощи/заказов
REQUEST_INDICATORS = [
    # Просьбы
    "помогите", "помоги", "нужна помощь", "кто может", "кто сможет", 
    "кто возьмется", "кто возьмётся", "посоветуйте", "подскажите",
    # Заказы
    "нужен", "нужна", "нужно", "ищу", "ищем", "требуется",
    "сделать", "сделайте", "создать", "разработать", "написать",
    # Доработка
    "доработать", "доработка", "исправить", "починить", "пофиксить",
    "добавить функци", "изменить", "переделать", "улучшить",
    # Оплата
    "оплачу", "заплачу", "бюджет", "за вознаграждение", "платно", "$", "₽", "руб"
]


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


def is_help_request(text: str):
    """Проверка на запрос помощи/заказ"""
    text_lower = text.lower()
    
    # Проверяем стоп-слова
    for stop in STOP_WORDS:
        if stop.lower() in text_lower:
            return False, []
    
    # Ищем ключевые слова (что нужно сделать)
    found = []
    for cat, words in KEYWORDS.items():
        for w in words:
            if w.lower() in text_lower:
                found.append(cat)
                break
    
    if not found:
        return False, []
    
    # Проверяем индикаторы просьбы/заказа
    has_request = any(ind in text_lower for ind in REQUEST_INDICATORS)
    
    return has_request, list(set(found))


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
    all_results = []
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for i in range(0, len(CHANNELS), 3):
            batch = CHANNELS[i:i+3]
            tasks = [parse_channel(session, ch) for ch in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(results)
            
            for result in results:
                if isinstance(result, list):
                    for msg in result:
                        is_request, keywords = is_help_request(msg["text"])
                        if is_request:
                            msg["keywords"] = keywords
                            msg["text_hash"] = calc_hash(msg["text"])
                            all_jobs.append(msg)
            
            await asyncio.sleep(0.5)
    
    total_parsed = sum(len(r) for r in all_results if isinstance(r, list))
    print(f"[CRON] Total parsed: {total_parsed}, passed filter: {len(all_jobs)}")
    
    if not all_jobs:
        # Отправим сообщение что ничего не найдено
        if BOT_TOKEN:
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(ADMIN_ID, f"📭 Заказов не найдено\n\nСпарсено сообщений: {total_parsed}\nПрошло фильтр: 0")
            await bot.session.close()
        return {"parsed": total_parsed, "new": 0, "status": "no jobs found"}
    
    # Работа с БД (используем общий класс Database из src.database)
    try:
        db = Database(DATABASE_URL)
        await db.init_tables()

        # Получаем существующие вакансии за последние 48 часов
        existing_jobs = await db.get_similar_jobs(hours=48)
        existing_hashes = {j["text_hash"] for j in existing_jobs}
        existing_texts = [j["text"] for j in existing_jobs]

        new_jobs = []
        for job in all_jobs:
            # Проверка по хешу
            if job["text_hash"] in existing_hashes:
                continue

            # Проверка по схожести текста (ограничиваемся первыми 50 для скорости)
            if any(is_similar(job["text"], t) for t in existing_texts[:50]):
                continue

            job_id = await db.add_job(
                message_id=job["message_id"],
                channel=job["channel"],
                text=job["text"],
                text_hash=job["text_hash"],
                url=job["url"],
                keywords=job.get("keywords", []),
            )

            if job_id:
                job["id"] = job_id
                new_jobs.append(job)
                existing_hashes.add(job["text_hash"])
        
        print(f"[CRON] New jobs: {len(new_jobs)}")
        
        # Отправляем в Telegram ВСЕ найденные (не только новые)
        bot = Bot(token=BOT_TOKEN)
        
        if all_jobs:
            # Отправляем заголовок
            header = f"📋 <b>Парсинг завершён</b>\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            header += f"📥 Спарсено сообщений: {total_parsed}\n"
            header += f"🔍 Прошло фильтр: {len(all_jobs)}\n"
            header += f"🆕 Новых: {len(new_jobs)}"
            await bot.send_message(ADMIN_ID, header, parse_mode="HTML")
            
            # Отправляем заказы (макс 5)
            jobs_to_show = new_jobs[:5] if new_jobs else all_jobs[:5]
            for job in jobs_to_show:
                text = job["text"][:500] + "..." if len(job["text"]) > 500 else job["text"]
                msg = f"📌 {text}\n\n🏷 {', '.join(job.get('keywords', []))}\n📢 <a href=\"{job['url']}\">Источник</a>"
                try:
                    await bot.send_message(ADMIN_ID, msg, parse_mode="HTML")
                except Exception as e:
                    print(f"[CRON] Send error: {e}")
        else:
            await bot.send_message(ADMIN_ID, f"📭 Заказов не найдено\n\nСпарсено сообщений: {total_parsed}\nПрошло фильтр: 0\n\nВозможно каналы недоступны или нет подходящих сообщений")
        
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
