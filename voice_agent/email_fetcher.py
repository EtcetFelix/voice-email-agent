# email_fetcher.py
import asyncio
import aiohttp
from typing import List, Dict, Optional
from loguru import logger
from voice_agent.config import settings

class NylasEmailFetcher:
    """Handles fetching emails from Nylas API"""
    
    def __init__(self, nylas_api_key: str = None):
        self.nylas_api_key = nylas_api_key or settings.NYLAS_API_KEY
        self.base_url = "https://api.us.nylas.com/v3"
        
        # Configuration
        self.EMAILS_PER_PAGE = 5  # API maximum is 200
        self.MAX_EMAILS = 10      # Default target
        
    async def fetch_emails(self, grant_id: str, max_emails: Optional[int] = None, emails_per_page: Optional[int] = None) -> List[Dict]:
        """
        Fetch emails from Nylas API with pagination
        
        Args:
            grant_id: The Nylas grant ID
            max_emails: Maximum number of emails to fetch (overrides default)
            
        Returns:
            List of email dictionaries
        """
        max_emails = max_emails or self.MAX_EMAILS
        emails_per_page = emails_per_page or self.EMAILS_PER_PAGE
        all_emails = []
        page_token = None
        
        async with aiohttp.ClientSession() as session:
            while len(all_emails) < max_emails:
                # Build URL and params
                url = f"{self.base_url}/grants/{grant_id}/messages"
                params = {
                    "limit": min(emails_per_page, max_emails - len(all_emails))
                }
                
                if page_token:
                    params["page_token"] = page_token
                
                # Make API call
                headers = {
                    "Authorization": f"Bearer {self.nylas_api_key}",
                    "Content-Type": "application/json"
                }
                
                logger.debug(f"Fetching emails page, current count: {len(all_emails)}")
                
                try:
                    async with session.get(url, params=params, headers=headers) as response:
                        response.raise_for_status()
                        data = await response.json()
                except aiohttp.ClientError as e:
                    logger.error(f"HTTP error fetching emails: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error fetching emails: {e}")
                    raise
                
                # Extract emails from response
                emails = data.get("data", [])
                all_emails.extend(emails)
                
                logger.info(f"Retrieved {len(emails)} emails, total: {len(all_emails)}")
                
                # Check if we should continue
                page_token = data.get("next_cursor")
                if not page_token:
                    logger.info("No more pages available")
                    break
                    
                if len(all_emails) >= max_emails:
                    logger.info(f"Reached max emails limit: {max_emails}")
                    break
        
        return all_emails[:max_emails]