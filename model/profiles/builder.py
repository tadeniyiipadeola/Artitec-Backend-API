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
    build_id = Column(String(64), unique=True, nullable=False, default=_gen_builder_public_id)

    # One-to-one link to platform user (the account that owns/manages this builder)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

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
    address = Column(String(255))
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
