"""
Billing webhook/event persistence models.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import text

from app.core.database import Base


class PaymentWebhookEvent(Base):
    """
    Idempotency and audit log for inbound payment-provider webhook events.
    """

    __tablename__ = "payment_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)  # e.g. paystack
    provider_event_id = Column(String, nullable=False, unique=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    processed = Column(Boolean, server_default=text("FALSE"), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )
