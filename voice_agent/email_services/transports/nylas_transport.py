# # voice_agent/email_services/transports/nylas_transport.py
# """
# Simplified Nylas transport for voice agent.
# """

# import logging
# from nylas import Client
# from .protocol import EmailSendResult, EmailTransport

# logger = logging.getLogger(__name__)


# class NylasTransport(EmailTransport):
#     """
#     Simplified Nylas transport - uses a single grant ID.
#     """

#     def __init__(self, api_key: str, grant_id: str):
#         """
#         Initialize Nylas transport.

#         Args:
#             api_key: Nylas API key
#             grant_id: Nylas grant ID for the email account
#         """
#         self.client = Client(api_key=api_key)
#         self.grant_id = grant_id

#     async def send_email(
#         self,
#         to_email: str,
#         subject: str,
#         html_body: str,
#         from_email: str | None = None,
#         user_id: str | None = None,
#         recipient_name: str | None = None,
#     ) -> EmailSendResult:
#         """Send email via Nylas API."""
#         try:
#             # Create draft
#             draft_request = {
#                 "to": [{"email": to_email, "name": recipient_name}] if recipient_name else [{"email": to_email}],
#                 "subject": subject,
#                 "body": html_body,
#             }
            
#             draft_response = self.client.drafts.create(
#                 self.grant_id, 
#                 request_body=draft_request
#             )
#             draft = draft_response.data
            
#             if not draft or not draft.id:
#                 return EmailSendResult(
#                     success=False,
#                     metadata={"transport": "nylas", "error": "Failed to create draft"}
#                 )
            
#             # Send draft
#             sent_response = self.client.drafts.send(self.grant_id, draft.id)
#             sent_message = sent_response.data
            
#             sender_email = None
#             if sent_message and sent_message.from_ and len(sent_message.from_) > 0:
#                 sender_email = sent_message.from_[0]["email"]
            
#             logger.info(f"Email sent via Nylas to {to_email}")
            
#             return EmailSendResult(
#                 success=True,
#                 external_message_id=sent_message.id if sent_message else draft.id,
#                 sender_email=sender_email,
#                 metadata={"transport": "nylas", "draft_id": draft.id}
#             )
            
#         except Exception as e:
#             logger.error(f"Failed to send via Nylas: {e}")
#             return EmailSendResult(
#                 success=False,
#                 metadata={"transport": "nylas", "error": str(e)}
#             )