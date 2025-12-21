"""
Lot models for phase map digitization and lot management
Integrates with community phases to track individual lots and their boundaries
"""
from sqlalchemy import (
    Column, String, Integer, Text, Date, TIMESTAMP, ForeignKey, JSON, Enum as SQLEnum, func
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT, DECIMAL
from sqlalchemy.orm import relationship
from model.base import Base
import enum


class LotStatus(str, enum.Enum):
    """Lot availability status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    UNAVAILABLE = "unavailable"
    ON_HOLD = "on_hold"


class PhaseStatus(str, enum.Enum):
    """Phase development status"""
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class Lot(Base):
    """
    Represents a single lot within a community phase.
    Supports polygon boundary tracking, status management, and property linking.
    """
    __tablename__ = "lots"

    # Primary Key
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Foreign Keys
    phase_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("community_phases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References community_phases.id"
    )
    community_id = Column(
        String(64),
        ForeignKey("communities.community_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References communities.community_id (CMY-xxx)"
    )
    builder_id = Column(
        String(64),
        nullable=True,
        index=True,
        comment="Builder ID (BLD-xxx) - references builder_profiles.builder_id"
    )
    property_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="References properties.id if lot has property listing"
    )

    # Lot Identification
    lot_number = Column(String(50), nullable=False, comment="Lot number (e.g., '101', 'A-5')")

    # Status & Availability
    status = Column(
        SQLEnum(LotStatus),
        nullable=False,
        server_default='available',
        index=True,
        comment="Current lot status"
    )

    # Geometry & Location
    boundary_coordinates = Column(
        JSON,
        nullable=True,
        comment="Polygon boundary as array of {x, y} coordinates in image space"
    )

    # Property Details
    square_footage = Column(Integer, nullable=True, comment="Lot size in square feet")
    price = Column(DECIMAL(12, 2), nullable=True, comment="Lot price or estimated home price")
    bedrooms = Column(Integer, nullable=True, comment="Number of bedrooms")
    bathrooms = Column(DECIMAL(3, 1), nullable=True, comment="Number of bathrooms (e.g., 2.5)")
    stories = Column(Integer, nullable=True, comment="Number of stories")
    garage_spaces = Column(Integer, nullable=True, comment="Number of garage spaces")
    model = Column(String(100), nullable=True, comment="Home model name")

    # Reservation & Sales Info
    reserved_by = Column(String(255), nullable=True, comment="Name of person who reserved lot")
    reserved_at = Column(TIMESTAMP, nullable=True, comment="When lot was reserved")
    sold_to = Column(String(255), nullable=True, comment="Name of buyer")
    sold_at = Column(TIMESTAMP, nullable=True, comment="When lot was sold")
    move_in_date = Column(Date, nullable=True, comment="Expected move-in date")

    # Notes & Metadata
    notes = Column(Text, nullable=True, comment="Additional notes about the lot")
    detection_method = Column(
        String(50),
        nullable=True,
        comment="How lot was detected: manual, yolo, line_detection"
    )
    detection_confidence = Column(
        DECIMAL(5, 4),
        nullable=True,
        comment="AI detection confidence score (0.0-1.0)"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False
    )
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    # Relationships
    phase = relationship("CommunityPhase", back_populates="lot_records")
    community = relationship("Community")
    property = relationship("Property", foreign_keys=[property_id])
    status_history = relationship(
        "LotStatusHistory",
        back_populates="lot",
        cascade="all, delete-orphan",
        order_by="LotStatusHistory.changed_at.desc()"
    )

    def __repr__(self):
        return f"<Lot(id={self.id}, lot_number='{self.lot_number}', phase_id={self.phase_id}, status='{self.status.value}')>"


class LotStatusHistory(Base):
    """
    Tracks all status changes for lots - provides complete audit trail
    """
    __tablename__ = "lot_status_history"

    # Primary Key
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Foreign Key
    lot_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("lots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="References lots.id"
    )

    # Status Change Info
    old_status = Column(
        SQLEnum(LotStatus),
        nullable=True,
        comment="Previous status (null for initial creation)"
    )
    new_status = Column(
        SQLEnum(LotStatus),
        nullable=False,
        comment="New status"
    )

    # Metadata
    changed_by = Column(String(255), nullable=True, comment="User who made the change")
    change_reason = Column(Text, nullable=True, comment="Reason for status change")
    changed_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False,
        index=True,
        comment="When status changed"
    )

    # Relationship
    lot = relationship("Lot", back_populates="status_history")

    def __repr__(self):
        return f"<LotStatusHistory(lot_id={self.lot_id}, {self.old_status} -> {self.new_status}, changed_at={self.changed_at})>"
