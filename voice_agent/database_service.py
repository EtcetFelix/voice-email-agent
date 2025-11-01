# database.py
import aiosqlite
from typing import Optional, List
from loguru import logger
from voice_agent.config import settings
from voice_agent.models import EmailModel, ETLJobModel, ETLJobStatus
from voice_agent.database.email_repository import EmailRepository
from voice_agent.database.etl_repository import ETLJobRepository 
from voice_agent.database.migrations import DatabaseMigrations

class Database:
    """Database connection and operations for the email ETL service"""
    
    def __init__(self):
        self.connection: Optional[aiosqlite.Connection] = None
        self.email_repo: Optional[EmailRepository] = None
        self.etl_repo: Optional[ETLJobRepository] = None  # Available if needed
        
    async def init_db(self, database_path: Optional[str] = None):
        """Initialize database connection pool and create tables"""
        try:
            if not database_path:
                database_path = self._get_database_path()
            
            self.connection = await aiosqlite.connect(database_path)
            # Enable foreign keys and WAL mode for better performance
            await self.connection.execute("PRAGMA foreign_keys = ON")
            await self.connection.execute("PRAGMA journal_mode = WAL")
            
            logger.info(f"Database connection created: {database_path}")
            
            # Initialize repositories
            self.email_repo = EmailRepository(self.connection)
            self.etl_repo = ETLJobRepository(self.connection)  # Uncomment when needed
            
            # Create tables
            migrations = DatabaseMigrations(self.connection)
            await migrations.create_tables()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")
    
    def _get_database_path(self) -> str:
        """Get database path from settings"""
        db_path = getattr(settings, 'DB_PATH', 'voice_email_agent.db')
        return db_path
    
    # Email operations - clean delegation
    async def save_email(self, email: EmailModel) -> None:
        """Save an EmailModel to database"""
        return await self.email_repo.save(email)
    
    async def save_email_batch(self, emails: List[EmailModel]) -> None:
        """Save multiple emails in a single transaction"""
        return await self.email_repo.save_batch(emails)
    
    async def get_email_by_id(self, email_id: str) -> Optional[EmailModel]:
        """Retrieve an email by ID"""
        return await self.email_repo.get_by_id(email_id)
    
    async def email_exists(self, email_id: str) -> bool:
        """Check if an email exists"""
        return await self.email_repo.exists(email_id)
    
    async def get_email_count(self) -> int:
        """Get total number of emails"""
        return await self.email_repo.count()
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            await self.pool.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def start_etl_job(self, job: ETLJobModel) -> str:
        return await self.etl_repo.start_job(job)
    
    async def complete_etl_job(self, job_id: str, status: ETLJobStatus, 
                              records_processed: int = 0, error_message: str = None):
        return await self.etl_repo.complete_job(job_id, status, records_processed, error_message)