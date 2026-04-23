"""
KontentPyper - Scheduled Job Model
Stores user-defined cron schedules for autonomous pipeline runs.
Max tier only.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class ScheduledJob(Base):
    """
    Persistent record of a user's automation schedule.

    cron_expression format:
      - 'daily_8am'     -> Run every day at 08:00 UTC
      - 'daily_12pm'    -> Run every day at 12:00 UTC
      - 'daily_6pm'     -> Run every day at 18:00 UTC
      - 'weekdays_9am'  -> Mon-Fri at 09:00 UTC
      - 'custom'        -> Uses cron_hour + cron_minute + cron_dow fields
    """
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One schedule per user
    )

    # Schedule config
    schedule_preset = Column(String, server_default=text("'daily_8am'"))
    cron_hour = Column(Integer, server_default=text("8"))
    cron_minute = Column(Integer, server_default=text("0"))
    cron_dow = Column(String, server_default=text("'*'"))  # '*' = every day, 'mon-fri' = weekdays

    is_active = Column(Boolean, server_default=text("FALSE"))

    # Tracking
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    total_runs = Column(Integer, server_default=text("0"))
    last_run_status = Column(String, nullable=True)  # 'success' | 'error' | 'pending_review'

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", backref="scheduled_jobs")
