"""Lifecycle management models."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_class import Base


class LifecycleTaskTemplate(Base):
    """Template for auto-created tasks on lifecycle transitions."""
    __tablename__ = "lifecycle_task_templates"

    id = Column(Integer, primary_key=True)
    to_state = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_offset_days = Column(Integer, nullable=False, default=7)
    assignment_strategy = Column(String(50), nullable=True, default="company_admin")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())
