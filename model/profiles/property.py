

# model/profiles/property.py
from sqlalchemy import (
    Column, String, Integer, Float, Text, JSON, TIMESTAMP, ForeignKey
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base
from model.profiles.builder import builder_portfolio


class Property(Base):
    """
    Mirrors SwiftUI PropertyRef/PropertyPage domain model.
    Uses internal numeric IDs with a public UUID string (public_id) for app routing.
    Associations to Builder, Community, and optional SalesRep.
    """
    __tablename__ = "properties"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    public_id = Column(String(36), unique=True, nullable=False)  # UUID string

    # Core
    title = Column(String(255), nullable=False)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builders.id", ondelete="RESTRICT"), nullable=False)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="RESTRICT"), nullable=False)
    sales_rep_id = Column(MyBIGINT(unsigned=True), ForeignKey("sales_reps.id", ondelete="SET NULL"))

    # Details
    gallery = Column(JSON, nullable=False, default=list)           # list[str] of image URLs
    beds = Column(Integer, nullable=False)
    baths = Column(Float, nullable=False)
    sqft = Column(Integer, nullable=False)

    # Display pricing/meta kept as strings to match UI formatting; normalize later if needed
    price = Column(String(64))                 # e.g., "$549,900"
    lot_size = Column(String(64))              # e.g., "8,450 sqft"
    year_built = Column(String(16))
    property_tax_annual = Column(String(64))   # e.g., "$9,800/yr" or "2.75%"
    community_dues_monthly = Column(String(64))

    # Plans & collateral
    plan_images = Column(JSON, nullable=False, default=list)      # list[str]
    plan_pdf = Column(String(1024))                               # URL string

    # Meta
    tags = Column(JSON, nullable=False, default=list)             # list[str]
    about = Column(Text)

    # Engagement (optional — can be moved to analytics service later)
    like_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    save_count = Column(Integer, nullable=False, default=0)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    builder = relationship("Builder")
    community = relationship("Community")
    sales_rep = relationship("SalesRep")

    # Many-to-many: any builders linked to this property via builder_portfolio
    # Note: keep `builder` (FK) as the primary/owning builder; use `builders` for portfolio associations.
    builders = relationship(
        "Builder",
        secondary=builder_portfolio,
        back_populates="properties",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Property(title='{self.title}', beds={self.beds}, baths={self.baths}, sqft={self.sqft})>"