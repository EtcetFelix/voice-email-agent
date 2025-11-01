# voice_agent/tools/email_tools.py
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
    
    async def search_emails(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for emails using natural language
        
        Args:
            query: Natural language search query (e.g., "emails about budget meetings")
            limit: Maximum number of results to return (default 5)
            
        Returns:
            List of email results with subject, sender, and content preview
        """
        try:
            # Search vector store for semantic matches
            vector_results = await self.vector_store.search_emails(
                query=query,
                limit=limit
            )
            
            if not vector_results:
                return []
            
            # Fetch full email details from database
            email_summaries = []
            for result in vector_results:
                email_id = result['email_id']
                email = await self.database.get_email_by_id(email_id)
                
                if email:
                    email_summaries.append({
                        "subject": email.subject or "No subject",
                        "from_name": email.from_name or "Unknown",
                        "from_email": email.from_email,
                        "date": str(email.date) if email.date else "Unknown date",
                        "body_preview": email.body[:200] if email.body else "No content",
                        "relevance_score": round(result['distance'], 2)
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
        """
        Search for emails from a specific sender
        
        Args:
            sender_name_or_email: Sender's name or email address
            query: Optional content query (e.g., "meeting notes")
            limit: Maximum number of results
            
        Returns:
            List of emails from the specified sender
        """
        try:
            # If no content query, just search by sender metadata
            if not query:
                query = "email"  # Generic query to get all from sender
            
            # Search with sender filter
            vector_results = await self.vector_store.search_similar(
                query=query,
                limit=limit,
                where_filters={"from_email": sender_name_or_email}
            )
            
            # If email filter didn't work, try filtering by name
            if not vector_results:
                vector_results = await self.vector_store.search_similar(
                    query=query,
                    limit=limit,
                    where_filters={"from_name": sender_name_or_email}
                )
            
            # Format results
            email_summaries = []
            for result in vector_results:
                email_id = result['email_id']
                email = await self.database.get_email_by_id(email_id)
                
                if email:
                    email_summaries.append({
                        "subject": email.subject or "No subject",
                        "from_name": email.from_name or "Unknown",
                        "from_email": email.from_email,
                        "date": str(email.date) if email.date else "Unknown date",
                        "body_preview": email.body[:200] if email.body else "No content",
                    })
            
            logger.info(f"Found {len(email_summaries)} emails from '{sender_name_or_email}'")
            return email_summaries
            
        except Exception as e:
            logger.error(f"Error searching emails by sender: {e}")
            return []
    
    async def get_recent_emails(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get most recent emails
        
        Args:
            limit: Number of recent emails to return
            
        Returns:
            List of recent emails
        """
        try:
            recent_emails = await self.database.email_repo.get_recent(limit=limit)
            
            email_summaries = []
            for email in recent_emails:
                email_summaries.append({
                    "subject": email.subject or "No subject",
                    "from_name": email.from_name or "Unknown",
                    "from_email": email.from_email,
                    "date": str(email.date) if email.date else "Unknown date",
                    "body_preview": email.body[:200] if email.body else "No content",
                })
            
            logger.info(f"Retrieved {len(email_summaries)} recent emails")
            return email_summaries
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []
    
    def format_emails_for_llm(self, emails: List[Dict[str, Any]]) -> str:
        """
        Format email results into a readable string for the LLM
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Formatted string of emails
        """
        if not emails:
            return "No emails found."
        
        formatted = f"Found {len(emails)} email(s):\n\n"
        for i, email in enumerate(emails, 1):
            formatted += f"{i}. Subject: {email['subject']}\n"
            formatted += f"   From: {email['from_name']} <{email['from_email']}>\n"
            formatted += f"   Date: {email['date']}\n"
            formatted += f"   Preview: {email['body_preview']}...\n\n"
        
        return formatted


# Function handlers for Pipecat
async def search_emails_handler(params: FunctionCallParams, email_tools: EmailSearchTools):
    """Handler for search_emails function"""
    query = params.arguments.get("query")
    limit = params.arguments.get("limit", 5)
    
    results = await email_tools.search_emails(query=query, limit=limit)
    formatted_results = email_tools.format_emails_for_llm(results)
    
    await params.result_callback(formatted_results)


async def search_emails_by_sender_handler(params: FunctionCallParams, email_tools: EmailSearchTools):
    """Handler for search_emails_by_sender function"""
    sender = params.arguments.get("sender")
    query = params.arguments.get("query")
    limit = params.arguments.get("limit", 5)
    
    results = await email_tools.search_emails_by_sender(
        sender_name_or_email=sender,
        query=query,
        limit=limit
    )
    formatted_results = email_tools.format_emails_for_llm(results)
    
    await params.result_callback(formatted_results)


async def get_recent_emails_handler(params: FunctionCallParams, email_tools: EmailSearchTools):
    """Handler for get_recent_emails function"""
    limit = params.arguments.get("limit", 5)
    
    results = await email_tools.get_recent_emails(limit=limit)
    formatted_results = email_tools.format_emails_for_llm(results)
    
    await params.result_callback(formatted_results)


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
    description="Get the most recent emails in the inbox",
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