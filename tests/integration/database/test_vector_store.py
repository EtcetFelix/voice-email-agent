# tests/test_vector_store.py
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from voice_agent.embeddings.vector_store import EmailSearchStore, create_email_search_store
from voice_agent.models import EmailModel


# Fixture: Create a mock email for testing
@pytest.fixture
def mock_email():
    """Create a realistic test email"""
    return EmailModel(
        id="test_email_001",
        thread_id="thread_abc123",
        subject="Q4 Budget Planning Meeting",
        body="Hi team,\n\nLet's schedule our quarterly budget planning meeting for next week. "
             "Please review the attached spreadsheet before the meeting.\n\nBest regards,\nJohn",
        from_name="John Doe",
        from_email="john.doe@company.com",
        to_name="Jane Smith",
        to_email="jane.smith@company.com",
        date=1698768000,  # Unix timestamp for Oct 31, 2023
        processed_at=datetime.now(timezone.utc)
    )


# Fixture: Create another mock email with different content
@pytest.fixture
def mock_email_2():
    """Create a second test email"""
    return EmailModel(
        id="test_email_002",
        thread_id="thread_xyz789",
        subject="Server Maintenance Notice",
        body="The production servers will undergo maintenance this weekend. "
             "Please plan accordingly.",
        from_name="IT Department",
        from_email="it@company.com",
        to_name="All Staff",
        to_email="staff@company.com",
        date=1698854400,
        processed_at=datetime.now(timezone.utc)
    )


# Fixture: Temporary directory for each test
@pytest.fixture
def temp_dir():
    """Create a temporary directory for ChromaDB persistence"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup after test
    shutil.rmtree(temp_path, ignore_errors=True)


class TestStoreInitialization:
    """Tests for store initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize_with_default_directory(self):
        """Test store initializes correctly with default persist directory"""
        # Create store with default directory
        store = EmailSearchStore()
        
        # Verify not initialized yet
        assert not store.initialized
        assert store.client is None
        assert store.collection is None
        
        # Initialize
        await store.init_store()
        
        # Verify initialization
        assert store.initialized
        assert store.client is not None
        assert store.collection is not None
        assert store.persist_directory == "./data/chroma_db"
        
        # Verify we can get count (proves collection works)
        count = await store.get_count()
        assert count >= 0
        
        # Cleanup
        await store.close()
        assert not store.initialized
    
    @pytest.mark.asyncio
    async def test_initialize_with_custom_directory(self, temp_dir):
        """Test store initializes correctly with custom persist directory"""
        # Create store with custom directory
        custom_path = str(Path(temp_dir) / "custom_chroma")
        store = EmailSearchStore(persist_directory=custom_path)
        
        # Initialize
        await store.init_store()
        
        # Verify initialization with custom path
        assert store.initialized
        assert store.persist_directory == custom_path
        assert store.client is not None
        assert store.collection is not None
        
        # Verify directory was created
        assert Path(custom_path).exists()
        
        # Verify collection works
        count = await store.get_count()
        assert count == 0  # Fresh store
        
        # Cleanup
        await store.close()
    
    @pytest.mark.asyncio
    async def test_repeated_initialization_is_idempotent(self, temp_dir):
        """Test that calling init_store multiple times doesn't break anything"""
        store = EmailSearchStore(persist_directory=temp_dir)
        
        # Initialize multiple times
        await store.init_store()
        first_client = store.client
        first_collection = store.collection
        
        await store.init_store()
        await store.init_store()
        
        # Should still be initialized with same objects
        assert store.initialized
        assert store.client is first_client
        assert store.collection is first_collection
        
        # Should still work
        count = await store.get_count()
        assert count == 0
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_factory_function_initialization(self, temp_dir):
        """Test create_email_search_store factory function"""
        # Use factory function
        store = await create_email_search_store(persist_directory=temp_dir)
        
        # Should be initialized and ready to use
        assert store.initialized
        assert store.client is not None
        assert store.collection is not None
        
        # Should work immediately
        count = await store.get_count()
        assert count == 0
        
        await store.close()


