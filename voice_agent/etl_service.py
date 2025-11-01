# Fetch emails from api, save to database

import asyncio
from typing import List, Dict
from loguru import logger
from database import Database
from email_fetcher import NylasEmailFetcher
from config import settings

class EmailETLService:
    def __init__(self, database, nylas_api_key: str = None):
        self.database = database
        self.email_fetcher = NylasEmailFetcher(nylas_api_key)
        
    async def run_etl(self, grant_id: str) -> Dict:
        """Run the complete ETL process for emails"""
        job_id = await self._start_etl_job()
        
        try:
            # Extract
            logger.info(f"Starting email extraction for grant {grant_id}")
            emails = await self.email_fetcher.fetch_emails(grant_id)
            
            # Transform
            logger.info(f"Transforming {len(emails)} emails")
            transformed_emails = self._transform_emails(emails)
            
            # Load
            logger.info(f"Loading {len(transformed_emails)} emails to database")
            await self._load_emails(transformed_emails)
            
            # Mark job complete
            await self._complete_etl_job(job_id, len(transformed_emails))
            
            return {
                "status": "success",
                "emails_processed": len(transformed_emails),
                "job_id": job_id
            }
            
        except Exception as e:
            await self._fail_etl_job(job_id, str(e))
            raise
    
    def _transform_emails(self, emails: List[Dict]) -> List[Dict]:
        """Transform raw Nylas emails to our database schema"""
        transformed = []
        
        for email in emails:
            # Handle from field (array, take first)
            from_info = email.get("from", [{}])[0] if email.get("from") else {}
            
            # Handle to field (array, take first)
            to_info = email.get("to", [{}])[0] if email.get("to") else {}
            
            transformed_email = {
                "id": email.get("id"),
                "thread_id": email.get("thread_id"),
                "subject": email.get("subject", ""),
                "body": email.get("body", ""),
                "from_name": from_info.get("name", ""),
                "from_email": from_info.get("email", ""),
                "to_name": to_info.get("name", ""),
                "to_email": to_info.get("email", ""),
                "date": email.get("date")  # Unix timestamp
            }
            
            transformed.append(transformed_email)
        
        return transformed
    
    async def _load_emails(self, emails: List[Dict]):
        """Load emails into database"""
        for email in emails:
            await self.database.save_email(email)
    
    async def _start_etl_job(self) -> str:
        """Record ETL job start in database"""
        job_id = await self.database.start_etl_job(
            job_type="email_extraction",
            status="running"
        )
        return job_id
    
    async def _complete_etl_job(self, job_id: str, records_processed: int):
        """Mark ETL job as complete"""
        await self.database.complete_etl_job(
            job_id=job_id,
            status="completed",
            records_processed=records_processed
        )
    
    async def _fail_etl_job(self, job_id: str, error_message: str):
        """Mark ETL job as failed"""
        await self.database.complete_etl_job(
            job_id=job_id,
            status="failed",
            error_message=error_message
        )


# Usage example:
async def main():
    from database import Database
    
    db = Database()
    await db.init_db()
    
    etl = EmailETLService(database=db)
    
    grant_id = settings.nylas_email_account_grant_id
    result = await etl.run_etl(grant_id)
    
    print(f"ETL completed: {result}")

if __name__ == "__main__":
    asyncio.run(main())