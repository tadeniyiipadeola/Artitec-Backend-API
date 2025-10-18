# model/user.py
from datetime import datetime
from sqlalchemy import (
    Column, String, BigInteger, Integer, Date, DateTime, ForeignKey,
    TIMESTAMP, SmallInteger, Boolean, CHAR, Text, JSON,
    UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base

class UserType(Base):
    __tablename__ = "user_types"
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False)
    display_name = Column(String(64), nullable=False)

import uuid
class User(Base):
    __tablename__ = "users"
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    public_id = Column(CHAR(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(120), nullable=False)
    last_name = Column(String(120), nullable=False)
    phone_e164 = Column(String(32))
    user_type_id = Column(SmallInteger, ForeignKey("user_types.id"), nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    status = Column(SAEnum("active","suspended","deleted", name="user_status"), nullable=False, default="active")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    user_type = relationship("UserType")
    creds = relationship("UserCredential", uselist=False, back_populates="user")
    buyer_profile = relationship(
        "BuyerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

class UserCredential(Base):
    __tablename__ = "user_credentials"
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    password_algo = Column(SAEnum("bcrypt", name="password_algo"), nullable=False, default="bcrypt")
    last_password_change = Column(DateTime)

    user = relationship("User", back_populates="creds")

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


# =============================
# Role/Org backing models (align with role selection & forms)
# =============================

# Organization directory. Both Builders and Communities live here.
class Organization(Base):
    __tablename__ = "organizations"
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    # e.g., "builder" or "community"
    org_type = Column(SAEnum("builder", "community", name="org_type"), nullable=False, index=True)

    # Display & linkage
    name = Column(String(255), nullable=False)
    enterprise_number = Column(String(64), unique=True)  # e.g., ENT-483920

    # Basic location (optional for builder; community tends to have these)
    address = Column(String(255))
    city = Column(String(120))
    state = Column(String(64))

    # Billing/plan flags derived from selection
    active_tier = Column(SAEnum("free", "pro", "enterprise", name="org_tier"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    __table_args__ = (
        Index("ix_org_type_name", "org_type", "name"),
    )

# Builder profile details (one per builder organization)
class BuilderProfile(Base):
    __tablename__ = "builder_profiles"
    org_id = Column(MyBIGINT(unsigned=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    company_name = Column(String(255), nullable=False)
    website_url = Column(String(512))
    company_address = Column(String(255))
    staff_size = Column(String(32))  # "1–5", "6–10", etc.
    years_in_business = Column(SmallInteger)

    # Optional quality signals (future use)
    rating_avg = Column(String(8))  # keep flexible until ratings module lands
    rating_count = Column(Integer, default=0)

# Community profile details (one per community organization)
class CommunityProfile(Base):
    __tablename__ = "community_profiles"
    org_id = Column(MyBIGINT(unsigned=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    community_name = Column(String(255), nullable=False)
    community_address = Column(String(255))
    city = Column(String(120), nullable=False)
    state = Column(String(64), nullable=False)
    stage = Column(SAEnum("pre_development", "first_phase", "second_stage", "completed", name="community_stage"))
    enterprise_number = Column(String(64))

    __table_args__ = (
        Index("ix_community_city_state", "city", "state"),
    )

# Link a user (admin) to a community org with verification status
class CommunityAdminLink(Base):
    __tablename__ = "community_admin_links"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(MyBIGINT(unsigned=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    # Pending until proof-of-ownership is checked
    status = Column(SAEnum("pending", "approved", "rejected", name="admin_verify_status"), nullable=False, server_default="pending")
    requested_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    decided_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_admin_user_org"),
        Index("ix_admin_status", "status"),
    )

# Sales Rep (Realtor) profile (1:1 with user)
class SalesRepProfile(Base):
    __tablename__ = "sales_rep_profiles"
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Personal / professional
    address = Column(String(255))
    phone = Column(String(32))  # keep separate from users.phone_e164 in case of business line
    sex = Column(SAEnum("female", "male", "non_binary", "prefer_not", name="sex"))
    dob = Column(Date)
    brokerage = Column(String(255))
    license_id = Column(String(64))
    years_at_company = Column(SmallInteger)

    # Company / placement
    company_account_number = Column(String(64))
    office_location = Column(String(255))
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("organizations.id", ondelete="SET NULL"))  # optional link to community org

# Buyer preferences (1:1 with user)
class BuyerPreferences(Base):
    __tablename__ = "buyer_preferences"
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Personal (duplicated minimally for quick cards; canonical lives in users)
    sex = Column(SAEnum("female", "male", "non_binary", "prefer_not", name="sex_pref"))

    # Preferences
    income_range = Column(String(64))  # "$100k–$200k"
    first_time = Column(SAEnum("yes", "no", "prefer_not", name="first_time_flag"))
    home_type = Column(SAEnum("single_home", "multiple_homes", name="home_type"))
    budget_min = Column(Integer)
    budget_max = Column(Integer)
    location_interest = Column(String(255))
    builder_interest = Column(String(255))

    # Extra future-proofing
    meta = Column(JSON)  # room for additional captured fields without migrations

# Optional: store raw onboarding JSON payloads for troubleshooting
class OnboardingForm(Base):
    __tablename__ = "onboarding_forms"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(SAEnum("user", "builder", "community", "communityAdmin", "salesRep", "buyer", name="onboard_role"), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(SAEnum("preview", "committed", name="onboard_status"), nullable=False, server_default="preview")
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

# -----------------
# Relationships on existing models
# -----------------
# Attach relationships to User so you can eager-load profiles in one go
User.sales_rep_profile = relationship("SalesRepProfile", uselist=False, cascade="all, delete-orphan")
User.buyer_preferences = relationship("BuyerPreferences", uselist=False, cascade="all, delete-orphan")
User.community_admin_links = relationship("CommunityAdminLink", cascade="all, delete-orphan")

# Optionally make it convenient to navigate across organizations
Organization.builder_profile = relationship("BuilderProfile", uselist=False, cascade="all, delete-orphan")
Organization.community_profile = relationship("CommunityProfile", uselist=False, cascade="all, delete-orphan")