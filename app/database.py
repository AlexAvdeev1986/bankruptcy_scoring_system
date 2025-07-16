import aiosqlite
import logging
from contextlib import asynccontextmanager
from .config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = Config.DATABASE_URL.split("///")[-1]):
        self.db_path = db_path
    
    @asynccontextmanager
    async def get_connection(self):
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            await conn.close()
    
    async def init_database(self):
        async with self.get_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT UNIQUE,
                    fio TEXT,
                    phone TEXT,
                    inn TEXT,
                    dob TEXT,
                    address TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags TEXT,
                    email TEXT,
                    region TEXT
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS scoring_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT,
                    score INTEGER,
                    reason_1 TEXT,
                    reason_2 TEXT,
                    reason_3 TEXT,
                    is_target INTEGER,
                    group_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS external_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT,
                    source TEXT,
                    data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
                )
            """)
            
            await conn.commit()
            logger.info("Database initialized")
    
    async def save_leads(self, leads: list):
        async with self.get_connection() as conn:
            for lead in leads:
                await conn.execute("""
                    INSERT OR IGNORE INTO leads 
                    (lead_id, fio, phone, inn, dob, address, source, tags, email, region)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lead.get('lead_id'),
                    lead.get('fio'),
                    lead.get('phone'),
                    lead.get('inn'),
                    lead.get('dob'),
                    lead.get('address'),
                    lead.get('source'),
                    lead.get('tags'),
                    lead.get('email'),
                    lead.get('region')
                ))
            await conn.commit()
            logger.info(f"Saved {len(leads)} leads to database")
    
    async def save_scoring_results(self, results: list):
        async with self.get_connection() as conn:
            for result in results:
                await conn.execute("""
                    INSERT INTO scoring_results 
                    (lead_id, score, reason_1, reason_2, reason_3, is_target, group_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.get('lead_id'),
                    result.get('score'),
                    result.get('reason_1'),
                    result.get('reason_2'),
                    result.get('reason_3'),
                    result.get('is_target'),
                    result.get('group')
                ))
            await conn.commit()
            logger.info(f"Saved {len(results)} scoring results to database")
    
    async def get_leads_by_region(self, regions: list) -> list:
        async with self.get_connection() as conn:
            placeholders = ','.join(['?' for _ in regions])
            query = f"SELECT * FROM leads WHERE region IN ({placeholders})"
            
            cursor = await conn.execute(query, regions)
            rows = await cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        