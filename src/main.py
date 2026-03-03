"""
Локальный запуск Telegram-бота через long polling.

Используется для разработки и тестирования на локальной машине.
"""
import asyncio
from typing import Optional

from src.config import BOT_TOKEN, DATABASE_URL
from src.database import Database
from src.bot import create_bot, set_database


async def main():
    """Точка входа для локального запуска бота."""
    if not BOT_TOKEN:
        raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

    db: Optional[Database] = None

    if DATABASE_URL:
        # Инициализируем базу данных (создаём таблицы при необходимости)
        db = Database(DATABASE_URL)
        await db.init_tables()
        set_database(db)
        print("[LOCAL] Database initialized")
    else:
        print("[LOCAL] WARNING: DATABASE_URL не задан, часть команд (stats/digest/export) работать не будет")

    bot, dp = create_bot()
    print("[LOCAL] Bot is starting via long polling...")

    try:
        await dp.start_polling(bot)
    finally:
        if db and db.pool:
            await db.close()
            print("[LOCAL] Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())


