# test_fetch_emails.py
import asyncio
import pytest
from voice_agent.email_fetcher import NylasEmailFetcher
from voice_agent.config import settings

@pytest.mark.asyncio
async def test_fetch_emails_integration():
    """Integration test for email fetching"""
    # Setup
    fetcher = NylasEmailFetcher()
    grant_id = settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
    
    # Test fetching a small number of emails
    emails = await fetcher.fetch_emails(grant_id, max_emails=5)
    
    # Assertions
    assert isinstance(emails, list)
    assert len(emails) <= 5
    
    if emails:  # If there are emails
        email = emails[0]
        
        # Check that emails have expected structure
        assert "id" in email
        assert "subject" in email
        assert "from" in email
        assert "to" in email
        assert "date" in email
        
        print(f"Successfully fetched {len(emails)} emails")
        print(f"First email subject: {email.get('subject', 'No subject')}")
    else:
        print("No emails found (might be expected for test account)")

