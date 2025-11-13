# model/user_updated.py
"""
Updated User model with role as string instead of role_id FK.

CHANGES:
- role_id (SmallInteger FK) → role (String/Enum)
- Direct role value: "buyer", "builder", "community", etc.
- Simpler queries, no JOIN needed
- Better API responses

MIGRATION: Run f2g3h4i5j6k7_replace_role_id_with_role_key.py first
"""

from sqlalchemy import (
    Column, String, BigInteger, Boolean, CHAR,
    TIMESTAMP, ForeignKey, Index, DateTime as SADateTime,
    Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.sql import func
from model.base import Base


# Define role enum
RoleEnum = SAEnum(
    "buyer", "builder", "community", "community_admin", "salesrep", "admin",
    name="user_role_enum"
)


class Users(Base):
    __tablename__ = "users"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone_e164 = Column(String(32))

    # CHANGED: Direct role value instead of FK
    # Options:
    # 1. Use String (more flexible, allows new roles without schema change)
    role = Column(String(32), nullable=False, index=True)

    # 2. Use Enum (stricter validation, uncomment if preferred)
    # role = Column(RoleEnum, nullable=False, index=True)

    onboarding_completed = Column(Boolean, server_default="0", nullable=False)
    is_email_verified = Column(Boolean, server_default="0", nullable=False)
    plan_tier = Column(SAEnum("free", "pro", "enterprise", name="plan_tier"), nullable=False, server_default="free")
    status = Column(SAEnum("active", "suspended", "deleted", name="user_status"), nullable=False, server_default="active")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_plan_tier", "plan_tier"),
        Index("ix_users_role", "role"),  # NEW: Index on role
        Index("ix_users_created_at", "created_at"),
    )

    # REMOVED: role relationship (no longer FK)
    # role = relationship("Role", back_populates="users")

    # Keep other relationships
    creds = relationship("UserCredential", uselist=False, back_populates="user", passive_deletes=True)
    buyer_profile = relationship("BuyerProfile", back_populates="user", uselist=False)
    builder_profile = relationship("BuilderProfile", back_populates="user", uselist=False)
    sessions = relationship("SessionToken", backref="user", passive_deletes=True)
    email_verifications = relationship("EmailVerification", backref="user", passive_deletes=True)

    # Helper property to get role display name from reference table
    @property
    def role_display_name(self) -> str:
        """Get display name for role (e.g., 'buyer' → 'Buyer')"""
        role_names = {
            "buyer": "Buyer",
            "builder": "Builder",
            "community": "Community",
            "community_admin": "Community Admin",
            "salesrep": "Sales Representative",
            "admin": "Administrator"
        }
        return role_names.get(self.role, self.role.title())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email!r}, role={self.role!r})>"


class UserCredential(Base):
    __tablename__ = "user_credentials"

    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    password_algo = Column(SAEnum("bcrypt", name="password_algo"), nullable=False, default="bcrypt")
    last_password_change = Column(SADateTime)

    user = relationship("Users", back_populates="creds")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(CHAR(64), unique=True, nullable=False)
    expires_at = Column(SADateTime, nullable=False)
    used_at = Column(SADateTime)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(CHAR(64), unique=True, nullable=False)
    user_agent = Column(String(255))
    ip_addr = Column(String(45))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    expires_at = Column(SADateTime, nullable=False)
    revoked_at = Column(SADateTime)

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
    )


class Role(Base):
    """
    Reference table for role metadata.

    NOTE: After migration, this table is for REFERENCE only.
    The users.role column stores the key directly (no FK).

    Use this table for:
    - Display names ("Buyer", "Builder")
    - Descriptions
    - UI metadata (icons, colors)
    - Permission mappings
    """
    __tablename__ = "roles"

    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    key = Column(String(32), unique=True, nullable=False, index=True)  # "buyer", "builder", etc.
    name = Column(String(64), nullable=False)  # "Buyer", "Builder"
    description = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    # REMOVED: users relationship (no longer FK)
    # users = relationship("Users", back_populates="role")

    def __repr__(self):
        return f"<Role(key={self.key!r}, name={self.name!r})>"


# =============================================================================
# Helper Functions
# =============================================================================

def get_role_display_name(role_key: str) -> str:
    """
    Get display name for a role key.

    Args:
        role_key: Role key (e.g., "buyer", "builder")

    Returns:
        Display name (e.g., "Buyer", "Builder")
    """
    role_names = {
        "buyer": "Buyer",
        "builder": "Builder",
        "community": "Community",
        "community_admin": "Community Admin",
        "salesrep": "Sales Representative",
        "admin": "Administrator"
    }
    return role_names.get(role_key, role_key.title())


def validate_role(role: str) -> bool:
    """
    Validate if a role is valid.

    Args:
        role: Role key to validate

    Returns:
        True if valid, False otherwise
    """
    valid_roles = {"buyer", "builder", "community", "community_admin", "salesrep", "admin"}
    return role in valid_roles


# =============================================================================
# Usage Examples
# =============================================================================

"""
# Creating a user with role

from model.user_updated import Users

user = Users(
    public_id=generate_user_id(),
    email="john@example.com",
    first_name="John",
    last_name="Doe",
    role="buyer",  # Direct string value
    plan_tier="free",
    status="active"
)
db.add(user)
db.commit()


# Querying users by role (NO JOIN NEEDED!)

# Before (with role_id FK):
buyers = db.query(Users).join(Role).filter(Role.key == "buyer").all()

# After (with role string):
buyers = db.query(Users).filter(Users.role == "buyer").all()


# API Response

{
    "id": "USR-1699564234-A7K9M2",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "buyer",  # Clean, readable value
    "role_display_name": "Buyer",  # From helper property
    "plan_tier": "free",
    "status": "active"
}


# Validation in routes

from model.user_updated import validate_role

@router.post("/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if not validate_role(payload.role):
        raise HTTPException(400, f"Invalid role: {payload.role}")

    user = Users(
        public_id=generate_user_id(),
        role=payload.role,  # Direct assignment
        ...
    )
    db.add(user)
    db.commit()
    return user
"""
