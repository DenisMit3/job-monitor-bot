"""
Telegram бот для отправки вакансий
"""
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict
import csv
import io
from datetime import datetime

from src.config import BOT_TOKEN, ADMIN_ID, KEYWORDS
from src.database import Database


router = Router()
db: Database = None


def set_database(database: Database):
    global db
    db = database


def format_job(job: Dict) -> str:
    """Форматирование вакансии для отправки"""
    keywords_str = ", ".join(job.get("keywords", []))
    text = job["text"]
    
    # Обрезаем длинный текст
    if len(text) > 800:
        text = text[:800] + "..."
    
    return (
        f"📌 <b>Новая вакансия</b>\n\n"
        f"{text}\n\n"
        f"🏷 <i>{keywords_str}</i>\n"
        f"📢 <a href=\"{job['url']}\">Источник</a>"
    )


def format_digest(jobs: List[Dict]) -> str:
    """Форматирование дайджеста"""
    if not jobs:
        return "📭 Новых вакансий не найдено"
    
    header = f"📋 <b>Дайджест вакансий</b>\n"
    header += f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    header += f"📊 Найдено: {len(jobs)} вакансий\n"
    header += "─" * 20 + "\n\n"
    
    return header


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
        "/keywords - Ключевые слова\n"
        "/help - Помощь",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "📖 <b>Справка</b>\n\n"
        "Бот автоматически парсит IT-каналы каждый час "
        "и присылает дайджест новых вакансий.\n\n"
        "🔍 <b>Фильтрация:</b>\n"
        "- Веб-разработка (React, Vue, Node, PHP...)\n"
        "- Telegram боты\n"
        "- Fullstack разработка\n"
        "- DevOps\n"
        "- Мобильная разработка\n"
        "- ML/AI\n\n"
        "🔄 <b>Дедупликация:</b>\n"
        "Похожие вакансии из разных каналов объединяются.",
        parse_mode="HTML"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not db:
        await message.answer("❌ База данных не подключена")
        return
    
    stats = await db.get_stats()
    
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"📝 Всего вакансий: {stats['total']}\n"
        f"🆕 За 24 часа: {stats['today']}\n"
        f"✅ Отправлено: {stats['sent']}",
        parse_mode="HTML"
    )


@router.message(Command("digest"))
async def cmd_digest(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not db:
        await message.answer("❌ База данных не подключена")
        return
    
    jobs = await db.get_unsent_jobs(limit=20)
    
    if not jobs:
        await message.answer("📭 Новых вакансий пока нет")
        return
    
    await message.answer(format_digest(jobs), parse_mode="HTML")
    
    for job in jobs[:10]:  # Отправляем первые 10
        try:
            await message.answer(format_job(job), parse_mode="HTML")
        except Exception as e:
            print(f"Error sending job: {e}")
    
    if len(jobs) > 10:
        await message.answer(f"... и ещё {len(jobs) - 10} вакансий. Используйте /export для полного списка.")
    
    # Отмечаем как отправленные
    job_ids = [j["id"] for j in jobs]
    await db.mark_jobs_sent(job_ids)


@router.message(Command("export"))
async def cmd_export(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not db:
        await message.answer("❌ База данных не подключена")
        return
    
    jobs = await db.get_jobs_for_export(days=7)
    
    if not jobs:
        await message.answer("📭 Нет вакансий для экспорта")
        return
    
    # Создаём CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Канал", "Текст", "URL", "Категории", "Дата"])
    
    for job in jobs:
        writer.writerow([
            job["id"],
            job["channel"],
            job["text"][:500],
            job["url"],
            ", ".join(job.get("keywords", [])),
            job["created_at"].strftime("%d.%m.%Y %H:%M")
        ])
    
    # Отправляем файл
    csv_bytes = output.getvalue().encode('utf-8-sig')
    file = BufferedInputFile(csv_bytes, filename=f"jobs_{datetime.now().strftime('%Y%m%d')}.csv")
    
    await message.answer_document(
        file,
        caption=f"📊 Экспорт {len(jobs)} вакансий за последние 7 дней"
    )


@router.message(Command("channels"))
async def cmd_channels(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    from src.config import CHANNELS
    
    channels_list = "\n".join([f"• {ch}" for ch in CHANNELS[:30]])
    
    await message.answer(
        f"📢 <b>Каналы для мониторинга</b>\n"
        f"Всего: {len(CHANNELS)}\n\n"
        f"{channels_list}\n"
        f"{'...' if len(CHANNELS) > 30 else ''}",
        parse_mode="HTML"
    )


@router.message(Command("keywords"))
async def cmd_keywords(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = "🔑 <b>Ключевые слова</b>\n\n"
    
    for category, words in KEYWORDS.items():
        text += f"<b>{category}:</b> {', '.join(words[:10])}...\n\n"
    
    await message.answer(text, parse_mode="HTML")


async def send_digest_to_admin(bot: Bot, jobs: List[Dict]):
    """Отправка дайджеста администратору"""
    if not jobs:
        return
    
    await bot.send_message(ADMIN_ID, format_digest(jobs), parse_mode="HTML")
    
    for job in jobs[:15]:
        try:
            await bot.send_message(ADMIN_ID, format_job(job), parse_mode="HTML")
        except Exception as e:
            print(f"Error sending job: {e}")
    
    if len(jobs) > 15:
        await bot.send_message(
            ADMIN_ID, 
            f"📌 Показано 15 из {len(jobs)} вакансий. /export для полного списка."
        )


def create_bot() -> tuple[Bot, Dispatcher]:
    """Создание бота и диспетчера"""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp
