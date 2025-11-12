# model/profiles/buyer.py
"""
Buyer domain models aligned with the SwiftUI Buyer Profile page.
- One-to-one BuyerProfile per user (users.id)
- Optional one-to-one BuyerPreference row for saved search/preferences

Boards/saved items are handled elsewhere (not part of this file).
"""

from sqlalchemy import (
    Column, String, Integer, Float, Text, JSON, TIMESTAMP, SmallInteger, Boolean, ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from model.base import Base

# --------------------------- Enums (stable) ---------------------------------
SexEnum = SAEnum("female", "male", "non_binary", "other", "prefer_not", name="sex_enum")
BuyTimelineEnum = SAEnum(
    "immediately", "one_to_three_months", "three_to_six_months", "six_plus_months", "exploring",
    name="buy_timeline_enum",
)
FinancingStatusEnum = SAEnum(
    "cash", "pre_approved", "pre_qualified", "needs_pre_approval", "unknown",
    name="financing_status_enum",
)
LoanProgramEnum = SAEnum("conventional", "fha", "va", "usda", "jumbo", "other", name="loan_program_enum")

PreferredChannelEnum = SAEnum("email", "phone", "sms", "in_app", name="preferred_channel_enum")

# Tours status
TourStatusEnum = SAEnum(
    "requested", "confirmed", "completed", "cancelled", "no_show", "rescheduled",
    name="buyer_tour_status_enum",
)


# ---------------------------- BuyerProfile ----------------------------------
class BuyerProfile(Base):
    __tablename__ = "buyer_profiles"

    # Primary key for buyer profile (used as buyer_profile_id in API)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # One-to-one with users.id (unique) - Changed to INT to match users.id
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Identity / display
    display_name = Column(String(255), nullable=True)
    profile_image = Column(String(500), nullable=True)           # URL to uploaded profile image
    bio = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    website_url = Column(String(512), nullable=True)

    # Legal name (often required up-front during onboarding)
    first_name = Column(String(120), nullable=True)
    last_name  = Column(String(120), nullable=True)

    # Contact (optional) — keep legacy fields for compatibility
    contact_email = Column(String(255), nullable=True)  # legacy alias for email
    contact_phone = Column(String(32), nullable=True)   # legacy alias for phone
    contact_preferred = Column(PreferredChannelEnum, nullable=False, server_default="email")

    # Canonical contact fields used by role form commit
    email = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)

    # Address (optional but required at onboarding for buyer role)
    address = Column(String(255), nullable=True)
    city    = Column(String(120), nullable=True)
    state   = Column(String(64), nullable=True)
    zip_code = Column(String(20), nullable=True)

    # Core profile attributes
    sex = Column(SexEnum, nullable=True)
    timeline = Column(BuyTimelineEnum, nullable=False, server_default="exploring")

    # Financing snapshot (optional and editable)
    financing_status = Column(FinancingStatusEnum, nullable=False, server_default="unknown")
    loan_program = Column(LoanProgramEnum, nullable=True)
    household_income_usd = Column(Integer, nullable=True)        # annual household income
    budget_min_usd = Column(Integer, nullable=True)              # minimum budget
    budget_max_usd = Column(Integer, nullable=True)              # whole dollars (use DECIMAL if you need cents)
    down_payment_percent = Column(SmallInteger, nullable=True)   # 0–100
    lender_name = Column(String(255), nullable=True)
    agent_name = Column(String(255), nullable=True)

    # Additional flexible metadata (app-specific flags, feature toggles)
    extra = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    user = relationship("Users", back_populates="buyer_profile", lazy="selectin")
    preferences = relationship(
        "BuyerPreference",
        back_populates="profile",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    tours = relationship(
        "BuyerTour",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    documents = relationship(
        "BuyerDocument",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<BuyerProfile(user_id={self.user_id}, name={self.first_name!r} {self.last_name!r}, display_name={self.display_name!r})>"


# --------------------------- BuyerPreference --------------------------------
class BuyerPreference(Base):
    """Search/saved preferences tied one-to-one to the buyer."""

    __tablename__ = "buyer_preferences"

    buyer_id = Column(
        Integer,
        ForeignKey("buyer_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Basic search ranges
    min_beds = Column(Integer, nullable=True)
    min_baths = Column(Float, nullable=True)
    price_min = Column(Integer, nullable=True)
    price_max = Column(Integer, nullable=True)

    # Property attributes
    has_pool = Column(Boolean, nullable=True)
    new_construction_ok = Column(Boolean, nullable=True)
    hoa_ok = Column(Boolean, nullable=True)
    lot_min_sqft = Column(Integer, nullable=True)

    # Geography / areas of interest
    cities = Column(JSON, nullable=True)   # ["Houston", "Willis"]
    zips = Column(JSON, nullable=True)     # ["77378", "77365"]
    states = Column(JSON, nullable=True)   # ["TX"]

    # Additional features/tags (free-form)
    features = Column(JSON, nullable=True)  # e.g., ["Waterfront","Cul-de-sac","Primary down"]

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationship
    profile = relationship("BuyerProfile", back_populates="preferences", lazy="selectin")

    def __repr__(self):
        return f"<BuyerPreference(buyer_id={self.buyer_id}, price=[{self.price_min},{self.price_max}])>"


# ----------------------------- BuyerTour ------------------------------------
class BuyerTour(Base):
    """In-person or virtual tour requests made by a buyer for a property."""

    __tablename__ = "buyer_tours"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # owner (1 buyer per tour)
    buyer_id = Column(
        Integer,
        ForeignKey("buyer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # target property
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # scheduling
    scheduled_at = Column(TIMESTAMP, nullable=True)
    status = Column(TourStatusEnum, nullable=False, server_default="requested")

    # optional details
    note = Column(Text, nullable=True)
    agent_name = Column(String(255), nullable=True)
    agent_phone = Column(String(64), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    profile = relationship("BuyerProfile", back_populates="tours", lazy="selectin")
    property = relationship("Property", lazy="selectin")

    def __repr__(self):
        return f"<BuyerTour(id={self.id}, buyer_id={self.buyer_id}, property_id={self.property_id}, status={self.status})>"


# ---------------------------- BuyerDocument ---------------------------------
class BuyerDocument(Base):
    """Documents uploaded/attached by a buyer (e.g., pre-approval letter).

    Stored as metadata with a remote file URL. Actual binary lives in object storage.
    """

    __tablename__ = "buyer_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # owner (ties to buyer profile)
    buyer_id = Column(
        Integer,
        ForeignKey("buyer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # optional linkage to a property (e.g., specific home offer)
    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # file metadata
    filename = Column(String(255), nullable=False)
    file_url = Column(String(1024), nullable=False)  # presigned URL or permanent location
    mime_type = Column(String(128), nullable=True)
    size_bytes = Column(Integer, nullable=True)

    note = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    profile = relationship("BuyerProfile", back_populates="documents", lazy="selectin")
    property = relationship("Property", lazy="selectin")

    def __repr__(self):
        return f"<BuyerDocument(id={self.id}, buyer_id={self.buyer_id}, filename={self.filename!r})>"


# ----------------------------- TourStatus -----------------------------------
class TourStatus(Base):
    """Static reference table for BuyerTour status descriptions.

    Useful for populating dropdowns or syncing to SwiftUI enums with localized labels.
    """

    __tablename__ = "tour_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False)  # e.g., 'requested', 'confirmed'
    label = Column(String(255), nullable=False)             # e.g., 'Requested', 'Confirmed'
    description = Column(Text, nullable=True)
    color_hex = Column(String(16), nullable=True)           # optional UI color hint

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self):
        return f"<TourStatus(code={self.code!r}, label={self.label!r})>"


# -------------------------- FinancingStatus ---------------------------------
class FinancingStatus(Base):
    """Reference table for available financing status options.

    Provides readable labels, descriptions, and optional icons or colors
    for buyer financing state shown in SwiftUI interfaces.
    """

    __tablename__ = "financing_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False)   # e.g., 'pre_approved', 'cash', 'needs_pre_approval'
    label = Column(String(255), nullable=False)              # e.g., 'Pre-Approved', 'Cash Buyer'
    description = Column(Text, nullable=True)
    icon_name = Column(String(128), nullable=True)           # optional UI icon reference
    color_hex = Column(String(16), nullable=True)            # optional UI color accent

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self):
        return f"<FinancingStatus(code={self.code!r}, label={self.label!r})>"


# ---------------------------- LoanProgram -----------------------------------
class LoanProgram(Base):
    """Reference table for supported loan programs.

    Provides friendly names, descriptions, icons, and colors to sync with SwiftUI pickers.
    """

    __tablename__ = "loan_programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False)   # e.g., 'conventional', 'fha', 'va', 'usda', 'jumbo'
    label = Column(String(255), nullable=False)              # e.g., 'Conventional Loan', 'FHA Loan'
    description = Column(Text, nullable=True)
    icon_name = Column(String(128), nullable=True)           # optional UI icon reference
    color_hex = Column(String(16), nullable=True)            # optional UI color accent

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self):
        return f"<LoanProgram(code={self.code!r}, label={self.label!r})>"


# --------------------------- BuyingTimeline ---------------------------------
class BuyingTimeline(Base):
    """Reference table for a buyer's intended purchase timeline.

    Useful for representing timeline categories (immediately, 1–3 months, etc.) with labels and descriptions.
    """

    __tablename__ = "buying_timelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False)   # e.g., 'immediately', 'one_to_three_months'
    label = Column(String(255), nullable=False)              # e.g., 'Immediately', '1–3 Months'
    description = Column(Text, nullable=True)
    icon_name = Column(String(128), nullable=True)           # optional UI icon name (e.g., clock)
    color_hex = Column(String(16), nullable=True)            # optional color accent for UI

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self):
        return f"<BuyingTimeline(code={self.code!r}, label={self.label!r})>"


# -------------------------- PreferredChannel --------------------------------
class PreferredChannel(Base):
    """Reference table for preferred contact channels.

    Provides metadata for communication options displayed in the SwiftUI Buyer Profile page.
    """

    __tablename__ = "preferred_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False)   # e.g., 'email', 'phone', 'sms', 'in_app'
    label = Column(String(255), nullable=False)              # e.g., 'Email', 'Phone Call', 'Text Message', 'In-App'
    description = Column(Text, nullable=True)
    icon_name = Column(String(128), nullable=True)           # optional UI icon name
    color_hex = Column(String(16), nullable=True)            # optional UI color accent

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    def __repr__(self):
        return f"<PreferredChannel(code={self.code!r}, label={self.label!r})>"