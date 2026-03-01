# Job Monitoring Telegram Bot

Телеграм-бот для мониторинга заказов и IT-вакансий из Telegram-каналов.

## Что умеет

- Парсит **100+ источников** (каналы и профильные чаты).
- Фильтрует сообщения по ключевым словам и индикаторам заказа/вакансии.
- Выполняет дедупликацию (hash + similarity).
- Отправляет отчёт и новые релевантные сообщения администратору.
- Поддерживает команды бота (`/start`, `/help`, `/parse`, `/channels`, ...).

## Переменные окружения

- `BOT_TOKEN` — токен Telegram-бота
- `ADMIN_ID` — Telegram ID администратора
- `DATABASE_URL` — строка подключения PostgreSQL
- `CRON_ENDPOINT` — (опционально) endpoint для ручного `/parse` из webhook
- `SIMILARITY_THRESHOLD` — (опционально) порог дедупликации, по умолчанию `0.72`
- `PROJECT_URL` — (опционально) URL Vercel проекта для healthcheck

## Локальный запуск

```bash
pip install -r requirements.txt
python -m src.main
```

## Локальная диагностика

```bash
python scripts/healthcheck.py
# Онлайн-проверки (cron + Vercel endpoints):
python scripts/healthcheck.py --online
# Строгая проверка деплоя (код !=0 если недоступен):
python scripts/healthcheck.py --online --require-online-success
```


## Табличная выгрузка результатов парсинга

При включенном `DATABASE_URL` бот пишет данные в PostgreSQL таблицы:

- `jobs` — карточки вакансий (`message_id`, `channel`, `text`, `text_hash`, `url`, `keywords`, `budget_min`, `budget_max`, `currency`, `contact_raw`, `is_remote`, `seniority`, `match_score`, `created_at`, `sent`)
- `parse_runs` — история запусков парсинга (`started_at`, `finished_at`, `status`, `sources_total`, `filtered_total`, `new_total`, `sent_total`, `recipients_total`, `*_errors`, `error_text`)
- `parse_run_jobs` — связь вакансий с конкретным запуском (`run_id`, `job_id`)

Где смотреть:
- в вашей Postgres БД (`DATABASE_URL`) таблица `jobs` — сами вакансии с доп. колонками,
- `parse_runs` — журнал запусков,
- `parse_run_jobs` — какие вакансии к какому запуску относятся.

## Деплой на Vercel

- `api/webhook.py` — endpoint для Telegram webhook
- `api/cron.py` — периодический парсинг и отправка дайджеста
- расписание Cron задаётся в `vercel.json`
