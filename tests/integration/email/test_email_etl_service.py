# test_etl_service.py
import pytest
import tempfile
import os
from voice_agent.database_service import Database
from voice_agent.etl_service import EmailETLService
from voice_agent.models import ETLJobStatus
from voice_agent.config import settings
from voice_agent.embeddings.vector_store import EmailSearchStore
import pytest_asyncio
import shutil

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

@pytest_asyncio.fixture
async def test_vector_store():
    """Create a test vector store for ETL testing"""
    # Create temporary directory for ChromaDB
    temp_dir = tempfile.mkdtemp()
    
    vector_store = EmailSearchStore(persist_directory=temp_dir)
    await vector_store.init_store()
    
    yield vector_store
    
    await vector_store.close()
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_full_etl_pipeline_with_real_api(test_database, test_vector_store):
    """Test the complete ETL pipeline with real Nylas API call and vector store"""
    
    # Create ETL service with both database and vector store
    etl_service = EmailETLService(
        test_database, 
        vector_store=test_vector_store
    )
    
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
    
    # Verify emails were saved to vector store
    vector_store_count = await test_vector_store.get_count()
    assert vector_store_count == emails_processed
    print(f"Vector store contains {vector_store_count} emails")
    
    if emails_processed > 0:
        # Test retrieving recent emails from database
        recent_emails = await test_database.email_repo.get_recent(limit=5)
        assert len(recent_emails) <= 5
        assert len(recent_emails) <= emails_processed
        
        # Check first email has required fields
        first_email = recent_emails[0]
        assert first_email.id is not None
        assert first_email.subject is not None
        assert first_email.created_at is not None
        assert first_email.processed_at is not None
        
        print(f"First email: {first_email.subject} from {first_email.from_email}")
        
        # Test retrieving by ID from database
        retrieved_email = await test_database.get_email_by_id(first_email.id)
        assert retrieved_email is not None
        assert retrieved_email.id == first_email.id
        
        # Test that email exists in vector store
        exists_in_vector_store = await test_vector_store.email_exists(first_email.id)
        assert exists_in_vector_store is True
        
        # Test semantic search works on real data
        if first_email.subject:
            # Search using words from the subject
            subject_words = first_email.subject.split()[:2]  # First 2 words
            if subject_words:
                search_query = " ".join(subject_words)
                search_results = await test_vector_store.search_emails(
                    query=search_query,
                    limit=5
                )
                assert len(search_results) > 0
                print(f"Search for '{search_query}' returned {len(search_results)} results")
                
                # Verify search results have expected structure
                first_result = search_results[0]
                assert 'email_id' in first_result
                assert 'distance' in first_result
                assert 'metadata' in first_result
    
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
async def test_etl_with_limited_emails(test_database, test_vector_store):
    """Test ETL with a small number of emails for faster testing"""
    
    etl_service = EmailETLService(
        test_database,
        vector_store=test_vector_store
    )
    
    # Limit to just 3 emails for faster testing
    etl_service.email_fetcher.MAX_EMAILS = 3
    
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    result = await etl_service.run_etl(grant_id)
    
    assert result["status"] == "success"
    assert result["emails_processed"] <= 3
    
    # Verify database operations work with real data
    email_count = await test_database.get_email_count()
    assert email_count == result["emails_processed"]
    
    # Verify vector store operations work with real data
    vector_count = await test_vector_store.get_count()
    assert vector_count == result["emails_processed"]

@pytest.mark.asyncio
async def test_etl_skips_duplicate_emails_in_vector_store(test_database, test_vector_store):
    """Test that running ETL twice doesn't duplicate emails in vector store"""
    
    etl_service = EmailETLService(
        test_database,
        vector_store=test_vector_store
    )
    
    # Limit emails for faster test
    etl_service.email_fetcher.MAX_EMAILS = 2
    
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    
    # Run ETL first time
    result1 = await etl_service.run_etl(grant_id)
    first_count = result1["emails_processed"]
    vector_count_1 = await test_vector_store.get_count()
    
    # Run ETL second time (should skip existing emails in vector store)
    result2 = await etl_service.run_etl(grant_id)
    second_count = result2["emails_processed"]
    vector_count_2 = await test_vector_store.get_count()
    
    # Vector store count should remain the same (no duplicates)
    assert vector_count_1 == vector_count_2
    assert vector_count_1 == first_count
    
    print(f"First run: {first_count} emails, Vector store: {vector_count_1}")
    print(f"Second run: {second_count} emails, Vector store: {vector_count_2}")
    print("✓ No duplicates created in vector store")

@pytest.mark.asyncio
async def test_semantic_search_on_real_emails(test_database, test_vector_store):
    """Test semantic search capabilities on real email data"""
    
    etl_service = EmailETLService(
        test_database,
        vector_store=test_vector_store
    )
    
    # Load some real emails
    etl_service.email_fetcher.MAX_EMAILS = 10
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    
    result = await etl_service.run_etl(grant_id)
    emails_processed = result["emails_processed"]
    
    if emails_processed > 0:
        # Test various search queries
        test_queries = [
            "meeting",
            "project update",
            "deadline",
            "important"
        ]
        
        for query in test_queries:
            results = await test_vector_store.search_emails(query, limit=3)
            print(f"\nSearch: '{query}' -> {len(results)} results")
            
            for i, result in enumerate(results[:2], 1):
                subject = result['metadata'].get('subject', 'No subject')
                distance = result['distance']
                print(f"  {i}. {subject} (distance: {distance:.3f})")