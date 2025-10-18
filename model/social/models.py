
# social/models.py
from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.sql import func

from model.base import Base


# ---------------------------------------------------------------------------
# Follows: user → (builder|community|user)
# Composite PK prevents duplicates; generic target avoids cross-table FK.
# ---------------------------------------------------------------------------
class Follow(Base):
    __tablename__ = "follows"

    follower_user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    target_type = Column(String(24), primary_key=True)  # e.g., 'builder','community','user'
    target_id = Column(MyBIGINT(unsigned=True), primary_key=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        # Fast lookups by target for follower lists
        Index("idx_follows_target", "target_type", "target_id", "created_at"),
        # Fast lookups by follower for following lists
        Index("idx_follows_user", "follower_user_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# Likes: user → (post|comment|property|builder|...)
# Composite PK prevents duplicates.
# ---------------------------------------------------------------------------
class Like(Base):
    __tablename__ = "likes"

    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    target_type = Column(String(24), primary_key=True)
    target_id = Column(MyBIGINT(unsigned=True), primary_key=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        Index("idx_likes_target", "target_type", "target_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# Comments: threaded discussions on any target
# Soft-deletion keeps threads coherent; parent_id allows 1+ level replies.
# ---------------------------------------------------------------------------
class Comment(Base):
    __tablename__ = "comments"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    author_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(String(24), nullable=False)
    target_id = Column(MyBIGINT(unsigned=True), nullable=False)
    parent_id = Column(MyBIGINT(unsigned=True), nullable=True)
    body = Column(Text, nullable=False)
    is_deleted = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=True, onupdate=func.current_timestamp())

    __table_args__ = (
        Index("idx_comments_target", "target_type", "target_id", "created_at"),
        Index("idx_comments_author", "author_id", "created_at"),
        Index("idx_comments_parent", "parent_id"),
    )