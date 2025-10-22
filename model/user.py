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
    users = relationship("Users", back_populates="role_type")


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
    is_email_verified = Column(Boolean, default=False, nullable=False)
    status = Column(SAEnum("active", "suspended", "deleted", name="user_status"), nullable=False, default="active")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_status", "status"),
    )

    role_type = relationship("RoleType", back_populates="users")
    creds = relationship("UserCredential", uselist=False, back_populates="user")

    @property
    def role(self) -> RoleEnum | None:
        if self.role_type_id is None or self.role_type is None:
            return None
        try:
            return RoleEnum(self.role_type.code)
        except Exception:
            return None

    @role.setter
    def role(self, value: RoleEnum | int | str | None):
        """Setter to update role via enum/int/str. Stores only the FK to RoleType.
        Accepts RoleEnum, its underlying int, or one of the strings: buyer, builder, community_admin, salesrep, admin.
        """
        if value is None:
            self.role_type_id = None
            return

        # Normalize to integer code
        if isinstance(value, RoleEnum):
            code = int(value)
        elif isinstance(value, int):
            code = value
        elif isinstance(value, str):
            mapping = {
                "buyer": 1,
                "builder": 2,
                "community_admin": 3,
                "salesrep": 4,
                "admin": 5,
            }
            code = mapping.get(value)
            if code is None:
                raise ValueError(f"Unknown role string: {value}")
        else:
            raise TypeError("role must be RoleEnum, int, str, or None")

        # Assign by FK; the calling service should ensure a RoleType with this code exists
        self.role_type_id = code


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