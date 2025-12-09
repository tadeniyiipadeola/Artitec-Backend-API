# model/profiles/community.py
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, ForeignKey, TIMESTAMP, JSON, Float, UniqueConstraint
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base
from model.profiles.builder import builder_communities


class Community(Base):
    """
    Mirrors SwiftUI Community struct. Represents a real-world residential community
    or HOA-style group (now renamed to Community in code).

    Relationships:
      - builders: many-to-many to real Builder entities via builder_communities (active builders in this community)
      - builder_cards: legacy/marketing cards table for curated builder tiles
    """
    __tablename__ = "communities"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(String(64), unique=True, nullable=False)  # mirrors Swift's `id` string (CMY-xxx)

    # Owner/Creator of community (FK to users.user_id string ID)
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    city = Column(String(255))
    state = Column(String(64))
    postal_code = Column(String(20))
    address = Column(String(512))  # Full community address

    # Contact Information
    phone = Column(String(32))  # Community contact phone
    email = Column(String(255))  # Community contact email
    sales_office_address = Column(String(512))  # Sales office address

    # Location
    total_acres = Column(Float)  # Total acreage of the community
    latitude = Column(Float)  # Latitude coordinate
    longitude = Column(Float)  # Longitude coordinate

    # Finance
    community_dues = Column(String(64))
    tax_rate = Column(String(32))
    monthly_fee = Column(String(64))

    # Header + meta
    followers = Column(Integer, default=0)
    about = Column(Text)
    is_verified = Column(Boolean, default=False)

    # Stats
    homes = Column(Integer, default=0)
    residents = Column(Integer, default=0)
    founded_year = Column(Integer)
    member_count = Column(Integer, default=0)

    # Schools
    elementary_school = Column(String(255))  # Elementary school
    middle_school = Column(String(255))  # Middle school
    high_school = Column(String(255))  # High school

    # Development
    development_stage = Column(String(64))  # Phase 1-5, Completed
    development_start_year = Column(Integer)  # Year when development started
    is_master_planned = Column(Boolean, default=False)  # Whether this is a master-planned community
    enterprise_number_hoa = Column(String(255))  # Registration/Enterprise ID
    developer_name = Column(String(255))  # Developer name

    # Reviews
    rating = Column(Float)  # Average rating (using Float for DECIMAL compatibility)
    review_count = Column(Integer, default=0)  # Number of reviews

    # Status Management
    is_active = Column(Boolean, server_default='1', nullable=False)
    development_status = Column(String(50), server_default='active', nullable=False)  # planned, under_development, active, sold_out, inactive
    availability_status = Column(String(50), server_default='available', nullable=False)  # available, limited_availability, sold_out, closed
    last_activity_at = Column(TIMESTAMP)
    status_changed_at = Column(TIMESTAMP)
    status_change_reason = Column(String(255))

    # Media
    intro_video_url = Column(String(1024))
    community_website_url = Column(String(1024))

    # Data Collection & Tracking
    school_district = Column(String(255))  # School district name
    hoa_management_company = Column(String(255))  # HOA management company
    hoa_contact_phone = Column(String(20))  # HOA contact phone
    hoa_contact_email = Column(String(255))  # HOA contact email
    last_data_sync = Column(TIMESTAMP)  # Last successful data collection
    data_source = Column(String(50), server_default='manual', nullable=False)  # Source of data: manual, collected, collected_manual
    data_confidence = Column(Float, server_default='1.0', nullable=False)  # Confidence score for collected data

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    # Relationships
    # Owner/creator user
    owner = relationship("Users", foreign_keys=[user_id], lazy="joined")

    # Relationships (1-to-many)
    amenities = relationship("CommunityAmenity", cascade="all, delete-orphan")
    events = relationship("CommunityEvent", cascade="all, delete-orphan", back_populates="community")
    builder_cards = relationship("CommunityBuilder", cascade="all, delete-orphan")
    admins = relationship("CommunityAdmin", cascade="all, delete-orphan")
    awards = relationship("CommunityAward", cascade="all, delete-orphan")
    threads = relationship("CommunityTopic", cascade="all, delete-orphan")
    phases = relationship("CommunityPhase", cascade="all, delete-orphan")

    sales_reps = relationship("SalesRep", back_populates="community", cascade="all, delete-orphan")

    # Admin/profile links
    admin_links = relationship(
        "CommunityAdminLink",
        back_populates="community",
        cascade="all, delete-orphan",
    )

    # Many-to-many: real Builder entities active in this community
    builders = relationship(
        "BuilderProfile",
        secondary=builder_communities,
        back_populates="communities",
        lazy="selectin",
    )


