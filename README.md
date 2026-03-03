# Job Monitoring Telegram Bot

Телеграм бот для мониторинга IT-вакансий из Telegram каналов.

## Функции

- Парсинг 50+ IT-каналов с вакансиями
- Фильтрация по ключевым словам (веб, боты, fullstack, DevOps, ML)
- Умная дедупликация похожих вакансий
- Дайджест раз в час
- Экспорт в CSV

## Структура проекта

- `src/config.py` — настройки бота, список каналов, ключевые слова, стоп‑слова.
- `src/database.py` — работа с базой данных (Postgres через asyncpg).
- `src/parser.py` — парсер Telegram‑каналов через публичный веб‑интерфейс.
- `src/bot.py` — обработчики команд и форматирование сообщений.
- `src/main.py` — **точка входа для локального запуска бота** (long polling).
- `api/webhook.py` — обработчик webhook для деплоя на Vercel.
- `api/cron.py` — фоновой парсинг и рассылка дайджеста на Vercel.
- `setup_webhook.py` — утилита для настройки webhook в Telegram.

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

## Локальный запуск (для разработки)

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта (рядом с `requirements.txt`) и пропишите в нём:

```bash
BOT_TOKEN=Ваш_токен_бота_из_BotFather
ADMIN_ID=Ваш_числовой_Telegram_ID
DATABASE_URL=postgres://user:password@host:5432/dbname  # опционально, но нужен для статистики/экспорта
```

3. Запустите бота локально:

```bash
python src/main.py
```

Бот будет работать через long polling. Для остановки нажмите `Ctrl+C` в консоли.

## Git и игнорируемые файлы

Рекомендуемый `.gitignore` для этого проекта:

```gitignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

.env
.env.*
.venv
.vscode/
.idea/

.DS_Store
thumbs.db
```
