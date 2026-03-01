"""Локальная диагностика работоспособности бота.

По умолчанию выполняет только офлайн-проверки (без внешней сети),
чтобы команда стабильно проходила в CI/изолированных окружениях.

Онлайн-проверки можно включить:
- аргументом `--online`
- или переменной `HEALTHCHECK_ONLINE=1`

Для валидации деплоя (упасть, если деплой недоступен):
- `--require-online-success`
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Tuple

import aiohttp
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Сначала .env, затем fallback на .env.example
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / ".env.example", override=False)

from api.cron import run_parsing
from src.config import CHANNELS


def check_env() -> List[str]:
    required = ["BOT_TOKEN", "ADMIN_ID", "DATABASE_URL"]
    missing = [name for name in required if not os.getenv(name)]

    print("[CHECK] ENV:")
    for key in required:
        print(f"  - {key}: {'OK' if os.getenv(key) else 'MISSING'}")

    return missing


def check_offline() -> None:
    print("[CHECK] Offline config:")
    print(f"  - channels_total={len(CHANNELS)}")
    print(f"  - channels_unique={len(set(CHANNELS))}")


def should_run_online_checks() -> bool:
    if "--online" in sys.argv:
        return True
    return os.getenv("HEALTHCHECK_ONLINE", "0") == "1"


def require_online_success() -> bool:
    return "--require-online-success" in sys.argv


async def check_cron_dry_run_online() -> Tuple[bool, dict]:
    print("[CHECK] Cron dry-run (online mode):")
    result = await run_parsing()
    print(f"  - result={result}")

    ok = result.get("status") in {"success", "no jobs found"} and "error" not in result
    return ok, result


async def check_vercel_online() -> bool:
    project_url = os.getenv("PROJECT_URL", "https://botmonitorinaraboty.vercel.app").rstrip("/")
    print("[CHECK] Vercel endpoints (online mode):")

    timeout = aiohttp.ClientTimeout(total=20)
    ok = True
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for path in ("/api/webhook", "/api/cron"):
            url = f"{project_url}{path}"
            try:
                async with session.get(url) as resp:
                    body = await resp.text()
                    preview = body[:180].replace("\n", " ")
                    print(f"  - GET {url}: status={resp.status}, body={preview}")
                    if resp.status >= 500:
                        ok = False
            except Exception as exc:
                print(f"  - GET {url}: error={exc}")
                ok = False
    return ok


async def main() -> None:
    missing = check_env()
    check_offline()

    online_ok = True
    if should_run_online_checks():
        cron_ok, _ = await check_cron_dry_run_online()
        vercel_ok = await check_vercel_online()
        online_ok = cron_ok and vercel_ok
    else:
        print("[CHECK] Online checks: SKIPPED (use --online or HEALTHCHECK_ONLINE=1)")

    if missing:
        print(f"[SUMMARY] Missing env vars: {', '.join(missing)}")
    else:
        print("[SUMMARY] Env looks complete")

    if require_online_success() and not online_ok:
        print("[SUMMARY] Online validation failed (deployment may be unavailable)")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
