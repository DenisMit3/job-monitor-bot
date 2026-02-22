"""
Конфигурация бота и список каналов для парсинга
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5171260626"))
DATABASE_URL = os.getenv("DATABASE_URL")

# Parsing settings
PARSE_INTERVAL = int(os.getenv("PARSE_INTERVAL", "60"))

# Список IT-каналов с вакансиями для парсинга
CHANNELS = [
    # Основные IT-вакансии
    "https://t.me/devjobs",
    "https://t.me/fordev",
    "https://t.me/jobsfordev",
    "https://t.me/web_work",
    "https://t.me/theyseekingdev",
    "https://t.me/freelancetaverna",
    "https://t.me/itchanneljob",
    "https://t.me/remote_it",
    "https://t.me/workinit",
    "https://t.me/myjobit",
    
    # Фриланс и удалёнка
    "https://t.me/freelance_hunt_job",
    "https://t.me/freelancejobsru",
    "https://t.me/udalenka_rabota",
    "https://t.me/remote_job_russia",
    "https://t.me/freelance_ru",
    "https://t.me/distantsiya",
    "https://t.me/freelancepro",
    
    # Веб-разработка
    "https://t.me/webjobsru",
    "https://t.me/frontend_jobs",
    "https://t.me/backend_jobs_ru",
    "https://t.me/nodejs_jobs",
    "https://t.me/react_jobs",
    "https://t.me/vuejs_jobs",
    "https://t.me/php_jobs",
    "https://t.me/python_jobs_ru",
    "https://t.me/javascript_jobs",
    
    # Telegram боты
    "https://t.me/botdev_jobs",
    "https://t.me/telegram_bot_dev",
    "https://t.me/tgbotjobs",
    
    # Fullstack и общие
    "https://t.me/fullstack_jobs",
    "https://t.me/devops_jobs_ru",
    "https://t.me/qa_jobs_ru",
    "https://t.me/mobile_dev_jobs",
    
    # Крупные агрегаторы
    "https://t.me/habr_career",
    "https://t.me/getmatch_jobs",
    "https://t.me/geekjob",
    "https://t.me/moikrug",
    "https://t.me/djinni_jobs",
    
    # Стартапы и проекты
    "https://t.me/startupjobs_ru",
    "https://t.me/vc_jobs",
    "https://t.me/founders_jobs",
    
    # Международные
    "https://t.me/remote_jobs_feed",
    "https://t.me/weworkremotely",
    "https://t.me/remoteworkers",
]

# Ключевые слова для фильтрации вакансий
KEYWORDS = {
    "web": [
        "сайт", "веб", "web", "frontend", "фронтенд", "backend", "бэкенд", "бекенд",
        "react", "vue", "angular", "next", "nuxt", "node", "nodejs", "php", "laravel",
        "wordpress", "django", "flask", "fastapi", "html", "css", "javascript", "js",
        "typescript", "ts", "верстка", "landing", "лендинг"
    ],
    "bots": [
        "бот", "bot", "telegram", "телеграм", "discord", "чат-бот", "chatbot",
        "aiogram", "pyrogram", "telethon", "telegraf", "автоматизация"
    ],
    "fullstack": [
        "fullstack", "фулстек", "full-stack", "full stack", "разработчик",
        "developer", "программист", "инженер", "engineer"
    ],
    "devops": [
        "devops", "девопс", "docker", "kubernetes", "k8s", "ci/cd", "aws",
        "azure", "gcp", "linux", "nginx", "деплой", "deploy", "инфраструктура"
    ],
    "mobile": [
        "ios", "android", "мобильн", "mobile", "flutter", "react native",
        "swift", "kotlin", "приложение"
    ],
    "ml": [
        "ml", "machine learning", "ai", "искусственный интеллект", "нейросет",
        "data science", "python", "tensorflow", "pytorch", "gpt", "llm"
    ]
}

# Стоп-слова (исключаем вакансии с этими словами)
STOP_WORDS = [
    "менеджер", "manager", "hr", "recruiter", "рекрутер", "продажи", "sales",
    "маркетолог", "marketing", "smm", "seo", "копирайт", "дизайнер ux/ui"
]

# Порог схожести для дедупликации (0.0 - 1.0)
SIMILARITY_THRESHOLD = 0.7
