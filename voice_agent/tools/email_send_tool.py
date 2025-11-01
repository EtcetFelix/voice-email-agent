# voice_agent/tools/email_send_tool.py
"""
Email sending tool for voice agent function calling.
"""

import logging
from typing import Optional
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from voice_agent.email_services.email_service import EmailService

logger = logging.getLogger(__name__)


async def send_email_handler(params: FunctionCallParams, email_service: EmailService):
    """Handler for send_email function"""
    logger.info(f"📧 Sending email to: {params.arguments.get('to_email')}")
    
    to_email = params.arguments.get("to_email")
    subject = params.arguments.get("subject")
    message = params.arguments.get("message")
    recipient_name = params.arguments.get("recipient_name")
    
    success = await email_service.send_email(
        to_email=to_email,
        subject=subject,
        message=message,
        recipient_name=recipient_name,
    )
    
    if success:
        result = {
            "success": True,
            "message": f"Email sent successfully to {to_email}"
        }
    else:
        result = {
            "success": False,
            "message": f"Failed to send email to {to_email}"
        }
    
    logger.info(f"📧 Email send result: {result}")
    await params.result_callback(result)


# Define function schema
send_email_schema = FunctionSchema(
    name="send_email",
    description="Send an email to a recipient. Use this when the user asks to send an email, draft an email, or compose a message to someone.",
    properties={
        "to_email": {
            "type": "string",
            "description": "Email address of the recipient"
        },
        "subject": {
            "type": "string",
            "description": "Subject line of the email"
        },
        "message": {
            "type": "string",
            "description": "Body content of the email (plain text)"
        },
        "recipient_name": {
            "type": "string",
            "description": "Name of the recipient (optional)"
        }
    },
    required=["to_email", "subject", "message"]
)

# Export tools schema
EMAIL_SEND_TOOLS = ToolsSchema(standard_tools=[send_email_schema])