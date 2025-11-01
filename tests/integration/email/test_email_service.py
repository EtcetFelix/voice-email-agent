# tests/integration/email/test_email_service.py
"""
Integration tests for email sending service with Mailpit.
"""

import pytest
import pytest_asyncio
from voice_agent.email_services.email_service import EmailService
from voice_agent.email_services.transports.mailpit_transport import MailpitTransport


@pytest_asyncio.fixture
async def email_service():
    """Create email service with Mailpit transport"""
    transport = MailpitTransport()
    service = EmailService(transport=transport)
    return service


class TestEmailService:
    """Test EmailService with Mailpit transport"""
    
    @pytest.mark.asyncio
    async def test_send_basic_email(self, email_service):
        """Test sending a basic plain text email"""
        success = await email_service.send_email(
            to_email="test@example.com",
            subject="Test Email",
            message="Hello, this is a test email!",
        )
        
        assert success is True
        print(f"✅ Basic email sent - view at http://localhost:8025")
    
    @pytest.mark.asyncio
    async def test_send_email_with_paragraphs(self, email_service):
        """Test email with multiple paragraphs"""
        message = """Hello,

This is the first paragraph.

This is the second paragraph.

Best regards,
Alice"""
        
        success = await email_service.send_email(
            to_email="paragraphs@example.com",
            subject="Multi-paragraph Email",
            message=message,
        )
        
        assert success is True
        print(f"✅ Multi-paragraph email sent")
    
    @pytest.mark.asyncio
    async def test_send_email_with_recipient_name(self, email_service):
        """Test sending email with recipient name"""
        success = await email_service.send_email(
            to_email="john@example.com",
            subject="Named Recipient Test",
            message="Hello John!\n\nThis email is addressed to you specifically.",
            recipient_name="John Doe",
        )
        
        assert success is True
        print(f"✅ Email sent with recipient name")
    
    @pytest.mark.asyncio
    async def test_send_multiple_emails(self, email_service):
        """Test sending multiple emails in sequence"""
        recipients = [
            ("user1@example.com", "User One", "Message for User One"),
            ("user2@example.com", "User Two", "Message for User Two"),
            ("user3@example.com", "User Three", "Message for User Three"),
        ]
        
        for email, name, message in recipients:
            success = await email_service.send_email(
                to_email=email,
                subject=f"Test for {name}",
                message=message,
                recipient_name=name,
            )
            assert success is True
        
        print(f"✅ Sent {len(recipients)} emails successfully")
    
    @pytest.mark.asyncio
    async def test_send_email_with_custom_sender(self, email_service):
        """Test sending email with custom from address"""
        success = await email_service.send_email(
            to_email="recipient@example.com",
            subject="Custom Sender Test",
            message="This email is from a custom sender address.",
            from_email="custom@sender.com",
        )
        
        assert success is True
        print(f"✅ Email sent from custom sender")

