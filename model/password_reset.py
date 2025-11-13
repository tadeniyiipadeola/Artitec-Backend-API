# model/password_reset.py
"""
SQLAlchemy model for password reset tokens.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from config.db import Base
from model.custom_types import MyBIGINT


class PasswordResetToken(Base):
    """Password reset token model for forgot password functionality."""

    __tablename__ = "password_reset_tokens"

    # Primary key
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Foreign key to users
    user_id = Column(
        String(50),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Token for URL (plain text, URL-safe)
    token = Column(String(255), nullable=False, unique=True, index=True)

    # Hashed token for database security
    token_hash = Column(String(255), nullable=False, unique=True)

    # Expiration timestamp
    expires_at = Column(DateTime, nullable=False, index=True)

    # When token was used (null = not used yet)
    used_at = Column(DateTime, nullable=True)

    # Audit timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship back to user
    user = relationship("Users", back_populates="password_reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at}, used={self.used_at is not None})>"

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not used)."""
        now = datetime.utcnow()
        return (
            self.expires_at > now and
            self.used_at is None
        )

    def mark_as_used(self):
        """Mark token as used."""
        self.used_at = datetime.utcnow()


# Create composite index for common queries
Index('ix_password_reset_user_valid',
      PasswordResetToken.user_id,
      PasswordResetToken.expires_at,
      PasswordResetToken.used_at)
