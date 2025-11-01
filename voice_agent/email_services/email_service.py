# voice_agent/email_services/email_service.py
"""
Simplified email service for voice agent.
No signature lookup or user settings needed.
"""

import logging
from voice_agent.email_services.transports.protocol import EmailTransport

logger = logging.getLogger(__name__)


class EmailService:
    """
    Simplified email service for voice agent.
    Handles email formatting and delegates sending to transport.
    """

    def __init__(self, transport: EmailTransport):
        """
        Initialize EmailService with transport.

        Args:
            transport: Email transport implementation
        """
        self.transport = transport

    async def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        from_email: str | None = None,
        recipient_name: str | None = None,
    ) -> bool:
        """
        Send a plain text email.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            message: Plain text message body
            from_email: Optional sender email
            recipient_name: Optional recipient name

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Format message to HTML
            html_body = self.format_email_message(message)
            
            # Send via transport
            result = await self.transport.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                from_email=from_email,
                recipient_name=recipient_name,
            )

            if result.success:
                logger.info(f"✅ Email sent to {to_email}: {subject}")
            else:
                logger.error(f"❌ Email send failed to {to_email}: {result.metadata}")

            return result.success

        except Exception as e:
            logger.exception(f"Failed to send email to {to_email}: {e}")
            return False

    def format_email_message(self, message_text: str) -> str:
        """
        Format plain text message to HTML for email.

        Args:
            message_text: Plain text message content

        Returns:
            str: HTML formatted content
        """
        # Split into paragraphs
        paragraphs = message_text.split("\n\n")
        
        # Format each paragraph
        formatted_paragraphs = []
        for paragraph in paragraphs:
            lines = paragraph.split("\n")
            formatted_paragraph = "<br>".join(lines)
            formatted_paragraphs.append(formatted_paragraph)
        
        # Join with double breaks
        html_content = "<br><br>".join(formatted_paragraphs)
        
        # Wrap in div
        return f'<div dir="ltr">{html_content}</div>'