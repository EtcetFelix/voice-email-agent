# app/email_services/transports/protocol.py
"""
Email transport protocol - defines interface for different email sending implementations
"""

from abc import ABC, abstractmethod
from typing import Any, List, NamedTuple


class EmailSendResult(NamedTuple):
    """
    Result of email sending operation.

    Attributes:
        success: Whether the email was sent successfully
        external_message_id: Transport-specific message ID (e.g., Nylas draft ID, SMTP message ID)
        sender_email: The actual email address used as sender
        metadata: Additional transport-specific information
    """

    success: bool
    external_message_id: str | None = None
    sender_email: str | None = None
    metadata: dict[str, Any] | None = None


class EmailRequest(NamedTuple):
    """
    Email request for batch operations.
    
    Contains all the parameters needed to send a single email.
    """
    to_email: str
    subject: str
    html_body: str
    from_email: str | None = None
    user_id: str | None = None
    recipient_name: str | None = None


class EmailTransport(ABC):
    """
    Abstract base class for email transport implementations.

    Transport layer handles the actual sending mechanism (Nylas, SMTP, Inbucket, etc.)
    Business logic (signatures, formatting, etc.) is handled by EmailService.
    """

    @abstractmethod
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
        Send an email via this transport.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML formatted email body (including signature)
            from_email: Optional sender email (transport-specific handling)
            user_id: Optional user ID for transport-specific needs (e.g. Nylas grants)
            recipient_name: Optional recipient name for 'to' protocol header

        Returns:
            EmailSendResult: Result containing success status, external message ID,
                           actual sender email used, and any additional metadata

        Raises:
            Exception: Transport-specific exceptions for connection/auth issues
        """
        pass

    async def send_batch(
        self,
        emails: List[EmailRequest],
    ) -> List[EmailSendResult]:
        """
        Send multiple emails via this transport.

        Default implementation sends emails individually. Transports that support
        efficient batching (like Resend) should override this method.

        Args:
            emails: List of email requests to send

        Returns:
            List[EmailSendResult]: Results for each email in the same order as input

        Raises:
            Exception: Transport-specific exceptions for connection/auth issues
        """
        results = []
        for email in emails:
            result = await self.send_email(
                to_email=email.to_email,
                subject=email.subject,
                html_body=email.html_body,
                from_email=email.from_email,
                user_id=email.user_id,
                recipient_name=email.recipient_name,
            )
            results.append(result)
        return results