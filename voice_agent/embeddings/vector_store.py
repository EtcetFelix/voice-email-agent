# embeddings/vector_store.py
import chromadb
from typing import List, Dict, Optional, Any
from loguru import logger
from voice_agent.models import EmailModel


class EmailSearchStore:
    """ChromaDB-backed semantic search for emails"""
    
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """
        Initialize the email search store
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.initialized = False
        
    async def init_store(self):
        """Initialize the ChromaDB client and collection"""
        if self.initialized:
            logger.debug("Store already initialized")
            return
            
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name="emails",
                metadata={"description": "Email content embeddings for semantic search"}
            )
            self.initialized = True
            logger.info(f"Initialized email search store at {self.persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize search store: {e}")
            raise
    
    def _ensure_initialized(self):
        """Check that store is initialized before operations"""
        if not self.initialized or not self.collection:
            raise RuntimeError("Search store not initialized. Call init_store() first.")
    
    def _prepare_email_content(self, email: EmailModel) -> str:
        """
        Prepare email content for embedding
        
        Args:
            email: EmailModel object
            
        Returns:
            Combined text content for embedding
        """
        content_parts = []
        
        if email.subject and email.subject.strip():
            content_parts.append(f"Subject: {email.subject.strip()}")
        
        if email.body and email.body.strip():
            content_parts.append(f"Body: {email.body.strip()}")
        
        return "\n\n".join(content_parts) if content_parts else "Empty email"
    
    def _prepare_email_metadata(self, email: EmailModel) -> Dict[str, Any]:
        """
        Prepare email metadata for filtering
        
        Args:
            email: EmailModel object
            
        Returns:
            Metadata dictionary for ChromaDB
        """
        metadata = {
            "email_id": email.id,
            "thread_id": email.thread_id or "",
            "from_email": email.from_email or "",
            "from_name": email.from_name or "",
            "to_email": email.to_email or "",
            "to_name": email.to_name or "",
            "subject": email.subject or "",
        }
        
        if email.date:
            metadata["date"] = str(email.date)
        
        if email.processed_at:
            metadata["processed_at"] = email.processed_at.isoformat()
            
        return metadata
    
    async def add_email(self, email: EmailModel) -> None:
        """
        Add a single email to the search store
        
        Args:
            email: EmailModel to add
        """
        self._ensure_initialized()
        
        try:
            content = self._prepare_email_content(email)
            metadata = self._prepare_email_metadata(email)
            
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[email.id]
            )
            
            logger.debug(f"Added email {email.id} to search store")
            
        except Exception as e:
            logger.error(f"Failed to add email {email.id}: {e}")
            raise
    
    async def add_emails_batch(self, emails: List[EmailModel]) -> None:
        """
        Add multiple emails to the search store efficiently
        
        Args:
            emails: List of EmailModel objects to add
        """
        self._ensure_initialized()
        
        if not emails:
            logger.debug("No emails to add")
            return
        
        try:
            documents = [self._prepare_email_content(email) for email in emails]
            metadatas = [self._prepare_email_metadata(email) for email in emails]
            ids = [email.id for email in emails]
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added batch of {len(emails)} emails to search store")
            
        except Exception as e:
            logger.error(f"Failed to add email batch: {e}")
            raise
    
    async def search_similar(
        self, 
        query: str, 
        limit: int = 5, 
        where_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar emails
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            where_filters: Optional metadata filters (e.g., {"from_email": "john@example.com"})
            
        Returns:
            List of search results with email IDs, distances, and metadata
        """
        self._ensure_initialized()
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filters
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, email_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        'email_id': email_id,
                        'distance': results['distances'][0][i],
                        'document': results['documents'][0][i] if results['documents'] else None,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    })
            
            logger.debug(f"Found {len(formatted_results)} emails for query: '{query}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            raise
    
    async def search_emails(
        self, 
        query: str, 
        limit: int = 5,
        from_email: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for emails using natural language query with optional filters
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            from_email: Optional filter by sender email
            thread_id: Optional filter by thread ID
            
        Returns:
            List of search results with email IDs and metadata
        """
        where_filters = {}
        if from_email:
            where_filters["from_email"] = from_email
        if thread_id:
            where_filters["thread_id"] = thread_id
        
        return await self.search_similar(
            query=query,
            limit=limit,
            where_filters=where_filters if where_filters else None
        )
    
    async def search_by_sender(
        self, 
        query: str, 
        sender_email: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for emails from a specific sender
        
        Args:
            query: Natural language search query
            sender_email: Email address to filter by
            limit: Maximum number of results
            
        Returns:
            List of search results from the specified sender
        """
        return await self.search_emails(
            query=query,
            limit=limit,
            from_email=sender_email
        )
    
    async def search_by_thread(
        self, 
        query: str, 
        thread_id: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search within a specific email thread
        
        Args:
            query: Natural language search query
            thread_id: Thread ID to search within
            limit: Maximum number of results
            
        Returns:
            List of search results from the specified thread
        """
        return await self.search_emails(
            query=query,
            limit=limit,
            thread_id=thread_id
        )
    
    async def find_emails_about_topic(
        self, 
        topic: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find emails about a specific topic (conversational method name)
        
        Args:
            topic: Topic to search for (e.g., "budget meetings", "server issues")
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        return await self.search_emails(query=topic, limit=limit)
    
    async def get_count(self) -> int:
        """
        Get the total number of emails in the search store
        
        Returns:
            Number of emails stored
        """
        self._ensure_initialized()
        
        try:
            count = self.collection.count()
            logger.debug(f"Search store contains {count} emails")
            return count
        except Exception as e:
            logger.error(f"Failed to get email count: {e}")
            raise
    
    async def email_exists(self, email_id: str) -> bool:
        """
        Check if an email exists in the search store
        
        Args:
            email_id: Email ID to check
            
        Returns:
            True if email exists, False otherwise
        """
        self._ensure_initialized()
        
        try:
            result = self.collection.get(ids=[email_id])
            exists = len(result['ids']) > 0
            logger.debug(f"Email {email_id} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check if email {email_id} exists: {e}")
            return False
    
    async def delete_email(self, email_id: str) -> None:
        """
        Delete an email from the search store
        
        Args:
            email_id: Email ID to delete
        """
        self._ensure_initialized()
        
        try:
            self.collection.delete(ids=[email_id])
            logger.info(f"Deleted email {email_id} from search store")
        except Exception as e:
            logger.error(f"Failed to delete email {email_id}: {e}")
            raise
    
    async def close(self):
        """Close the search store connection"""
        # ChromaDB with PersistentClient doesn't need explicit closing
        # Data is automatically persisted
        self.initialized = False
        logger.info("Search store closed")
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry"""
        await self.init_store()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Factory function for easy initialization
async def create_email_search_store(
    persist_directory: str = "./data/chroma_db"
) -> EmailSearchStore:
    """
    Factory function to create and initialize an EmailSearchStore
    
    Args:
        persist_directory: Directory to persist ChromaDB data
        
    Returns:
        Initialized EmailSearchStore instance
    """
    store = EmailSearchStore(persist_directory=persist_directory)
    await store.init_store()
    return store
