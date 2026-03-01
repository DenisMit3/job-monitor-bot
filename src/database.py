"""
Работа с базой данных Vercel Postgres
"""
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict


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
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    message_id BIGINT,
                    channel VARCHAR(255),
                    text TEXT,
                    text_hash VARCHAR(64),
                    url VARCHAR(500),
                    keywords TEXT[],
                    budget_min NUMERIC,
                    budget_max NUMERIC,
                    currency VARCHAR(10),
                    contact_raw TEXT,
                    is_remote BOOLEAN,
                    seniority VARCHAR(32),
                    match_score NUMERIC,
                    created_at TIMESTAMP DEFAULT NOW(),
                    sent BOOLEAN DEFAULT FALSE,
                    UNIQUE(channel, message_id)
                )
                """
            )

            # Миграции для уже существующей таблицы jobs
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS budget_min NUMERIC")
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS budget_max NUMERIC")
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS currency VARCHAR(10)")
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS contact_raw TEXT")
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_remote BOOLEAN")
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS seniority VARCHAR(32)")
            await conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS match_score NUMERIC")

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_digests (
                    id SERIAL PRIMARY KEY,
                    job_ids INTEGER[],
                    sent_at TIMESTAMP DEFAULT NOW()
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS parse_runs (
                    id BIGSERIAL PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT NOW(),
                    finished_at TIMESTAMP,
                    status VARCHAR(32) DEFAULT 'running',
                    sources_total INTEGER DEFAULT 0,
                    filtered_total INTEGER DEFAULT 0,
                    new_total INTEGER DEFAULT 0,
                    sent_total INTEGER DEFAULT 0,
                    recipients_total INTEGER DEFAULT 0,
                    network_errors INTEGER DEFAULT 0,
                    timeout_errors INTEGER DEFAULT 0,
                    http_errors INTEGER DEFAULT 0,
                    other_errors INTEGER DEFAULT 0,
                    error_text TEXT
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS parse_run_jobs (
                    run_id BIGINT REFERENCES parse_runs(id) ON DELETE CASCADE,
                    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                    added_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (run_id, job_id)
                )
                """
            )

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_sent ON jobs(sent)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_hash ON jobs(text_hash)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_parse_runs_started ON parse_runs(started_at)")

    async def create_parse_run(self, sources_total: int, recipients_total: int) -> Optional[int]:
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO parse_runs (sources_total, recipients_total)
                VALUES ($1, $2)
                RETURNING id
                """,
                sources_total,
                recipients_total,
            )
            return int(row["id"]) if row else None

    async def finish_parse_run(
        self,
        run_id: int,
        status: str,
        filtered_total: int,
        new_total: int,
        sent_total: int,
        parser_errors: Dict,
        error_text: Optional[str] = None,
    ):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE parse_runs
                SET finished_at = NOW(),
                    status = $2,
                    filtered_total = $3,
                    new_total = $4,
                    sent_total = $5,
                    network_errors = $6,
                    timeout_errors = $7,
                    http_errors = $8,
                    other_errors = $9,
                    error_text = $10
                WHERE id = $1
                """,
                run_id,
                status,
                filtered_total,
                new_total,
                sent_total,
                int(parser_errors.get("network", 0)),
                int(parser_errors.get("timeout", 0)),
                int(parser_errors.get("http", 0)),
                int(parser_errors.get("other", 0)),
                error_text,
            )

    async def add_jobs_to_parse_run(self, run_id: int, job_ids: List[int]):
        if not job_ids:
            return
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO parse_run_jobs (run_id, job_id)
                VALUES ($1, $2)
                ON CONFLICT (run_id, job_id) DO NOTHING
                """,
                [(run_id, jid) for jid in job_ids],
            )

    async def add_job(
        self,
        message_id: int,
        channel: str,
        text: str,
        text_hash: str,
        url: str,
        keywords: List[str],
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        currency: Optional[str] = None,
        contact_raw: Optional[str] = None,
        is_remote: Optional[bool] = None,
        seniority: Optional[str] = None,
        match_score: Optional[float] = None,
    ) -> Optional[int]:
        await self.connect()
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO jobs (
                        message_id, channel, text, text_hash, url, keywords,
                        budget_min, budget_max, currency, contact_raw, is_remote, seniority, match_score
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (channel, message_id) DO NOTHING
                    RETURNING id
                    """,
                    message_id,
                    channel,
                    text,
                    text_hash,
                    url,
                    keywords,
                    budget_min,
                    budget_max,
                    currency,
                    contact_raw,
                    is_remote,
                    seniority,
                    match_score,
                )
                return result["id"] if result else None
        except Exception as e:
            print(f"Error adding job: {e}")
            return None

    async def get_unsent_jobs(self, limit: int = 50) -> List[Dict]:
        await self.connect()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, message_id, channel, text, url, keywords, created_at,
                       budget_min, budget_max, currency, contact_raw, is_remote, seniority, match_score
                FROM jobs
                WHERE sent = FALSE
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
            return [dict(row) for row in rows]

    async def mark_jobs_sent(self, job_ids: List[int]):
        if not job_ids:
            return
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE jobs SET sent = TRUE WHERE id = ANY($1)", job_ids)
            await conn.execute("INSERT INTO sent_digests (job_ids) VALUES ($1)", job_ids)

    async def check_duplicate(self, text_hash: str) -> bool:
        await self.connect()
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM jobs WHERE text_hash = $1)", text_hash)
            return result

    async def get_similar_jobs(self, hours: int = 24) -> List[Dict]:
        await self.connect()
        since = datetime.utcnow() - timedelta(hours=hours)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, text, text_hash FROM jobs
                WHERE created_at > $1
                """,
                since,
            )
            return [dict(row) for row in rows]

    async def get_jobs_for_export(self, days: int = 7) -> List[Dict]:
        await self.connect()
        since = datetime.utcnow() - timedelta(days=days)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, channel, text, url, keywords, created_at,
                       budget_min, budget_max, currency, contact_raw, is_remote, seniority, match_score
                FROM jobs
                WHERE created_at > $1
                ORDER BY created_at DESC
                """,
                since,
            )
            return [dict(row) for row in rows]

    async def get_stats(self) -> Dict:
        await self.connect()
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM jobs")
            today = await conn.fetchval(
                """
                SELECT COUNT(*) FROM jobs
                WHERE created_at > NOW() - INTERVAL '24 hours'
                """
            )
            sent = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE sent = TRUE")

            return {
                "total": total,
                "today": today,
                "sent": sent,
            }
