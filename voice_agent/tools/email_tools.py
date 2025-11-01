# voice_agent/tools/email_tools.py
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from voice_agent.database_service import Database
from voice_agent.embeddings.vector_store import EmailSearchStore


class EmailSearchTools:
    """Tools for searching emails via voice commands"""
    
    def __init__(self, database: Database, vector_store: EmailSearchStore):
        self.database = database
        self.vector_store = vector_store
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove HTML tags and clean up text"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace and newlines
        text = ' '.join(text.split())
        return text
    
    async def search_emails(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for emails using natural language"""
        try:
            vector_results = await self.vector_store.search_emails(
                query=query,
                limit=limit
            )
            
            if not vector_results:
                return []
            
            email_summaries = []
            for result in vector_results:
                email_id = result['email_id']
                email = await self.database.get_email_by_id(email_id)
                
                if email:
                    # Clean the body text
                    body_clean = self._clean_text(email.body)
                    preview = body_clean[:200] if len(body_clean) > 200 else body_clean
                    
                    email_summaries.append({
                        "subject": email.subject or "No subject",
                        "from_name": email.from_name or "Unknown",
                        "from_email": email.from_email,
                        "preview": preview
                    })
            
            logger.info(f"Found {len(email_summaries)} emails for query: '{query}'")
            return email_summaries
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    async def search_emails_by_sender(
        self,
        sender_name_or_email: str,
        query: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for emails from a specific sender"""
        try:
            if not query:
                query = "email"
            
            vector_results = await self.vector_store.search_similar(
                query=query,
                limit=limit,
                where_filters={"from_email": sender_name_or_email}
            )
            
            if not vector_results:
                vector_results = await self.vector_store.search_similar(
                    query=query,
                    limit=limit,
                    where_filters={"from_name": sender_name_or_email}
                )
            
            email_summaries = []
            for result in vector_results:
                email_id = result['email_id']
                email = await self.database.get_email_by_id(email_id)
                
                if email:
                    body_clean = self._clean_text(email.body)
                    preview = body_clean[:200] if len(body_clean) > 200 else body_clean
                    
                    email_summaries.append({
                        "subject": email.subject or "No subject",
                        "from_name": email.from_name or "Unknown",
                        "from_email": email.from_email,
                        "preview": preview
                    })
            
            logger.info(f"Found {len(email_summaries)} emails from '{sender_name_or_email}'")
            return email_summaries
            
        except Exception as e:
            logger.error(f"Error searching emails by sender: {e}")
            return []
    
    async def get_recent_emails(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most recent emails"""
        try:
            recent_emails = await self.database.email_repo.get_recent(limit=limit)
            
            email_summaries = []
            for email in recent_emails:
                body_clean = self._clean_text(email.body)
                preview = body_clean[:200] if len(body_clean) > 200 else body_clean
                
                email_summaries.append({
                    "subject": email.subject or "No subject",
                    "from_name": email.from_name or "Unknown",
                    "from_email": email.from_email,
                    "preview": preview
                })
            
            logger.info(f"Retrieved {len(email_summaries)} recent emails")
            return email_summaries
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []


# Function handlers - return JSON, not formatted strings!
async def search_emails_handler(params: FunctionCallParams, email_tools: EmailSearchTools):
    """Handler for search_emails function"""
    logger.info(f"🔍 Searching emails with query: {params.arguments.get('query')}")
    
    query = params.arguments.get("query")
    limit = params.arguments.get("limit", 5)
    
    results = await email_tools.search_emails(query=query, limit=limit)
    
    logger.info(f"📧 Found {len(results)} emails, returning to LLM")
    
    # Return structured JSON - let the LLM format it naturally
    await params.result_callback(results)


async def search_emails_by_sender_handler(params: FunctionCallParams, email_tools: EmailSearchTools):
    """Handler for search_emails_by_sender function"""
    logger.info(f"🔍 Searching emails by sender: {params.arguments.get('sender')}")
    
    sender = params.arguments.get("sender")
    query = params.arguments.get("query")
    limit = params.arguments.get("limit", 5)
    
    results = await email_tools.search_emails_by_sender(
        sender_name_or_email=sender,
        query=query,
        limit=limit
    )
    
    logger.info(f"📧 Found {len(results)} emails from sender, returning to LLM")
    
    # Return structured JSON
    await params.result_callback(results)


async def get_recent_emails_handler(params: FunctionCallParams, email_tools: EmailSearchTools):
    """Handler for get_recent_emails function"""
    logger.info(f"🔍 Getting recent emails (limit: {params.arguments.get('limit', 5)})")
    
    limit = params.arguments.get("limit", 5)
    
    results = await email_tools.get_recent_emails(limit=limit)
    
    logger.info(f"📧 Found {len(results)} recent emails, returning to LLM")
    
    # Return structured JSON - LLM will create natural summary
    await params.result_callback(results)


# Define function schemas using Pipecat's standard schema
search_emails_schema = FunctionSchema(
    name="search_emails",
    description="Search for emails using natural language. Use this when the user asks about specific topics, keywords, or content in their emails.",
    properties={
        "query": {
            "type": "string",
            "description": "Natural language search query (e.g., 'budget meetings', 'project updates', 'from my manager')"
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results to return (default 5)"
        }
    },
    required=["query"]
)

search_emails_by_sender_schema = FunctionSchema(
    name="search_emails_by_sender",
    description="Search for emails from a specific person or email address",
    properties={
        "sender": {
            "type": "string",
            "description": "Name or email address of the sender"
        },
        "query": {
            "type": "string",
            "description": "Optional: specific content to search for from this sender"
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results to return (default 5)"
        }
    },
    required=["sender"]
)

get_recent_emails_schema = FunctionSchema(
    name="get_recent_emails",
    description="Get the most recent emails in the inbox. Returns email subject, sender name, sender email, and preview of content.",
    properties={
        "limit": {
            "type": "integer",
            "description": "Number of recent emails to retrieve (default 5)"
        }
    },
    required=[]
)

# Create ToolsSchema with all email search functions
EMAIL_SEARCH_TOOLS = ToolsSchema(
    standard_tools=[
        search_emails_schema,
        search_emails_by_sender_schema,
        get_recent_emails_schema
    ]
)