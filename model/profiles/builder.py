# model/profiles/builder.py
from sqlalchemy import (
    Column, 
    String, Float, Integer, Text, JSON, TIMESTAMP, ForeignKey, Table
)
import uuid
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base


# --- Association Tables ------------------------------------------------------
# Many-to-many: builders ↔ properties (portfolio)
# Expects a `properties` table/model defined elsewhere as `Property`.
builder_portfolio = Table(
    "builder_portfolio",
    Base.metadata,
    Column("builder_id", MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("property_id", MyBIGINT(unsigned=True), ForeignKey("properties.id", ondelete="CASCADE"), primary_key=True),
)

# Many-to-many: builders ↔ communities (active build areas)
# Expects a `communities` table/model defined elsewhere as `Community`.
builder_communities = Table(
    "builder_communities",
    Base.metadata,
    Column("builder_id", MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("community_id", MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True),
)

# Helper to generate IDs like B_329_XXX_XXX_XXX_XXX
def _gen_builder_public_id() -> str:
    s = uuid.uuid4().hex.upper()[:12]
    parts = [s[i:i+3] for i in range(0, 12, 3)]
    return f"B_329_{'_'.join(parts)}"

class BuilderProfile(Base):
    """
    Mirrors SwiftUI Builder struct.
    Represents a home builder / construction firm with specialties and ratings.
    Also links to:
      - portfolio properties via builder_portfolio
      - active communities via builder_communities
      - owning/primary user via user_id
    """
    __tablename__ = "builder_profiles"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    # Builder ID for API (e.g., BLD-1699564234-X3P8Q1)
    builder_id = Column(String(50), unique=True, nullable=False, index=True)

    # One-to-one link to platform user (the account that owns/manages this builder)
    # FK to users.user_id (String)
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    website = Column(String(1024))               # Swift: URL? — stored as string
    specialties = Column(JSON)                   # Swift: [String]
    rating = Column(Float)                       # Swift: Double?
    communities_served = Column(JSON)            # Swift: communitiesServed

    # Optional extended fields
    about = Column(Text)
    phone = Column(String(64))
    email = Column(String(255))
    address = Column(String(255))  # Street address
    city = Column(String(255))
    state = Column(String(64))
    postal_code = Column(String(20))
    verified = Column(Integer, default=0)        # 0 = not verified, 1 = verified

    # Former BuilderProfile metadata (merged here)
    title = Column(String(128))                  # e.g., "Owner", "Regional Manager"
    bio = Column(Text)
    socials = Column(JSON)                       # {"linkedin": "…", "x": "…"}

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    user = relationship("Users", back_populates="builder_profile", lazy="joined", uselist=False)
    sales_reps = relationship("SalesRep", back_populates="builder", cascade="all, delete-orphan")
    awards = relationship("BuilderAward", back_populates="builder", cascade="all, delete-orphan")
    home_plans = relationship("BuilderHomePlan", back_populates="builder", cascade="all, delete-orphan")
    credentials = relationship("BuilderCredential", back_populates="builder", cascade="all, delete-orphan")

    # Many-to-many relationships
    properties = relationship(
        "Property",
        secondary=builder_portfolio,
        back_populates="builders",
        lazy="selectin",
    )

    communities = relationship(
        "Community",
        secondary=builder_communities,
        back_populates="builders",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<BuilderProfile(name='{self.name}', rating={self.rating})>"


# --- Builder Awards ---------------------------------------------------------
class BuilderAward(Base):
    """
    Awards and recognitions received by a builder.
    Mirrors Swift BuilderProfile.awards: [Award]
    """
    __tablename__ = "builder_awards"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    # FK to builder_profiles.id (internal DB ID)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)      # e.g., "Best Custom Home Builder"
    awarded_by = Column(String(255), nullable=True)  # e.g., "National Association of Home Builders"
    year = Column(Integer, nullable=True)            # e.g., 2023

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    # Relationship
    builder = relationship("BuilderProfile", back_populates="awards")

    def __repr__(self):
        return f"<BuilderAward(title='{self.title}', year={self.year})>"


# --- Builder Home Plans -----------------------------------------------------
class BuilderHomePlan(Base):
    """
    Home plans/floor plans offered by a builder.
    Mirrors Swift BuilderProfile.homePlans: [HomePlan]
    """
    __tablename__ = "builder_home_plans"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    # FK to builder_profiles.id (internal DB ID)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)           # e.g., "The Oakmont"
    series = Column(String(255), nullable=False)         # e.g., "Executive Series"
    sqft = Column(Integer, nullable=False)               # Square footage
    beds = Column(Integer, nullable=False)               # Number of bedrooms
    baths = Column(Float, nullable=False)                # Number of bathrooms (can be 2.5)
    stories = Column(Integer, nullable=False)            # Number of stories
    starting_price = Column(String(64), nullable=False)  # Stored as string (e.g., "450000.00")
    description = Column(Text)                           # Detailed description
    image_url = Column(String(1024))                     # Optional image URL

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    # Relationship
    builder = relationship("BuilderProfile", back_populates="home_plans")

    def __repr__(self):
        return f"<BuilderHomePlan(name='{self.name}', series='{self.series}')>"


# --- Builder Credentials ----------------------------------------------------
class BuilderCredential(Base):
    """
    Builder licenses, certifications, and memberships.
    Mirrors Swift BuilderProfile.licenses, certifications, memberships
    Consolidated into one table with a type field.
    """
    __tablename__ = "builder_credentials"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    # FK to builder_profiles.id (internal DB ID)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)           # e.g., "General Contractor License #12345"
    credential_type = Column(String(64), nullable=False) # "license", "certification", or "membership"

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    # Relationship
    builder = relationship("BuilderProfile", back_populates="credentials")

    def __repr__(self):
        return f"<BuilderCredential(type='{self.credential_type}', name='{self.name}')>"
