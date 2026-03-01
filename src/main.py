"""Локальный запуск бота через long polling."""
import asyncio

from src.bot import create_bot, set_database
from src.config import DATABASE_URL
from src.database import Database


async def main() -> None:
    bot, dp = create_bot()

    db = None
    if DATABASE_URL:
        db = Database(DATABASE_URL)
        await db.init_tables()
        set_database(db)
        print("[MAIN] Database initialized")
    else:
        print("[MAIN] DATABASE_URL is not set. Bot will run without DB features")

    print("[MAIN] Starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        if db:
            await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
