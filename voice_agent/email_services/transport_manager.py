# voice_agent/email_services/transport_manager.py
"""
Simple transport manager for voice agent email sending.
Uses environment configuration to select transport.
"""

import logging
from voice_agent.config import settings
from .transports.mailpit_transport import MailpitTransport
# from .transports.nylas_transport import NylasTransport
from .transports.protocol import EmailTransport

logger = logging.getLogger(__name__)


class SimpleTransportManager:
    """
    Simplified transport manager that selects based on environment only.
    No user-specific transport selection needed for voice agent.
    """

    def __init__(self, nylas_api_key: str | None = None, nylas_grant_id: str | None = None):
        """
        Initialize SimpleTransportManager.

        Args:
            nylas_api_key: Nylas API key for production transport
            nylas_grant_id: Nylas grant ID for the email account
        """
        self.email_mode = getattr(settings, 'EMAIL_MODE', 'development')  # default to dev
        
        # Initialize test transport (always available)
        self.test_transport = MailpitTransport(
            smtp_host=getattr(settings, 'MAILPIT_SMTP_HOST', '127.0.0.1'),
            smtp_port=getattr(settings, 'MAILPIT_SMTP_PORT', 1025),
            from_email=getattr(settings, 'TEST_FROM_EMAIL', 'alice@voiceagent.local'),
        )
        
        # # Initialize production transport if credentials provided
        # self.production_transport = None
        # if nylas_api_key and nylas_grant_id:
        #     self.production_transport = NylasTransport(
        #         api_key=nylas_api_key,
        #         grant_id=nylas_grant_id
        #     )
        #     logger.info("Nylas production transport initialized")
        
        logger.info(f"TransportManager initialized with mode: {self.email_mode}")

    def get_transport(self) -> EmailTransport:
        """
        Get the appropriate email transport based on environment.
        
        Returns:
            EmailTransport: The transport to use
        """
        if self.email_mode in ['test', 'development']:
            logger.debug("Using test transport (Mailpit)")
            return self.test_transport
        
        if self.production_transport:
            logger.debug("Using production transport (Nylas)")
            return self.production_transport
        
        # Fallback to test if production not configured
        logger.warning("Production mode but no production transport configured, using test transport")
        return self.test_transport