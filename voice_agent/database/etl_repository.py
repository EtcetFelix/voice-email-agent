# database/etl_repository.py
from typing import Optional
from datetime import datetime, timezone
from loguru import logger
import aiosqlite
from voice_agent.models import ETLJobModel, ETLJobStatus

class ETLJobRepository:
    """Repository for ETL job database operations"""
    
    def __init__(self, connection: aiosqlite.Connection):
        self.connection = connection
    
    async def start_job(self, job: ETLJobModel) -> str:
        """Start a new ETL job"""
        query = """
        INSERT INTO etl_jobs (job_type, status, started_at)
        VALUES (?, ?, ?)
        """
        
        try:
            cursor = await self.connection.execute(
                query, (job.job_type, job.status.value, job.started_at)
            )
            await self.connection.commit()
            
            job_id = cursor.lastrowid
            logger.info(f"Started ETL job {job_id} of type {job.job_type}")
            return str(job_id)
            
        except Exception as e:
            logger.error(f"Failed to start ETL job: {e}")
            raise
    
    async def complete_job(
        self, 
        job_id: str, 
        status: ETLJobStatus, 
        records_processed: int = 0,
        error_message: Optional[str] = None
    ):
        """Complete an ETL job"""
        query = """
        UPDATE etl_jobs 
        SET status = ?, records_processed = ?, error_message = ?, completed_at = ?
        WHERE id = ?
        """
        
        try:
            await self.connection.execute(
                query, 
                (status.value, records_processed, error_message, 
                 datetime.now(timezone.utc), int(job_id))
            )
            await self.connection.commit()
            logger.info(f"Completed ETL job {job_id} with status {status.value}")
            
        except Exception as e:
            logger.error(f"Failed to complete ETL job {job_id}: {e}")
            raise
    
    async def get_by_id(self, job_id: str) -> Optional[ETLJobModel]:
        """Get ETL job by ID"""
        query = "SELECT * FROM etl_jobs WHERE id = ?"
        
        try:
            cursor = await self.connection.execute(query, (int(job_id),))
            row = await cursor.fetchone()
            
            if row:
                # Convert row to dict (SQLite returns tuples)
                columns = [description[0] for description in cursor.description]
                job_data = dict(zip(columns, row))
                
                # Convert status string back to enum
                job_data['status'] = ETLJobStatus(job_data['status'])
                return ETLJobModel(**job_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get ETL job {job_id}: {e}")
            raise
    
    async def get_recent(self, limit: int = 20) -> list[ETLJobModel]:
        """Get recent ETL jobs"""
        query = "SELECT * FROM etl_jobs ORDER BY started_at DESC LIMIT ?"
        
        try:
            cursor = await self.connection.execute(query, (limit,))
            rows = await cursor.fetchall()
            
            jobs = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                job_data = dict(zip(columns, row))
                job_data['status'] = ETLJobStatus(job_data['status'])
                jobs.append(ETLJobModel(**job_data))
                
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to get recent ETL jobs: {e}")
            raise