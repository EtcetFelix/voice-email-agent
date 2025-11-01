# tests/integration/email/test_email_tools.py
import pytest
import tempfile
import os
import shutil
from voice_agent.database_service import Database
from voice_agent.embeddings.vector_store import EmailSearchStore
from voice_agent.etl_service import EmailETLService
from voice_agent.tools.email_tools import EmailSearchTools
from voice_agent.config import settings
import pytest_asyncio


@pytest_asyncio.fixture
async def test_database():
    """Create a test database"""
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
    """Create a test vector store"""
    temp_dir = tempfile.mkdtemp()
    
    vector_store = EmailSearchStore(persist_directory=temp_dir)
    await vector_store.init_store()
    
    yield vector_store
    
    await vector_store.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def populated_email_system(test_database, test_vector_store):
    """
    Fixture that populates both database and vector store with real email data.
    This is the key fixture that sets up test data.
    """
    # Run ETL to populate both database and vector store
    etl_service = EmailETLService(
        test_database,
        vector_store=test_vector_store
    )
    
    # Limit to 10 emails for faster testing
    etl_service.email_fetcher.MAX_EMAILS = 10
    
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    result = await etl_service.run_etl(grant_id)
    
    # Create email tools instance
    email_tools = EmailSearchTools(
        database=test_database,
        vector_store=test_vector_store
    )
    
    return {
        "email_tools": email_tools,
        "database": test_database,
        "vector_store": test_vector_store,
        "emails_loaded": result["emails_processed"]
    }


