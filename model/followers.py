# model/followers.py
"""
Followers model for tracking user-to-user following relationships.
This enables social features across all user types (buyers, builders, sales reps, etc.)
"""

from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from model.base import Base


class Follower(Base):
    """
    Tracks following relationships between users.

    Example:
        - User A (id=1) follows User B (id=2)
          -> follower_user_id=1, following_user_id=2
    """
    __tablename__ = "followers"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys to users table
    # FIXED: Changed from Integer to MyBIGINT to match users.id type
    follower_user_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who is following"
    )

    following_user_id = Column(
        MyBIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User being followed"
    )

    # Timestamp
    created_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        nullable=False
    )

    # Relationships (optional - for easier querying)
    # FIXED: Changed "User" to "Users" to match actual model name
    follower = relationship("Users", foreign_keys=[follower_user_id], backref="following")
    following = relationship("Users", foreign_keys=[following_user_id], backref="followers")

    # Constraints
    __table_args__ = (
        # Unique constraint - a user can only follow another user once
        UniqueConstraint(
            'follower_user_id',
            'following_user_id',
            name='uq_follower_following'
        ),
        # Check constraint - users cannot follow themselves
        CheckConstraint(
            'follower_user_id != following_user_id',
            name='ck_no_self_follow'
        ),
    )

    def __repr__(self):
        return f"<Follower(id={self.id}, follower={self.follower_user_id}, following={self.following_user_id})>"
