# model/buyer.py
from datetime import datetime
from sqlalchemy import (
    Column, String, BigInteger, Integer, DateTime, ForeignKey,
    TIMESTAMP, SmallInteger, JSON
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base
from model.user import User

# ---------- Enums (aligned with Swift) ----------
Sex = SAEnum("female", "male", "non_binary", "other", "prefer_not", name="sex_enum")
BuyingTimeline = SAEnum(
    "immediately", "one_to_three_months", "three_to_six_months", "six_plus_months", "exploring",
    name="buy_timeline"
)
FinancingStatus = SAEnum("cash", "pre_approved", "pre_qualified", "needs_pre_approval", "unknown", name="fin_status")
LoanProgram = SAEnum("conventional", "fha", "va", "usda", "jumbo", "other", name="loan_program")
PreferredChannel = SAEnum("email", "phone", "sms", "in_app", name="preferred_channel")
TourStatus = SAEnum("requested", "confirmed", "completed", "canceled", name="tour_status")

# ---------- BuyerProfile (1:1 with users.id) ----------
class BuyerProfile(Base):
    """
    Mirrors Swift BuyerProfile identity/contact/finance and top-level timeline.
    Saved boards (properties/builders/communities) are UI-side and not stored here.
    """
    __tablename__ = "buyer_profiles"

    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Display / identity
    display_name = Column(String(120), nullable=False)
    avatar_symbol = Column(String(64))          # Swift: avatarSystemName
    location = Column(String(255))
    bio = Column(String(1024))

    # Contact
    contact_email = Column(String(255))
    contact_phone = Column(String(32))
    contact_preferred = Column(PreferredChannel, nullable=False, server_default="email")

    # Core
    sex = Column(Sex)
    timeline = Column(BuyingTimeline, nullable=False, server_default="exploring")

    # Finance
    financing_status = Column(FinancingStatus, nullable=False, server_default="unknown")
    loan_program = Column(LoanProgram)
    budget_max_usd = Column(Integer)            # store whole dollars (or change to DECIMAL for cents)
    down_payment_percent = Column(SmallInteger) # 0–100
    lender_name = Column(String(255))
    agent_name = Column(String(255))

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(),
                        onupdate=func.current_timestamp(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="buyer_profile")
    tours = relationship("BuyerTour", back_populates="profile", cascade="all, delete-orphan")
    documents = relationship("BuyerDocument", back_populates="profile", cascade="all, delete-orphan")


# ---------- Tours ----------
class BuyerTour(Base):
    __tablename__ = "buyer_tours"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("buyer_profiles.user_id", ondelete="CASCADE"), nullable=False)

    property_public_id = Column(String(36), nullable=False)  # UUID string of the property
    status = Column(TourStatus, nullable=False, server_default="requested")
    notes = Column(String(1024))

    # Optional preferred time slots as JSON: [{ "start": "...ISO8601...", "end": "...ISO8601..." }, ...]
    preferred_slots = Column(JSON)
    profile = relationship("BuyerProfile", back_populates="tours")

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(),
                        onupdate=func.current_timestamp(), nullable=False)


# ---------- Documents ----------
class BuyerDocument(Base):
    __tablename__ = "buyer_documents"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("buyer_profiles.user_id", ondelete="CASCADE"), nullable=False)

    kind = SAEnum(
        "id", "pre_approval_letter", "proof_of_funds",
        "employment_letter", "tax_return", "bank_statement", "other",
        name="buyer_doc_kind"
    )
    name = Column(String(255), nullable=False)
    file_url = Column(String(1024))  # store external URL or S3 key
    profile = relationship("BuyerProfile", back_populates="documents")
    uploaded_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)