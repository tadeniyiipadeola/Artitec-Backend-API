# model/user.py
from datetime import datetime
from sqlalchemy import (
    Column, String, BigInteger, DateTime, ForeignKey, TIMESTAMP, SmallInteger, Boolean, CHAR
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base

class UserType(Base):
    __tablename__ = "user_types"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False)
    display_name = Column(String(64), nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    public_id = Column(CHAR(26), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(120), nullable=False)
    phone_e164 = Column(String(32))
    user_type_id = Column(SmallInteger, ForeignKey("user_types.id"), nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    status = Column(SAEnum("active","suspended","deleted", name="user_status"), nullable=False, default="active")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    user_type = relationship("UserType")
    creds = relationship("UserCredential", uselist=False, back_populates="user")

class UserCredential(Base):
    __tablename__ = "user_credentials"
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    password_algo = Column(SAEnum("bcrypt", name="password_algo"), nullable=False, default="bcrypt")
    last_password_change = Column(DateTime)

    user = relationship("User", back_populates="creds")

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(CHAR(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

class SessionToken(Base):
    __tablename__ = "sessions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(CHAR(64), unique=True, nullable=False)
    user_agent = Column(String(255))
    ip_addr = Column(String(45))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)