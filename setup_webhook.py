"""
Скрипт для управления webhook Telegram-бота.

Использует токен бота из переменной окружения BOT_TOKEN,
чтобы не хранить его в репозитории.
"""
import asyncio
import aiohttp
import os
import sys

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def set_webhook(vercel_url: str):
    """Установка webhook"""
    if not BOT_TOKEN:
        raise RuntimeError("Переменная окружения BOT_TOKEN не задана")
    webhook_url = f"{vercel_url}/api/webhook"
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json={"url": webhook_url}) as resp:
            result = await resp.json()
            print(f"Set webhook result: {result}")
            return result


async def get_webhook_info():
    """Получение информации о webhook"""
    if not BOT_TOKEN:
        raise RuntimeError("Переменная окружения BOT_TOKEN не задана")
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            result = await resp.json()
            print(f"Webhook info: {result}")
            return result


async def delete_webhook():
    """Удаление webhook"""
    if not BOT_TOKEN:
        raise RuntimeError("Переменная окружения BOT_TOKEN не задана")
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url) as resp:
            result = await resp.json()
            print(f"Delete webhook result: {result}")
            return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  BOT_TOKEN=<your_token> python setup_webhook.py set <vercel_url>")
        print("  BOT_TOKEN=<your_token> python setup_webhook.py info")
        print("  BOT_TOKEN=<your_token> python setup_webhook.py delete")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "set":
        if len(sys.argv) < 3:
            print("Please provide Vercel URL")
            sys.exit(1)
        asyncio.run(set_webhook(sys.argv[2]))
    
    elif command == "info":
        asyncio.run(get_webhook_info())
    
    elif command == "delete":
        asyncio.run(delete_webhook())
    
    else:
        print(f"Unknown command: {command}")
