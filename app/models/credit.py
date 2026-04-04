"""
KontentPyper - Credit Transaction Model
Audit log for every credit event (workflow run, video regeneration, top-up).
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class CreditTransaction(Base):
    """
    Immutable audit log of every credit-related event.

    action_type values:
      - workflow_run   : credits consumed by running the autonomous pipeline
      - regenerate     : credits consumed by regenerating a video in HITL
      - topup          : credits added via credit pack purchase
      - monthly_reset  : credits granted at subscription renewal
      - daily_reset    : daily run counter reset to 0
    """
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action_type = Column(String, nullable=False, index=True)
    # Positive for topup/reset, negative for consumption
    credits_delta = Column(Integer, nullable=False)
    credits_before = Column(Integer, nullable=False)
    credits_after = Column(Integer, nullable=False)

    # Which AI model was used (if applicable)
    model_used = Column(String, nullable=True)

    # Optional context (e.g., "Regenerated video for asset #42")
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", backref="credit_transactions")