# ---------- Related Tables ----------

class CommunityAmenity(Base):
    """
    Amenities available in a community (pool, clubhouse, trails, etc.).
    Each amenity can have a gallery of photos.
    """
    __tablename__ = "community_amenities"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_numeric_id = Column(MyBIGINT(unsigned=True), nullable=True)  # Legacy numeric ID
    community_id = Column(String(50), ForeignKey("communities.community_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    gallery = Column(JSON, default=list)  # list of photo URLs
    description = Column(Text)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    # Relationship back to Community
    community = relationship("Community", back_populates="amenities")

    def __repr__(self):
        return f"<CommunityAmenity(id={self.id}, name='{self.name}', community_id={self.community_id})>"


class CommunityEvent(Base):
    __tablename__ = "community_events"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_numeric_id = Column(MyBIGINT(unsigned=True), nullable=True)  # Legacy numeric ID
    community_id = Column(String(50), ForeignKey("communities.community_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    start_at = Column(TIMESTAMP, nullable=False, index=True)
    end_at = Column(TIMESTAMP)
    is_public = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    # Relationship back to Community
    community = relationship("Community", back_populates="events")


class CommunityBuilder(Base):
    __tablename__ = "community_builders"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    icon = Column(String(64))
    name = Column(String(255))
    subtitle = Column(String(255))
    followers = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)


class CommunityAdmin(Base):
    __tablename__ = "community_admins"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_numeric_id = Column(MyBIGINT(unsigned=True), nullable=True)  # Legacy numeric ID
    community_id = Column(String(50), ForeignKey("communities.community_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255))
    role = Column(String(128))
    email = Column(String(255))
    phone = Column(String(64))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )


class CommunityAward(Base):
    __tablename__ = "community_awards"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_numeric_id = Column(MyBIGINT(unsigned=True), nullable=True)  # Legacy numeric ID
    community_id = Column(String(50), ForeignKey("communities.community_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255))
    year = Column(Integer)
    issuer = Column(String(255))
    icon = Column(String(64))
    note = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )


class CommunityTopic(Base):
    __tablename__ = "community_topics"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    category = Column(String(255))
    replies = Column(Integer, default=0)
    last_activity = Column(String(128))
    is_pinned = Column(Boolean, default=False)
    comments = Column(JSON)  # store as list of dicts (author, text, timestamp)


class CommunityPhase(Base):
    __tablename__ = "community_phases"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_numeric_id = Column(MyBIGINT(unsigned=True), nullable=True)  # Legacy numeric ID
    community_id = Column(String(50), ForeignKey("communities.community_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255))
    lots = Column(JSON)  # simplified representation; can expand to a dedicated table later
    map_url = Column(String(1024))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )


class CommunityAdminLink(Base):
    """Explicit role mapping of a User to a Community with an assigned role.
    Use this when you need role-specific permissions separate from the profile metadata.
    """
    __tablename__ = "community_admin_links"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(64))          # e.g., "owner", "moderator", "editor"
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("community_id", "user_id", name="uq_community_admin_user"),
    )

    # Relationships
    community = relationship(
        "Community",
        back_populates="admin_links",
        lazy="joined",
    )
    user = relationship("Users", backref="community_admin_roles", lazy="joined")

    def __repr__(self):
        return f"<CommunityAdminLink(community_id={self.community_id}, user_id={self.user_id}, role={self.role!r})>"