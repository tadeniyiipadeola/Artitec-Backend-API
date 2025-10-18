# model/profiles/community.py
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, ForeignKey, TIMESTAMP, JSON, Float
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
    public_id = Column(String(64), unique=True, nullable=False)  # mirrors Swift's `id` string (UUID)
    name = Column(String(255), nullable=False)
    city = Column(String(255))
    postal_code = Column(String(20))

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

    # Media
    intro_video_url = Column(String(1024))

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    # Relationships (1-to-many)
    amenities = relationship("CommunityAmenity", cascade="all, delete-orphan")
    events = relationship("CommunityEvent", cascade="all, delete-orphan")
    builder_cards = relationship("CommunityBuilder", cascade="all, delete-orphan")
    admins = relationship("CommunityAdmin", cascade="all, delete-orphan")
    awards = relationship("CommunityAward", cascade="all, delete-orphan")
    threads = relationship("CommunityTopic", cascade="all, delete-orphan")
    phases = relationship("CommunityPhase", cascade="all, delete-orphan")

    # Many-to-many: real Builder entities active in this community
    builders = relationship(
        "Builder",
        secondary=builder_communities,
        back_populates="communities",
        lazy="selectin",
    )


# ---------- Related Tables ----------

class CommunityAmenity(Base):
    __tablename__ = "community_amenities"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    gallery = Column(JSON)  # list of URLs


class CommunityEvent(Base):
    __tablename__ = "community_events"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    date = Column(TIMESTAMP, nullable=False)
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255))


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
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255))
    role = Column(String(128))
    email = Column(String(255))
    phone = Column(String(64))


class CommunityAward(Base):
    __tablename__ = "community_awards"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    year = Column(Integer)
    issuer = Column(String(255))
    icon = Column(String(64))
    note = Column(Text)


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
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255))
    lots = Column(JSON)  # simplified representation; can expand to a dedicated table later
    map_url = Column(String(1024))