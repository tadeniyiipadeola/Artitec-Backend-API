# model/property.py
from sqlalchemy import (
    Column, String, Integer, Float, Text, JSON, TIMESTAMP, ForeignKey, Numeric, Boolean
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from model.base import Base
# Import association table from builder module (no circular import back from builder)
from model.profiles.builder import builder_portfolio


class Property(Base):
    """Primary Property listing model.

    Matches the Pydantic schema in schema/property.py and is compatible with
    the routes in routes/property/property.py.
    """

    __tablename__ = "properties"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Ownership / authorship
    owner_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Core details
    title = Column(String(140), nullable=False)
    description = Column(Text)

    # Address / location
    address1 = Column(String(255), nullable=False)
    address2 = Column(String(255))
    city = Column(String(120), nullable=False)
    state = Column(String(120), nullable=False)
    postal_code = Column(String(20), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

    # Specs
    price = Column(Numeric(12, 2), nullable=False)
    bedrooms = Column(Integer, nullable=False, default=0)
    bathrooms = Column(Float, nullable=False, default=0)
    sqft = Column(Integer)
    lot_sqft = Column(Integer)
    year_built = Column(Integer)

    # Associations / flags
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="SET NULL"), nullable=True)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="SET NULL"), nullable=True)
    has_pool = Column(Boolean, default=False)

    # Media (store as JSON array of URLs)
    media_urls = Column(JSON)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    listed_at = Column(TIMESTAMP)

    # Relationships
    # Many-to-many with builders via portfolio (collection of builders who built this property)
    builders = relationship(
        "BuilderProfile",
        secondary=builder_portfolio,
        back_populates="properties",
        lazy="selectin",
    )

    # Optional direct relations (primary builder/community, if applicable)
    primary_builder = relationship("BuilderProfile", foreign_keys=[builder_id], lazy="selectin", viewonly=True)
    community = relationship("Community", foreign_keys=[community_id], lazy="selectin", viewonly=True)

    def __repr__(self):
        return f"<Property(title='{self.title}', city='{self.city}', price={self.price})>"


# Optional favorites model to support save/like behavior in routes/property/property.py
class FavoriteProperty(Base):
    __tablename__ = "favorite_properties"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(MyBIGINT(unsigned=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    # Basic relationships (not strictly necessary for the router but helpful)
    # Using lazy='selectin' to avoid N+1 queries in list endpoints
    user = relationship("Users", lazy="selectin")
    property = relationship("Property", lazy="selectin")