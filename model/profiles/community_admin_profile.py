# model/profiles/community_admin_profile.py
"""
Community Admin Profile - Links users to communities they manage
One-to-one relationship: each user can be an admin for ONE community
Similar to BuyerProfile and BuilderProfile structure
"""

from sqlalchemy import (
    Column, String, Integer, Text, TIMESTAMP, ForeignKey, Boolean
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from model.base import Base


class CommunityAdminProfile(Base):
    """
    Profile for users who are Community Administrators.
    Links a user to the community they manage.
    One-to-one with users.id (unique)
    """
    __tablename__ = "community_admin_profiles"

    # Primary key for community admin profile
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # One-to-one with users.id (unique)
    user_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Which community this admin manages (one admin = one community)
    community_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("communities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Profile/Display fields
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
    profile_image = Column(String(500))  # URL to profile image
    bio = Column(Text)
    title = Column(String(128))  # e.g., "HOA President", "Community Manager"

    # Contact information
    contact_email = Column(String(255))
    contact_phone = Column(String(64))
    contact_preferred = Column(String(32))  # "email", "phone", "sms", "in_app"

    # Permissions/Settings
    can_post_announcements = Column(Boolean, default=True, nullable=False)
    can_manage_events = Column(Boolean, default=True, nullable=False)
    can_moderate_threads = Column(Boolean, default=True, nullable=False)

    # Metadata (JSON for flexible future additions)
    extra = Column(Text)  # JSON string for additional metadata

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    # Relationships
    user = relationship("Users", backref="community_admin_profile", lazy="joined")
    community = relationship("Community", backref="admin_profile", lazy="joined")

    def __repr__(self):
        return f"<CommunityAdminProfile(id={self.id}, user_id={self.user_id}, community_id={self.community_id})>"
