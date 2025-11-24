"""
Status History Model

Tracks all status changes for audit trail and rollback capability.
"""
from sqlalchemy import Column, String, Integer, JSON, TIMESTAMP
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.sql import func
from model.base import Base


class StatusHistory(Base):
    """
    Records all status changes across all entities.

    Provides:
    - Complete audit trail
    - Rollback capability
    - Analytics on status transitions
    """
    __tablename__ = "status_history"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Entity identification
    entity_type = Column(
        String(50), nullable=False, index=True,
        comment='builder, community, property, sales_rep'
    )
    entity_id = Column(
        MyBIGINT(unsigned=True), nullable=False, index=True,
        comment='ID of the entity'
    )

    # Status change details
    status_field = Column(
        String(50), nullable=False,
        comment='Which status field changed (business_status, listing_status, etc.)'
    )
    old_status = Column(
        String(50), nullable=True,
        comment='Previous status value'
    )
    new_status = Column(
        String(50), nullable=False,
        comment='New status value'
    )

    # Change context
    change_reason = Column(
        String(255), nullable=True,
        comment='Reason for status change'
    )
    changed_by = Column(
        String(50), nullable=True,
        comment='User ID who made the change, or "system" for automated'
    )
    change_source = Column(
        String(50), nullable=True, index=True,
        comment='Source of change: manual, auto_grace_period, data_collection, admin'
    )

    # Additional context
    change_metadata = Column(
        'metadata', JSON, nullable=True,
        comment='Additional context about the change (e.g., days_inactive, property_count)'
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(),
        nullable=False, index=True
    )

    def __repr__(self):
        return (
            f"<StatusHistory({self.entity_type}#{self.entity_id}: "
            f"{self.old_status} -> {self.new_status})>"
        )