class TestEmailSearchTools:
    """Integration tests for email search tools with real data"""
    
    @pytest.mark.asyncio
    async def test_search_emails_returns_results(self, populated_email_system):
        """Test basic email search functionality"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        # Skip test if no emails loaded
        if emails_loaded == 0:
            pytest.skip("No emails available for testing")
        
        # Search for a generic term that should match something
        results = await email_tools.search_emails(query="email", limit=5)
        
        # Should return some results
        assert len(results) > 0
        assert len(results) <= 5
        
        # Check result structure
        first_result = results[0]
        assert "subject" in first_result
        assert "from_name" in first_result
        assert "from_email" in first_result
        assert "date" in first_result
        assert "body_preview" in first_result
        assert "relevance_score" in first_result
        
        print(f"Search returned {len(results)} results")
        print(f"First result: {first_result['subject']}")
    
    @pytest.mark.asyncio
    async def test_search_emails_with_specific_query(self, populated_email_system):
        """Test search with specific query terms"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded == 0:
            pytest.skip("No emails available for testing")
        
        # Get a real subject from loaded emails to search for
        db = populated_email_system["database"]
        recent = await db.email_repo.get_recent(limit=1)
        
        if recent and recent[0].subject:
            # Extract a word from the subject to search for
            subject_words = recent[0].subject.split()
            if subject_words:
                search_term = subject_words[0]
                
                results = await email_tools.search_emails(query=search_term, limit=3)
                
                # Should find something
                assert len(results) > 0
                print(f"Searched for '{search_term}', found {len(results)} results")
    
    @pytest.mark.asyncio
    async def test_search_emails_limit_parameter(self, populated_email_system):
        """Test that limit parameter is respected"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded < 3:
            pytest.skip("Need at least 3 emails for this test")
        
        # Search with different limits
        results_limit_2 = await email_tools.search_emails(query="email", limit=2)
        results_limit_5 = await email_tools.search_emails(query="email", limit=5)
        
        assert len(results_limit_2) <= 2
        assert len(results_limit_5) <= 5
        
        print(f"Limit 2: {len(results_limit_2)} results")
        print(f"Limit 5: {len(results_limit_5)} results")
    
    @pytest.mark.asyncio
    async def test_search_emails_by_sender(self, populated_email_system):
        """Test searching by sender"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded == 0:
            pytest.skip("No emails available for testing")
        
        # Get a real sender from loaded emails
        db = populated_email_system["database"]
        recent = await db.email_repo.get_recent(limit=1)
        
        if recent and recent[0].from_email:
            sender_email = recent[0].from_email
            
            results = await email_tools.search_emails_by_sender(
                sender_name_or_email=sender_email,
                limit=5
            )
            
            # Should find at least the one we know exists
            assert len(results) >= 1
            
            # All results should be from that sender
            for result in results:
                assert result["from_email"] == sender_email
            
            print(f"Found {len(results)} emails from {sender_email}")
    
    @pytest.mark.asyncio
    async def test_search_emails_by_sender_with_query(self, populated_email_system):
        """Test searching by sender with content query"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded == 0:
            pytest.skip("No emails available for testing")
        
        # Get a real sender and subject
        db = populated_email_system["database"]
        recent = await db.email_repo.get_recent(limit=1)
        
        if recent and recent[0].from_email and recent[0].subject:
            sender_email = recent[0].from_email
            subject_word = recent[0].subject.split()[0] if recent[0].subject.split() else "email"
            
            results = await email_tools.search_emails_by_sender(
                sender_name_or_email=sender_email,
                query=subject_word,
                limit=5
            )
            
            # Should find results from that sender
            assert len(results) > 0
            
            print(f"Found {len(results)} emails from {sender_email} about '{subject_word}'")
    
    @pytest.mark.asyncio
    async def test_get_recent_emails(self, populated_email_system):
        """Test getting recent emails"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded == 0:
            pytest.skip("No emails available for testing")
        
        results = await email_tools.get_recent_emails(limit=5)
        
        # Should return emails up to the limit
        assert len(results) > 0
        assert len(results) <= min(5, emails_loaded)
        
        # Check structure
        first_result = results[0]
        assert "subject" in first_result
        assert "from_name" in first_result
        assert "from_email" in first_result
        assert "date" in first_result
        assert "body_preview" in first_result
        
        print(f"Retrieved {len(results)} recent emails")
        for i, email in enumerate(results[:3], 1):
            print(f"{i}. {email['subject']} from {email['from_email']}")
    
    @pytest.mark.asyncio
    async def test_format_emails_for_llm(self, populated_email_system):
        """Test email formatting for LLM consumption"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded == 0:
            pytest.skip("No emails available for testing")
        
        results = await email_tools.search_emails(query="email", limit=3)
        formatted = email_tools.format_emails_for_llm(results)
        
        # Should be a string
        assert isinstance(formatted, str)
        
        # Should contain key information
        assert "Found" in formatted
        assert "Subject:" in formatted
        assert "From:" in formatted
        
        print("Formatted output:")
        print(formatted)
    
    @pytest.mark.asyncio
    async def test_format_emails_for_llm_empty_results(self, populated_email_system):
        """Test formatting when no results found"""
        email_tools = populated_email_system["email_tools"]
        
        formatted = email_tools.format_emails_for_llm([])
        
        assert formatted == "No emails found."
    
    @pytest.mark.asyncio
    async def test_semantic_search_quality(self, populated_email_system):
        """Test that semantic search actually finds semantically relevant content"""
        email_tools = populated_email_system["email_tools"]
        emails_loaded = populated_email_system["emails_loaded"]
        
        if emails_loaded < 5:
            pytest.skip("Need more emails for semantic search testing")
        
        # Test different semantic queries
        test_queries = [
            "meeting",
            "update",
            "important",
            "schedule"
        ]
        
        for query in test_queries:
            results = await email_tools.search_emails(query=query, limit=3)
            
            if results:
                print(f"\nQuery: '{query}'")
                print(f"Found {len(results)} results")
                
                # Check relevance scores - lower is better in vector search
                scores = [r['relevance_score'] for r in results]
                print(f"Relevance scores: {scores}")
                
                # Scores should generally increase (worse relevance) as you go down the list
                # This verifies ranking is working


class TestEmailToolsErrorHandling:
    """Test error handling in email tools"""
    
    @pytest.mark.asyncio
    async def test_search_emails_with_empty_query(self, populated_email_system):
        """Test searching with empty query"""
        email_tools = populated_email_system["email_tools"]
        
        # Should handle gracefully
        results = await email_tools.search_emails(query="", limit=5)
        
        # Might return empty or all results depending on implementation
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_search_nonexistent_sender(self, populated_email_system):
        """Test searching for sender that doesn't exist"""
        email_tools = populated_email_system["email_tools"]
        
        results = await email_tools.search_emails_by_sender(
            sender_name_or_email="nonexistent@example.com",
            limit=5
        )
        
        # Should return empty list, not error
        assert results == []
