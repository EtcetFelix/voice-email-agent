# voice_agent/email_services/transports/mailpit_transport.py
"""
Mailpit transport implementation for testing email sending via Mailpit SMTP.
"""

import logging
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from .protocol import EmailSendResult, EmailTransport


logger = logging.getLogger(__name__)


class MailpitTransport(EmailTransport):
    """
    Email transport implementation using Mailpit SMTP for testing.

    Sends emails to local Mailpit instance via SMTP, where they can be
    viewed in the Mailpit web UI at http://127.0.0.1:8025
    """

    def __init__(
        self,
        smtp_host: str = "127.0.0.1",
        smtp_port: int = 1025,
        from_email: str = "alice@voiceagent.local",
    ):
        """
        Initialize Mailpit transport.

        Args:
            smtp_host: Mailpit SMTP host (default: 127.0.0.1)
            smtp_port: Mailpit SMTP port (default: 1025)
            from_email: Default sender email for test emails
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.default_from_email = from_email

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: str | None = None,
        user_id: str | None = None,
        recipient_name: str | None = None,
    ) -> EmailSendResult:
        """
        Send email via Mailpit SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML formatted email body
            from_email: Sender email (uses default if None)
            user_id: Not used for Mailpit, but kept for interface compatibility
            recipient_name: Recipient name for display

        Returns:
            EmailSendResult: Result with success status, message ID, and sender email
        """
        # Determine the actual sender email that will be used
        actual_sender_email = from_email or self.default_from_email

        try:
            # Create the email message
            message = self._create_email_message(
                to_email=to_email,
                from_email=actual_sender_email,
                subject=subject,
                html_body=html_body,
                recipient_name=recipient_name,
            )

            # Send via SMTP to Mailpit
            smtp_response = await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=False,  # Mailpit doesn't require TLS
                start_tls=False,
            )

            # Extract message ID from message headers
            external_message_id = None
            if "Message-ID" in message:
                external_message_id = message["Message-ID"]

            # Create metadata with transport-specific info
            metadata = {
                "transport": "mailpit",
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "smtp_response": str(smtp_response) if smtp_response else None,
                "user_id": user_id,
            }

            logger.info(f"📧 Email sent to Mailpit: {to_email} | Subject: {subject}")
            logger.info(f"   View at: http://127.0.0.1:8025")

            return EmailSendResult(
                success=True,
                external_message_id=external_message_id,
                sender_email=actual_sender_email,
                metadata=metadata,
            )

        except Exception as e:
            logger.exception(f"Failed to send email to Mailpit: {e}")

            # Return failure result with whatever info we have
            return EmailSendResult(
                success=False,
                external_message_id=None,
                sender_email=actual_sender_email,
                metadata={
                    "transport": "mailpit",
                    "error": str(e),
                    "user_id": user_id,
                },
            )

    def _create_email_message(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        recipient_name: str | None = None,
    ) -> MIMEMultipart:
        """
        Create email message for SMTP sending.

        Args:
            to_email: Recipient email address
            from_email: Sender email address
            subject: Email subject line
            html_body: HTML formatted email body
            recipient_name: Optional recipient name

        Returns:
            MIMEMultipart: Email message ready for SMTP
        """
        # Create multipart message
        message = MIMEMultipart("alternative")

        # Set headers
        message["Subject"] = subject
        message["From"] = from_email

        # Format To field with name if provided
        if recipient_name:
            message["To"] = f"{recipient_name} <{to_email}>"
        else:
            message["To"] = to_email

        # Add a Message-ID header for tracking
        message_id = f"<{uuid.uuid4()}@{time.time()}>"
        message["Message-ID"] = message_id

        # Add plain text version first (for email clients that prefer it)
        text_body = self._html_to_text(html_body)
        text_part = MIMEText(text_body, "plain")
        message.attach(text_part)

        # Add HTML content
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        return message

    def _html_to_text(self, html_content: str) -> str:
        """
        Simple HTML to text conversion for email compatibility.

        Args:
            html_content: HTML formatted content

        Returns:
            str: Plain text version
        """
        import re

        # Replace <br> tags with newlines
        text = re.sub(r"<br\s*/?>", "\n", html_content, flags=re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Clean up extra whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = text.strip()

        return text