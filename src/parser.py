"""
Парсер Telegram каналов через публичный веб-интерфейс
"""
import aiohttp
import asyncio
import re
import hashlib
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime
from src.config import CHANNELS, KEYWORDS, STOP_WORDS, SIMILARITY_THRESHOLD


class TelegramParser:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def extract_channel_name(self, url: str) -> str:
        """Извлечение имени канала из URL"""
        match = re.search(r't\.me/([^/]+)', url)
        return match.group(1) if match else url
    
    async def parse_channel(self, channel_url: str) -> List[Dict]:
        """Парсинг одного канала через t.me/s/"""
        channel_name = self.extract_channel_name(channel_url)
        web_url = f"https://t.me/s/{channel_name}"
        
        try:
            session = await self.get_session()
            async with session.get(web_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    print(f"Channel {channel_name}: status {resp.status}")
                    return []
                
                html = await resp.text()
                return self.parse_html(html, channel_name)
        except asyncio.TimeoutError:
            print(f"Timeout parsing {channel_name}")
            return []
        except Exception as e:
            print(f"Error parsing {channel_name}: {e}")
            return []
    
    def parse_html(self, html: str, channel_name: str) -> List[Dict]:
        """Парсинг HTML страницы канала"""
        messages = []
        
        # Ищем блоки сообщений
        message_pattern = r'<div class="tgme_widget_message_wrap[^"]*"[^>]*data-post="([^"]+)"[^>]*>(.*?)</div>\s*</div>\s*</div>'
        
        # Упрощённый паттерн для текста
        text_pattern = r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>'
        
        # Ищем все посты
        post_pattern = r'data-post="([^"]+)"'
        posts = re.findall(post_pattern, html)
        
        # Ищем тексты сообщений
        texts = re.findall(text_pattern, html, re.DOTALL)
        
        for i, post_id in enumerate(posts[-20:]):  # Последние 20 сообщений
            if i < len(texts):
                text = self.clean_html(texts[i])
                if text and len(text) > 50:  # Минимальная длина
                    message_id = int(post_id.split('/')[-1]) if '/' in post_id else 0
                    messages.append({
                        "message_id": message_id,
                        "channel": channel_name,
                        "text": text,
                        "url": f"https://t.me/{post_id}"
                    })
        
        return messages
    
    def clean_html(self, html: str) -> str:
        """Очистка HTML от тегов"""
        # Заменяем <br> на переносы
        text = re.sub(r'<br\s*/?>', '\n', html)
        # Убираем все теги
        text = re.sub(r'<[^>]+>', '', text)
        # Декодируем HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        # Убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def is_job_posting(self, text: str) -> Tuple[bool, List[str]]:
        """Проверка, является ли текст вакансией"""
        text_lower = text.lower()
        
        # Проверяем стоп-слова
        for stop_word in STOP_WORDS:
            if stop_word.lower() in text_lower:
                return False, []
        
        # Ищем ключевые слова
        found_keywords = []
        for category, words in KEYWORDS.items():
            for word in words:
                if word.lower() in text_lower:
                    found_keywords.append(category)
                    break
        
        # Должно быть хотя бы одно ключевое слово
        if not found_keywords:
            return False, []
        
        # Дополнительные признаки вакансии
        job_indicators = [
            "ищем", "ищу", "требуется", "нужен", "вакансия", "работа",
            "оплата", "бюджет", "зп", "зарплата", "оклад", "ставка",
            "удалённо", "удаленно", "remote", "фриланс", "freelance",
            "проект", "заказ", "задача", "тз", "разработка", "разработать",
            "сделать", "создать", "написать", "нужно сделать"
        ]
        
        has_indicator = any(ind in text_lower for ind in job_indicators)
        
        return has_indicator, list(set(found_keywords))
    
    def calculate_hash(self, text: str) -> str:
        """Вычисление хеша текста для дедупликации"""
        # Нормализуем текст
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        # Убираем числа (цены, даты могут меняться)
        normalized = re.sub(r'\d+', '', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Вычисление схожести двух текстов"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def is_similar_to_existing(self, text: str, existing_texts: List[str]) -> bool:
        """Проверка схожести с существующими вакансиями"""
        for existing in existing_texts:
            if self.calculate_similarity(text, existing) > SIMILARITY_THRESHOLD:
                return True
        return False
    
    async def parse_all_channels(self) -> List[Dict]:
        """Парсинг всех каналов"""
        all_jobs = []
        
        # Парсим каналы пачками по 5
        batch_size = 5
        for i in range(0, len(CHANNELS), batch_size):
            batch = CHANNELS[i:i + batch_size]
            tasks = [self.parse_channel(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    for msg in result:
                        is_job, keywords = self.is_job_posting(msg["text"])
                        if is_job:
                            msg["keywords"] = keywords
                            msg["text_hash"] = self.calculate_hash(msg["text"])
                            all_jobs.append(msg)
            
            # Пауза между пачками
            await asyncio.sleep(1)
        
        await self.close()
        return all_jobs
