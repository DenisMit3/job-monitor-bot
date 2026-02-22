# Job Monitoring Telegram Bot

Телеграм бот для мониторинга IT-вакансий из Telegram каналов.

## Функции

- Парсинг 50+ IT-каналов с вакансиями
- Фильтрация по ключевым словам (веб, боты, fullstack, DevOps, ML)
- Умная дедупликация похожих вакансий
- Дайджест раз в час
- Экспорт в CSV

## Деплой на Vercel

1. Fork репозитория
2. Подключить к Vercel
3. Добавить переменные окружения:
   - `BOT_TOKEN` - токен бота
   - `ADMIN_ID` - ваш Telegram ID
   - `DATABASE_URL` - URL базы данных Vercel Postgres

## Локальный запуск

```bash
pip install -r requirements.txt
python src/main.py
```
