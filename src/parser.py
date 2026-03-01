"""
Парсер Telegram каналов через публичный веб-интерфейс
"""
import aiohttp
import asyncio
import re
import hashlib
import os
from html import unescape
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from src.config import CHANNELS, KEYWORDS, STOP_WORDS, SIMILARITY_THRESHOLD


class TelegramParser:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.verbose = os.getenv("PARSER_VERBOSE", "0") == "1"
        self.error_stats = {
            "network": 0,
            "timeout": 0,
            "http": 0,
            "other": 0,
        }

    async def get_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                }
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    @staticmethod
    def extract_channel_name(url: str) -> str:
        """Извлечение имени канала из URL/username"""
        value = url.strip().rstrip("/")
        match = re.search(r"t\.me/([^/?]+)", value)
        if match:
            return match.group(1)
        return value.lstrip("@")

    async def parse_channel(self, channel_url: str, limit: int = 30) -> List[Dict]:
        """Парсинг одного канала через t.me/s/"""
        channel_name = self.extract_channel_name(channel_url)
        web_url = f"https://t.me/s/{channel_name}"

        try:
            session = await self.get_session()
            async with session.get(web_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    self.error_stats["http"] += 1
                    if self.verbose:
                        print(f"[PARSER] Channel {channel_name}: HTTP {resp.status}")
                    return []

                html = await resp.text()
                return self.parse_html(html, channel_name, limit)
        except asyncio.TimeoutError:
            self.error_stats["timeout"] += 1
            if self.verbose:
                print(f"[PARSER] Timeout parsing {channel_name}")
            return []
        except aiohttp.ClientConnectorError as e:
            self.error_stats["network"] += 1
            if self.verbose:
                print(f"[PARSER] Network error parsing {channel_name}: {e}")
            return []
        except Exception as e:
            self.error_stats["other"] += 1
            print(f"[PARSER] Error parsing {channel_name}: {e}")
            return []

    def parse_html(self, html: str, channel_name: str, limit: int = 30) -> List[Dict]:
        """Устойчивый парсинг HTML страницы канала"""
        messages: List[Dict] = []

        post_pattern = re.compile(r'<div class="tgme_widget_message_wrap[^"]*"[^>]*data-post="([^"]+)"[^>]*>')
        text_pattern = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.DOTALL)

        post_matches = list(post_pattern.finditer(html))
        if not post_matches:
            return messages

        selected = post_matches[-limit:]
        for idx, post_match in enumerate(selected):
            post = post_match.group(1)
            start_pos = post_match.end()
            if idx + 1 < len(selected):
                end_pos = selected[idx + 1].start()
            else:
                end_pos = min(len(html), start_pos + 20000)

            block = html[start_pos:end_pos]
            text_match = text_pattern.search(block)
            if not text_match:
                continue

            text = self.clean_html(text_match.group(1))
            if not text or len(text) < 50:
                continue

            message_id = 0
            raw_id = post.split('/')[-1]
            if raw_id.isdigit():
                message_id = int(raw_id)

            messages.append(
                {
                    "message_id": message_id,
                    "channel": channel_name,
                    "text": text,
                    "url": f"https://t.me/{post}",
                }
            )

        return messages

    @staticmethod
    def clean_html(html: str) -> str:
        """Очистка HTML от тегов"""
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def is_job_posting(self, text: str) -> Tuple[bool, List[str]]:
        """Проверка, является ли текст потенциальным заказом/вакансией"""
        text_lower = text.lower()

        for stop_word in STOP_WORDS:
            if stop_word.lower() in text_lower:
                return False, []

        found_keywords = []
        for category, words in KEYWORDS.items():
            for word in words:
                if word.lower() in text_lower:
                    found_keywords.append(category)
                    break

        if not found_keywords:
            return False, []

        job_indicators = [
            "ищем", "ищу", "требуется", "нужен", "нужна", "нужно", "вакансия", "работа",
            "оплата", "бюджет", "зп", "зарплата", "оклад", "ставка", "проект", "заказ",
            "задача", "тз", "разработка", "разработать", "сделать", "создать", "написать",
            "доработать", "пофиксить", "нужна помощь", "кто сможет", "кто возьмется",
            "remote", "freelance", "фриланс", "подработка", "part-time",
        ]

        has_indicator = any(ind in text_lower for ind in job_indicators)
        return has_indicator, list(set(found_keywords))

    @staticmethod
    def calculate_hash(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.lower().strip())
        normalized = re.sub(r"\d+", "", normalized)
        return hashlib.md5(normalized.encode()).hexdigest()

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def is_similar_to_existing(self, text: str, existing_texts: List[str]) -> bool:
        for existing in existing_texts:
            if self.calculate_similarity(text, existing) > SIMILARITY_THRESHOLD:
                return True
        return False

    def extract_metadata(self, text: str, keywords: List[str]) -> Dict:
        """Извлечение доп. полей для таблицы jobs."""
        text_lower = text.lower()

        # Бюджет
        currency = None
        if "$" in text or "usd" in text_lower:
            currency = "USD"
        elif "€" in text or "eur" in text_lower:
            currency = "EUR"
        elif "₽" in text or "руб" in text_lower or "rur" in text_lower:
            currency = "RUB"

        numbers = [int(x) for x in re.findall(r"(?<!\d)(\d{2,7})(?!\d)", text)]
        budget_min = min(numbers) if numbers else None
        budget_max = max(numbers) if len(numbers) > 1 else budget_min

        # Контакт
        contact_match = re.search(r"(@[A-Za-z0-9_]{4,})", text)
        email_match = re.search(r"([\w\.-]+@[\w\.-]+\.[A-Za-z]{2,})", text)
        contact_raw = None
        if contact_match:
            contact_raw = contact_match.group(1)
        elif email_match:
            contact_raw = email_match.group(1)

        # Remote
        is_remote = any(word in text_lower for word in ["remote", "удал", "удален", "удалён"])

        # Seniority
        seniority = None
        if any(w in text_lower for w in ["junior", "джун", "стажер", "стажёр"]):
            seniority = "junior"
        elif any(w in text_lower for w in ["middle", "мидл"]):
            seniority = "middle"
        elif any(w in text_lower for w in ["senior", "сеньор", "lead", "лид"]):
            seniority = "senior"

        # Match score (простая эвристика 0..100)
        score = 30
        score += min(30, len(keywords) * 8)
        if contact_raw:
            score += 15
        if currency or budget_min:
            score += 15
        if is_remote:
            score += 10
        match_score = min(100, score)

        return {
            "budget_min": budget_min,
            "budget_max": budget_max,
            "currency": currency,
            "contact_raw": contact_raw,
            "is_remote": is_remote,
            "seniority": seniority,
            "match_score": float(match_score),
        }

    async def parse_all_channels(self, batch_size: int = 8, per_channel_limit: int = 30) -> List[Dict]:
        """Парсинг всех каналов с фильтрацией релевантных заказов/вакансий"""
        all_jobs = []

        for i in range(0, len(CHANNELS), batch_size):
            batch = CHANNELS[i:i + batch_size]
            tasks = [self.parse_channel(url, limit=per_channel_limit) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    for msg in result:
                        is_job, keywords = self.is_job_posting(msg["text"])
                        if is_job:
                            msg["keywords"] = keywords
                            msg["text_hash"] = self.calculate_hash(msg["text"])
                            msg.update(self.extract_metadata(msg["text"], keywords))
                            all_jobs.append(msg)
                elif isinstance(result, Exception):
                    self.error_stats["other"] += 1
                    if self.verbose:
                        print(f"[PARSER] Gather exception: {result}")

            await asyncio.sleep(0.5)

        print(
            "[PARSER] Parse summary: "
            f"jobs={len(all_jobs)}, "
            f"network_errors={self.error_stats['network']}, "
            f"timeouts={self.error_stats['timeout']}, "
            f"http_errors={self.error_stats['http']}, "
            f"other_errors={self.error_stats['other']}"
        )

        await self.close()
        return all_jobs
