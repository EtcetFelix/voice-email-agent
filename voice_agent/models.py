# models.py
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum

class EmailModel(BaseModel):
    """Email model for database operations"""
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "nylas_email_123",
                "thread_id": "thread_456", 
                "subject": "Important Meeting",
                "body": "Let's schedule a meeting...",
                "from_name": "John Doe",
                "from_email": "john@example.com",
                "to_name": "Jane Smith", 
                "to_email": "jane@example.com",
                "date": 1640995200
            }
        }
    )
    
    # Core fields
    id: str = Field(..., description="Nylas email ID")
    thread_id: Optional[str] = Field(None, description="Nylas thread ID")
    subject: str = Field(default="", description="Email subject")
    body: str = Field(default="", description="Email body content")
    
    # Sender info
    from_name: str = Field(default="", description="Sender display name")
    from_email: str = Field(default="", description="Sender email address")
    
    # Recipient info  
    to_name: str = Field(default="", description="Primary recipient display name")
    to_email: str = Field(default="", description="Primary recipient email address")
    
    # Timestamps
    date: Optional[int] = Field(None, description="Email date as Unix timestamp")
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Record creation time")
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Record update time")
    
    # Processing metadata
    processed_at: Optional[datetime] = Field(None, description="When email was processed")
    
    @field_validator('from_email', 'to_email')
    def validate_email_format(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

class ETLJobStatus(str, Enum):
    """ETL job status enumeration"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

class ETLJobModel(BaseModel):
    """ETL Job model for tracking processing jobs"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_type": "email_extraction",
                "status": "running", 
                "records_processed": 150
            }
        }
    )
    
    id: Optional[str] = Field(None, description="Job ID")
    job_type: str = Field(..., description="Type of ETL job")
    status: ETLJobStatus = Field(default=ETLJobStatus.PENDING, description="Job status")
    records_processed: int = Field(default=0, description="Number of records processed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Timestamps
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")