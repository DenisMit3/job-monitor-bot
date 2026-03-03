# Job Monitoring Telegram Bot

Телеграм бот для мониторинга IT-вакансий из Telegram каналов.

## Функции

- Парсинг 50+ IT-каналов с вакансиями
- Фильтрация по ключевым словам (веб, боты, fullstack, DevOps, ML)
- Умная дедупликация похожих вакансий
- Дайджест раз в час
- Экспорт в CSV

## Деплой на Vercel

1. Создать репозиторий на GitHub/GitLab и запушить этот проект
2. Подключить репозиторий к Vercel
3. В Vercel добавить переменные окружения:
   - `BOT_TOKEN` — токен бота
   - `ADMIN_ID` — ваш Telegram ID
   - `DATABASE_URL` — URL базы данных Vercel Postgres
4. Задеплоить проект (Vercel сам поднимет функции `api/webhook.py` и `api/cron.py`)
5. Установить webhook Telegram на Vercel‑URL:
   ```bash
   # в Windows PowerShell
   $env:BOT_TOKEN = "ВАШ_ТОКЕН"
   python setup_webhook.py set https://ВАШ_ПРОЕКТ.vercel.app
   ```

## Локальный запуск (только для отладки)

```bash
pip install -r requirements.txt
python -m src.bot
```
