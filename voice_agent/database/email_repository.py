# database/email_repository.py
from typing import Optional, List
from loguru import logger
import aiosqlite
from voice_agent.models import EmailModel

class EmailRepository:
    """Repository for email database operations"""
    
    def __init__(self, connection: aiosqlite.Connection):
        self.connection = connection
    
    async def save(self, email: EmailModel) -> None:
        """Save an email to database"""
        query = """
        INSERT OR REPLACE INTO emails (
            id, thread_id, subject, body, from_name, from_email, 
            to_name, to_email, date, created_at, updated_at, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            await self.connection.execute(
                query,
                (email.id, email.thread_id, email.subject, email.body,
                 email.from_name, email.from_email, email.to_name, email.to_email,
                 email.date, email.created_at, email.updated_at, email.processed_at)
            )
            await self.connection.commit()
            logger.debug(f"Saved email: {email.id}")
            
        except Exception as e:
            logger.error(f"Failed to save email {email.id}: {e}")
            raise
    
    async def save_batch(self, emails: List[EmailModel]) -> None:
        """Save multiple emails in a transaction"""
        if not emails:
            return
            
        query = """
        INSERT OR IGNORE INTO emails (
            id, thread_id, subject, body, from_name, from_email, 
            to_name, to_email, date, created_at, updated_at, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            email_data = [
                (email.id, email.thread_id, email.subject, email.body,
                 email.from_name, email.from_email, email.to_name, email.to_email,
                 email.date, email.created_at, email.updated_at, email.processed_at)
                for email in emails
            ]
            
            await self.connection.executemany(query, email_data)
            await self.connection.commit()
            
            logger.info(f"Saved batch of {len(emails)} emails")
            
        except Exception as e:
            logger.error(f"Failed to save email batch: {e}")
            raise
        
    async def get_recent(self, limit: int = 50) -> List[EmailModel]:
        """Get recent emails ordered by date"""
        query = "SELECT * FROM emails ORDER BY date DESC LIMIT ?"
        
        try:
            cursor = await self.connection.execute(query, (limit,))
            rows = await cursor.fetchall()
            
            # Convert rows to EmailModel objects
            emails = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                email_data = dict(zip(columns, row))
                emails.append(EmailModel(**email_data))
                
            return emails
            
        except Exception as e:
            logger.error(f"Failed to get recent emails: {e}")
            raise
    
    async def get_by_id(self, email_id: str) -> Optional[EmailModel]:
        """Get email by ID"""
        query = "SELECT * FROM emails WHERE id = ?"
        
        try:
            cursor = await self.connection.execute(query, (email_id,))
            row = await cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                email_data = dict(zip(columns, row))
                return EmailModel(**email_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get email {email_id}: {e}")
            raise

    async def exists(self, email_id: str) -> bool:
        """Check if email exists"""
        query = "SELECT 1 FROM emails WHERE id = ?"
        
        try:
            cursor = await self.connection.execute(query, (email_id,))
            result = await cursor.fetchone()
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to check if email exists {email_id}: {e}")
            raise
    
    async def count(self) -> int:
        """Get total email count"""
        query = "SELECT COUNT(*) FROM emails"
        try:
            cursor = await self.connection.execute(query)
            result = await cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get email count: {e}")
            raise