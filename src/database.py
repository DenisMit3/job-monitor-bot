"""
Работа с базой данных Vercel Postgres
"""
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        return self.pool
    
    async def close(self):
        """Закрытие соединения"""
        if self.pool:
            await self.pool.close()
    
    async def init_tables(self):
        """Создание таблиц"""
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    message_id BIGINT,
                    channel VARCHAR(255),
                    text TEXT,
                    text_hash VARCHAR(64),
                    url VARCHAR(500),
                    keywords TEXT[],
                    created_at TIMESTAMP DEFAULT NOW(),
                    sent BOOLEAN DEFAULT FALSE,
                    UNIQUE(channel, message_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_digests (
                    id SERIAL PRIMARY KEY,
                    job_ids INTEGER[],
                    sent_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_sent ON jobs(sent)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_hash ON jobs(text_hash)
            """)
    
    async def add_job(self, message_id: int, channel: str, text: str, 
                      text_hash: str, url: str, keywords: List[str]) -> Optional[int]:
        """Добавление вакансии"""
        await self.connect()
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    INSERT INTO jobs (message_id, channel, text, text_hash, url, keywords)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (channel, message_id) DO NOTHING
                    RETURNING id
                """, message_id, channel, text, text_hash, url, keywords)
                return result['id'] if result else None
        except Exception as e:
            print(f"Error adding job: {e}")
            return None
    
    async def get_unsent_jobs(self, limit: int = 50) -> List[Dict]:
        """Получение неотправленных вакансий"""
        await self.connect()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, message_id, channel, text, url, keywords, created_at
                FROM jobs
                WHERE sent = FALSE
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            return [dict(row) for row in rows]
    
    async def mark_jobs_sent(self, job_ids: List[int]):
        """Отметить вакансии как отправленные"""
        if not job_ids:
            return
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE jobs SET sent = TRUE WHERE id = ANY($1)
            """, job_ids)
            
            await conn.execute("""
                INSERT INTO sent_digests (job_ids) VALUES ($1)
            """, job_ids)
    
    async def check_duplicate(self, text_hash: str) -> bool:
        """Проверка на дубликат по хешу"""
        await self.connect()
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM jobs WHERE text_hash = $1)
            """, text_hash)
            return result
    
    async def get_similar_jobs(self, hours: int = 24) -> List[Dict]:
        """Получение вакансий за последние N часов для проверки схожести"""
        await self.connect()
        since = datetime.utcnow() - timedelta(hours=hours)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, text, text_hash FROM jobs
                WHERE created_at > $1
            """, since)
            return [dict(row) for row in rows]
    
    async def get_jobs_for_export(self, days: int = 7) -> List[Dict]:
        """Получение вакансий для экспорта"""
        await self.connect()
        since = datetime.utcnow() - timedelta(days=days)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, channel, text, url, keywords, created_at
                FROM jobs
                WHERE created_at > $1
                ORDER BY created_at DESC
            """, since)
            return [dict(row) for row in rows]
    
    async def get_stats(self) -> Dict:
        """Статистика по вакансиям"""
        await self.connect()
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM jobs")
            today = await conn.fetchval("""
                SELECT COUNT(*) FROM jobs 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            sent = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE sent = TRUE")
            
            return {
                "total": total,
                "today": today,
                "sent": sent
            }