class TestCollectionMetadata:
    """Tests for ChromaDB collection creation and metadata"""
    
    @pytest.mark.asyncio
    async def test_collection_created_with_correct_metadata(self, temp_dir):
        """Test that ChromaDB collection is created with correct metadata"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Verify collection exists
        assert store.collection is not None
        
        # Verify collection name
        assert store.collection.name == "emails"
        
        # Verify collection metadata
        metadata = store.collection.metadata
        assert metadata is not None
        assert "description" in metadata
        assert metadata["description"] == "Email content embeddings for semantic search"
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_collection_persists_across_reinitializations(self, temp_dir):
        """Test that collection persists when store is closed and reopened"""
        # Create store and initialize
        store1 = EmailSearchStore(persist_directory=temp_dir)
        await store1.init_store()
        
        # Verify collection exists
        assert store1.collection.name == "emails"
        initial_count = await store1.get_count()
        
        # Close store
        await store1.close()
        
        # Create new store instance with same directory
        store2 = EmailSearchStore(persist_directory=temp_dir)
        await store2.init_store()
        
        # Verify collection still exists with same name and metadata
        assert store2.collection.name == "emails"
        assert store2.collection.metadata["description"] == "Email content embeddings for semantic search"
        
        # Verify count is the same (data persisted)
        new_count = await store2.get_count()
        assert new_count == initial_count
        
        await store2.close()


class TestSingleEmailAddition:
    """Tests for adding individual emails"""
    
    @pytest.mark.asyncio
    async def test_add_single_email_successfully(self, temp_dir, mock_email):
        """Test adding a single email to the store"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Verify store is empty
        initial_count = await store.get_count()
        assert initial_count == 0
        
        # Add email
        await store.add_email(mock_email)
        
        # Verify count increased
        new_count = await store.get_count()
        assert new_count == 1
        
        # Verify email exists
        exists = await store.email_exists(mock_email.id)
        assert exists is True
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_email_stores_correct_content(self, temp_dir, mock_email):
        """Test that email content is properly prepared and stored"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Add email
        await store.add_email(mock_email)
        
        # Retrieve the stored document
        result = store.collection.get(ids=[mock_email.id])
        
        # Verify document was stored
        assert len(result['ids']) == 1
        assert result['ids'][0] == mock_email.id
        
        # Verify content format
        stored_document = result['documents'][0]
        assert "Subject: Q4 Budget Planning Meeting" in stored_document
        assert "Body: Hi team" in stored_document
        assert "budget planning meeting" in stored_document
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_email_stores_correct_metadata(self, temp_dir, mock_email):
        """Test that email metadata is properly prepared and stored"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Add email
        await store.add_email(mock_email)
        
        # Retrieve the stored metadata
        result = store.collection.get(ids=[mock_email.id])
        
        # Verify metadata was stored
        assert len(result['metadatas']) == 1
        metadata = result['metadatas'][0]
        
        # Verify all expected metadata fields
        assert metadata['email_id'] == mock_email.id
        assert metadata['thread_id'] == mock_email.thread_id
        assert metadata['from_email'] == mock_email.from_email
        assert metadata['from_name'] == mock_email.from_name
        assert metadata['to_email'] == mock_email.to_email
        assert metadata['to_name'] == mock_email.to_name
        assert metadata['subject'] == mock_email.subject
        assert 'date' in metadata
        assert 'processed_at' in metadata
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_multiple_different_emails(self, temp_dir, mock_email, mock_email_2):
        """Test adding multiple different emails one by one"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Add first email
        await store.add_email(mock_email)
        assert await store.get_count() == 1
        
        # Add second email
        await store.add_email(mock_email_2)
        assert await store.get_count() == 2
        
        # Verify both exist
        assert await store.email_exists(mock_email.id)
        assert await store.email_exists(mock_email_2.id)
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_email_with_minimal_data(self, temp_dir):
        """Test adding an email with only required fields"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Create minimal email
        minimal_email = EmailModel(
            id="minimal_001",
            # All other fields will use defaults (empty strings, None)
        )
        
        # Should not raise an error
        await store.add_email(minimal_email)
        
        # Verify it was added
        assert await store.get_count() == 1
        assert await store.email_exists("minimal_001")
        
        # Verify it stored "Empty email" as content
        result = store.collection.get(ids=["minimal_001"])
        assert result['documents'][0] == "Empty email"
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_email_with_special_characters(self, temp_dir):
        """Test adding an email with special characters in content"""
        store = EmailSearchStore(persist_directory=temp_dir)
        await store.init_store()
        
        # Create email with special characters
        special_email = EmailModel(
            id="special_001",
            subject="Re: Important! 🚀 [URGENT]",
            body="Hello! Here's the link: https://example.com/path?query=1&foo=bar\n\n"
                 "Special chars: <>&\"'@#$%\n"
                 "Unicode: café, naïve, 日本語",
            from_name="José García",
            from_email="jose@example.com",
            to_email="test@example.com"
        )
        
        # Should not raise an error
        await store.add_email(special_email)
        
        # Verify it was added
        assert await store.get_count() == 1
        assert await store.email_exists("special_001")
        
        # Verify content is preserved
        result = store.collection.get(ids=["special_001"])
        stored_doc = result['documents'][0]
        assert "🚀" in stored_doc
        assert "café" in stored_doc
        assert "https://example.com" in stored_doc
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_email_persists_after_store_close(self, temp_dir, mock_email):
        """Test that added email persists after closing and reopening store"""
        # Create store and add email
        store1 = EmailSearchStore(persist_directory=temp_dir)
        await store1.init_store()
        await store1.add_email(mock_email)
        await store1.close()
        
        # Reopen store
        store2 = EmailSearchStore(persist_directory=temp_dir)
        await store2.init_store()
        
        # Verify email still exists
        assert await store2.get_count() == 1
        assert await store2.email_exists(mock_email.id)
        
        # Verify we can retrieve it
        result = store2.collection.get(ids=[mock_email.id])
        assert len(result['ids']) == 1
        assert result['ids'][0] == mock_email.id
        
        await store2.close()
