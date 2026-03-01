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

# Список источников для парсинга (100+)
CHANNELS = [
    # RU вакансии/фриланс
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
    "https://t.me/freelance_hunt_job",
    "https://t.me/freelancejobsru",
    "https://t.me/udalenka_rabota",
    "https://t.me/remote_job_russia",
    "https://t.me/freelance_ru",
    "https://t.me/distantsiya",
    "https://t.me/freelancepro",
    "https://t.me/webjobsru",
    "https://t.me/frontend_jobs",
    "https://t.me/backend_jobs_ru",
    "https://t.me/nodejs_jobs",
    "https://t.me/react_jobs",
    "https://t.me/vuejs_jobs",
    "https://t.me/php_jobs",
    "https://t.me/python_jobs_ru",
    "https://t.me/javascript_jobs",
    "https://t.me/botdev_jobs",
    "https://t.me/telegram_bot_dev",
    "https://t.me/tgbotjobs",
    "https://t.me/fullstack_jobs",
    "https://t.me/devops_jobs_ru",
    "https://t.me/qa_jobs_ru",
    "https://t.me/mobile_dev_jobs",
    "https://t.me/habr_career",
    "https://t.me/getmatch_jobs",
    "https://t.me/geekjob",
    "https://t.me/moikrug",
    "https://t.me/djinni_jobs",
    "https://t.me/startupjobs_ru",
    "https://t.me/vc_jobs",
    "https://t.me/founders_jobs",

    # RU чаты/заказы
    "https://t.me/fl_ru_chat",
    "https://t.me/freelanceru",
    "https://t.me/zakazy_freelance",
    "https://t.me/webdev_ru",
    "https://t.me/frontend_ru",
    "https://t.me/js_ru",
    "https://t.me/python_ru",
    "https://t.me/php_ru",
    "https://t.me/botoid",
    "https://t.me/it_orders",
    "https://t.me/dev_orders",
    "https://t.me/it_vacancies",
    "https://t.me/it_rabota",
    "https://t.me/remotedevjobs",
    "https://t.me/jobs_in_it",
    "https://t.me/workforprogrammers",
    "https://t.me/jobforjunior",
    "https://t.me/it_freelance_projects",
    "https://t.me/orders_for_dev",
    "https://t.me/python_work",

    # International sources
    "https://t.me/remote_jobs_feed",
    "https://t.me/weworkremotely",
    "https://t.me/remoteworkers",
    "https://t.me/remoteokjobs",
    "https://t.me/devops_jobs",
    "https://t.me/frontendjob",
    "https://t.me/backendjob",
    "https://t.me/pythonjobs",
    "https://t.me/javascriptjobs",
    "https://t.me/reactjobs",
    "https://t.me/nodejobs",
    "https://t.me/golangjobs",
    "https://t.me/rustjobs",
    "https://t.me/javajobs",
    "https://t.me/dotnetjobs",
    "https://t.me/mobilejobs",
    "https://t.me/androidjobs",
    "https://t.me/iosjobs",
    "https://t.me/flutterjobs",
    "https://t.me/wordpressjobs",
    "https://t.me/shopifyjobs",
    "https://t.me/upworkjobs",
    "https://t.me/fiverrjobs",
    "https://t.me/remoteprogrammingjobs",
    "https://t.me/techjobsworld",
    "https://t.me/web3jobs",
    "https://t.me/blockchainjobs",
    "https://t.me/ai_jobs",
    "https://t.me/ml_jobs",
    "https://t.me/datajobs",

    # Extra sources to exceed 100
    "https://t.me/itjobschannel",
    "https://t.me/itjobs_daily",
    "https://t.me/programming_jobs",
    "https://t.me/coding_jobs",
    "https://t.me/devrel_jobs",
    "https://t.me/startupremotejobs",
    "https://t.me/remoteeujobs",
    "https://t.me/remoteworldjobs",
    "https://t.me/careersintech",
    "https://t.me/engineerjobs",
    "https://t.me/saas_jobs",
    "https://t.me/no_code_jobs",
    "https://t.me/uiux_jobs",
    "https://t.me/productdev_jobs",
    "https://t.me/qaautomationjobs",
    "https://t.me/sre_jobs",
    "https://t.me/cloudjobs",
    "https://t.me/kubernetes_jobs",
    "https://t.me/docker_jobs",
    "https://t.me/aws_jobs",
    "https://t.me/azure_jobs",
    "https://t.me/gcp_jobs",
    "https://t.me/fintech_jobs",
    "https://t.me/ecommerce_jobs",
    "https://t.me/telegramdevjobs",
    "https://t.me/chatbot_jobs",
    "https://t.me/opensource_jobs",
    "https://t.me/parttime_dev_jobs",
    "https://t.me/junior_dev_jobs",
    "https://t.me/middle_dev_jobs",
    "https://t.me/senior_dev_jobs",
    "https://t.me/remote_freelance_projects",
    "https://t.me/daily_dev_gigs",
    "https://t.me/it_side_projects",
    "https://t.me/it_gig_market",
    "https://t.me/indiehackers_jobs",
    "https://t.me/founder_needs_dev",
    "https://t.me/agency_dev_jobs",
    "https://t.me/landingpage_jobs",
    "https://t.me/telegram_orders",
]

KEYWORDS = {
    "web": [
        "сайт", "веб", "web", "frontend", "фронтенд", "backend", "бэкенд", "бекенд",
        "react", "vue", "angular", "next", "nuxt", "node", "nodejs", "php", "laravel",
        "wordpress", "django", "flask", "fastapi", "html", "css", "javascript", "js",
        "typescript", "ts", "верстка", "landing", "лендинг", "интернет-магазин"
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
    ],
    "freelance": [
        "заказ", "проект", "бюджет", "оплата", "платно", "сделать", "доработать",
        "исправить", "тз", "нужен", "нужна", "кто сможет", "freelance", "gig"
    ],
}

STOP_WORDS = [
    "менеджер", "manager", "hr", "recruiter", "рекрутер", "продажи", "sales",
    "маркетолог", "marketing", "smm", "seo", "копирайт", "дизайнер ux/ui",
    "gamedev", "unity", "unreal", "3d artist"
]

# Порог схожести для дедупликации (0.0 - 1.0)
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.72"))
