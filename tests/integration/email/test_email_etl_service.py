import pytest
import tempfile
import os
from voice_agent.database_service import Database
from voice_agent.etl_service import EmailETLService
from voice_agent.models import ETLJobStatus
from voice_agent.config import settings
import pytest_asyncio

@pytest_asyncio.fixture
async def test_database():
    """Create a test database for ETL testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    db = Database()
    await db.init_db(db_path)
    
    yield db
    
    await db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.mark.asyncio
async def test_full_etl_pipeline_with_real_api(test_database):
    """Test the complete ETL pipeline with real Nylas API call"""
    
    # Create ETL service with real email fetcher
    etl_service = EmailETLService(test_database)
    
    # Use real grant ID from settings
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    
    # Run the ETL process with real API
    result = await etl_service.run_etl(grant_id)
    
    # Verify ETL completed successfully
    assert result["status"] == "success"
    assert "emails_processed" in result
    assert "job_id" in result
    
    emails_processed = result["emails_processed"]
    print(f"Processed {emails_processed} emails from real API")
    
    # Verify emails were saved to database
    email_count = await test_database.get_email_count()
    assert email_count == emails_processed
    
    if emails_processed > 0:
        # Test retrieving recent emails
        recent_emails = await test_database.email_repo.get_recent(limit=5)
        assert len(recent_emails) <= 5
        assert len(recent_emails) <= emails_processed
        
        # Check first email has required fields
        first_email = recent_emails[0]
        assert first_email.id is not None
        assert first_email.subject is not None  # Can be empty string
        assert first_email.created_at is not None
        assert first_email.processed_at is not None
        
        print(f"First email: {first_email.subject} from {first_email.from_email}")
        
        # Test retrieving by ID
        retrieved_email = await test_database.get_email_by_id(first_email.id)
        assert retrieved_email is not None
        assert retrieved_email.id == first_email.id
        assert retrieved_email.subject == first_email.subject
    
    # Verify ETL job was tracked correctly
    job_id = result["job_id"]
    etl_job = await test_database.etl_repo.get_by_id(job_id)
    assert etl_job is not None
    assert etl_job.status == ETLJobStatus.COMPLETED
    assert etl_job.records_processed == emails_processed
    assert etl_job.job_type == "email_extraction"
    assert etl_job.error_message is None
    assert etl_job.completed_at is not None
    
    print(f"ETL job {job_id} completed successfully")

@pytest.mark.asyncio
async def test_etl_with_limited_emails(test_database):
    """Test ETL with a small number of emails for faster testing"""
    
    etl_service = EmailETLService(test_database)
    
    # Limit to just 3 emails for faster testing
    etl_service.email_fetcher.MAX_EMAILS = 3
    
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    result = await etl_service.run_etl(grant_id)
    
    assert result["status"] == "success"
    assert result["emails_processed"] <= 3
    
    # Verify database operations work with real data
    email_count = await test_database.get_email_count()
    assert email_count == result["emails_processed"]
