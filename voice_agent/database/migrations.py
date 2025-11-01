# database/migrations.py
from loguru import logger
import aiosqlite

class DatabaseMigrations:
    """Handles database schema creation and migrations"""
    
    def __init__(self, connection: aiosqlite.Connection):
        self.connection = connection
    
    async def create_tables(self):
        """Create all database tables"""
        try:
            await self._create_emails_table()
            await self._create_etl_jobs_table()
            await self._create_indexes()
            await self.connection.commit()
                
            logger.info("Database tables and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def _create_emails_table(self):
        """Create emails table"""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                subject TEXT DEFAULT '',
                body TEXT DEFAULT '',
                from_name TEXT DEFAULT '',
                from_email TEXT DEFAULT '',
                to_name TEXT DEFAULT '',
                to_email TEXT DEFAULT '',
                date INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            );
        """)
    
    async def _create_etl_jobs_table(self):
        """Create ETL jobs table"""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS etl_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                records_processed INTEGER DEFAULT 0,
                error_message TEXT,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );
        """)
    
    async def _create_indexes(self):
        """Create database indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);",
            "CREATE INDEX IF NOT EXISTS idx_emails_from_email ON emails(from_email);",
            "CREATE INDEX IF NOT EXISTS idx_emails_to_email ON emails(to_email);",
            "CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date);",
            "CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_etl_jobs_status ON etl_jobs(status);",
            "CREATE INDEX IF NOT EXISTS idx_etl_jobs_started_at ON etl_jobs(started_at);"
        ]
        
        for index in indexes:
            await self.connection.execute(index)