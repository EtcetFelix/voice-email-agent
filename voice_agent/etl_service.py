# email_etl_service.py
from datetime import datetime, timezone
from typing import List, Dict
from loguru import logger
from voice_agent.database_service import Database
from voice_agent.email_fetcher import NylasEmailFetcher
from voice_agent.models import EmailModel, ETLJobModel, ETLJobStatus
from voice_agent.embeddings.vector_store import EmailSearchStore


class EmailETLService:
    def __init__(
        self, 
        database: Database, 
        nylas_api_key: str = None,
        vector_store: EmailSearchStore = None,
        persist_directory: str = "./data/chroma_db"
    ):
        self.database = database
        self.email_fetcher = NylasEmailFetcher(nylas_api_key)
        self.vector_store = vector_store
        self.persist_directory = persist_directory
        
    async def run_etl(self, grant_id: str) -> Dict:
        """Run the complete ETL process for emails"""
        job_id = await self._start_etl_job()
        
        try:
            # Initialize vector store if not provided
            if self.vector_store is None:
                self.vector_store = EmailSearchStore(persist_directory=self.persist_directory)
                await self.vector_store.init_store()
            
            # Extract
            logger.info(f"Starting email extraction for grant {grant_id}")
            raw_emails = await self.email_fetcher.fetch_emails(grant_id)
            
            # Transform
            logger.info(f"Transforming {len(raw_emails)} emails")
            email_models = self._transform_emails(raw_emails)
            
            # Load to database
            logger.info(f"Loading {len(email_models)} emails to database")
            await self._load_emails(email_models)
            
            # Load to vector store
            logger.info(f"Loading {len(email_models)} emails to vector store")
            await self._load_emails_to_vector_store(email_models)
            
            # Mark job complete
            await self._complete_etl_job(job_id, len(email_models))
            
            return {
                "status": "success",
                "emails_processed": len(email_models),
                "job_id": job_id
            }
            
        except Exception as e:
            await self._fail_etl_job(job_id, str(e))
            raise
    
    def _transform_emails(self, raw_emails: List[Dict]) -> List[EmailModel]:
        """Transform raw Nylas emails to EmailModel objects"""
        email_models = []
        
        for raw_email in raw_emails:
            try:
                # Handle from field (array, take first)
                from_info = raw_email.get("from", [{}])[0] if raw_email.get("from") else {}
                
                # Handle to field (array, take first)
                to_info = raw_email.get("to", [{}])[0] if raw_email.get("to") else {}
                
                # Create EmailModel with validation
                email_model = EmailModel(
                    id=raw_email.get("id"),
                    thread_id=raw_email.get("thread_id"),
                    subject=raw_email.get("subject", ""),
                    body=raw_email.get("body", ""),
                    from_name=from_info.get("name", ""),
                    from_email=from_info.get("email", ""),
                    to_name=to_info.get("name", ""),
                    to_email=to_info.get("email", ""),
                    date=raw_email.get("date"),
                    processed_at=datetime.now(timezone.utc)
                )
                
                email_models.append(email_model)
                
            except Exception as e:
                logger.error(f"Failed to transform email {raw_email.get('id', 'unknown')}: {e}")
                continue
        
        return email_models
    
    async def _load_emails(self, emails: List[EmailModel]):
        """Load EmailModel objects into database"""
        for email in emails:
            await self.database.save_email(email)
    
    async def _load_emails_to_vector_store(self, emails: List[EmailModel]):
        """Load EmailModel objects into vector store for semantic search"""
        if not emails:
            logger.debug("No emails to load to vector store")
            return
        
        try:
            # Check which emails already exist to avoid duplicates
            new_emails = []
            for email in emails:
                exists = await self.vector_store.email_exists(email.id)
                if not exists:
                    new_emails.append(email)
            
            if new_emails:
                # Use batch operation for efficiency
                await self.vector_store.add_emails_batch(new_emails)
                logger.info(f"Added {len(new_emails)} new emails to vector store")
            else:
                logger.info("All emails already exist in vector store, skipping")
                
        except Exception as e:
            logger.error(f"Failed to load emails to vector store: {e}")
            # Don't fail the entire ETL if vector store fails
            # Log error but continue
    
    async def _start_etl_job(self) -> str:
        """Record ETL job start in database"""
        job = ETLJobModel(
            job_type="email_extraction",
            status=ETLJobStatus.RUNNING
        )
        job_id = await self.database.start_etl_job(job)
        return job_id
    
    async def _complete_etl_job(self, job_id: str, records_processed: int):
        """Mark ETL job as complete"""
        await self.database.complete_etl_job(
            job_id=job_id,
            status=ETLJobStatus.COMPLETED,
            records_processed=records_processed
        )
    
    async def _fail_etl_job(self, job_id: str, error_message: str):
        """Mark ETL job as failed"""
        await self.database.complete_etl_job(
            job_id=job_id,
            status=ETLJobStatus.FAILED,
            error_message=error_message
        )