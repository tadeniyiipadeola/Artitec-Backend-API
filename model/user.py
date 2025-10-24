# model/user.py
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, BigInteger, Integer, DateTime, SmallInteger, Boolean, CHAR,
    TIMESTAMP, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy import Enum as SAEnum
from sqlalchemy.sql import func
from model.base import Base


class RoleEnum(enum.IntEnum):
    buyer = 1
    builder = 2
    community_admin = 3
    salesrep = 4
    admin = 5


class RoleType(Base):
    __tablename__ = "role_types"

    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(SmallInteger, unique=True, index=True, nullable=False)
    display_name = Column(String(64), nullable=False)


class Users(Base):
    __tablename__ = "users"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone_e164 = Column(String(32))
    role_type_id = Column(SmallInteger, ForeignKey("role_types.id"), nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    role = Column(SAEnum("buyer", "builder", "community_admin", "salesrep", "admin", name="user_role"), nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    status = Column(SAEnum("active", "suspended", "deleted", name="user_status"), nullable=False, default="active")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_status", "status"),
    )

    role_type = relationship("RoleType")
    creds = relationship("UserCredential", uselist=False, back_populates="user")
    buyer_profile = relationship("BuyerProfile", back_populates="user", uselist=False)


class UserCredential(Base):
    __tablename__ = "user_credentials"

    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    password_algo = Column(SAEnum("bcrypt", name="password_algo"), nullable=False, default="bcrypt")
    last_password_change = Column(DateTime)

    user = relationship("Users", back_populates="creds")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(CHAR(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(CHAR(64), unique=True, nullable=False)
    user_agent = Column(String(255))
    ip_addr = Column(String(45))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)