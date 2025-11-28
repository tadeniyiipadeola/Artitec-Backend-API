# model/property.py
from sqlalchemy import (
    Column, String, Integer, Float, Text, JSON, TIMESTAMP, ForeignKey, Numeric, Boolean
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship, validates
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

    # Property classification
    property_type = Column(String(64), nullable=True)  # single_family, townhome, condo, etc.
    listing_status = Column(String(50), nullable=True)  # available, pending, under_contract, sold

    # Structural details
    stories = Column(Integer, nullable=True)
    garage_spaces = Column(Integer, nullable=True)

    # Lot characteristics
    lot_number = Column(String(64), nullable=True)  # Lot number for new construction
    corner_lot = Column(Boolean, default=False, nullable=True)
    cul_de_sac = Column(Boolean, default=False, nullable=True)
    lot_backing = Column(String(128), nullable=True)  # greenbelt, pond, street, etc.
    views = Column(String(255), nullable=True)

    # School information
    school_district = Column(String(255), nullable=True)
    elementary_school = Column(String(255), nullable=True)
    middle_school = Column(String(255), nullable=True)
    high_school = Column(String(255), nullable=True)
    school_ratings = Column(JSON, nullable=True)

    # Builder-specific information
    model_home = Column(Boolean, default=False, nullable=True)
    quick_move_in = Column(Boolean, default=False, nullable=True)
    construction_stage = Column(String(64), nullable=True)  # pre_construction, under_construction, completed
    estimated_completion = Column(String(64), nullable=True)  # Date as string
    builder_plan_name = Column(String(255), nullable=True)
    builder_series = Column(String(255), nullable=True)
    elevation_options = Column(String(255), nullable=True)

    # Interior features
    flooring_types = Column(String(255), nullable=True)
    countertop_materials = Column(String(255), nullable=True)
    appliances = Column(String(255), nullable=True)
    game_room = Column(Boolean, default=False, nullable=True)
    study_office = Column(Boolean, default=False, nullable=True)
    bonus_rooms = Column(String(255), nullable=True)

    # Outdoor amenities
    pool_type = Column(String(64), nullable=True)  # private, community, none
    covered_patio = Column(Boolean, default=False, nullable=True)
    outdoor_kitchen = Column(Boolean, default=False, nullable=True)
    landscaping = Column(String(255), nullable=True)

    # Pricing & market information
    price_per_sqft = Column(Numeric(10, 2), nullable=True)
    days_on_market = Column(Integer, nullable=True)
    builder_incentives = Column(Text, nullable=True)
    upgrades_included = Column(Text, nullable=True)
    upgrades_value = Column(Numeric(12, 2), nullable=True)

    # HOA & restrictions
    hoa_fee_monthly = Column(Numeric(10, 2), nullable=True)
    pet_restrictions = Column(String(255), nullable=True)
    lease_allowed = Column(Boolean, default=True, nullable=True)

    # Energy & utilities
    energy_rating = Column(String(64), nullable=True)
    internet_providers = Column(String(255), nullable=True)

    # Tax & financial
    annual_property_tax = Column(Numeric(12, 2), nullable=True)
    assumable_loan = Column(Boolean, default=False, nullable=True)

    # Media & virtual tours
    virtual_tour_url = Column(String(1024), nullable=True)
    floor_plan_url = Column(String(1024), nullable=True)
    matterport_link = Column(String(1024), nullable=True)

    # Availability & showing
    move_in_date = Column(String(64), nullable=True)  # Date as string
    showing_instructions = Column(Text, nullable=True)

    # Collection metadata
    source_url = Column(String(1024), nullable=True)
    data_confidence = Column(Float, nullable=True)

    # Associations / flags
    # REQUIRED foreign keys - Properties MUST belong to a builder and community
    # Using RESTRICT to prevent accidental deletion of builders/communities with properties
    # Changed from BIGINT to Integer to match builder_profiles.id and communities.id types
    builder_id = Column(Integer, ForeignKey("builder_profiles.id", ondelete="RESTRICT"), nullable=False)
    builder_id_string = Column(String(50), nullable=True)  # String format builder ID (e.g., "BLD-PSALMSFINE-0420")
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="RESTRICT"), nullable=False)
    community_id_string = Column(String(64), nullable=True)  # String format community ID (e.g., "CMY-23F55C68")
    has_pool = Column(Boolean, default=False)  # Legacy field, use pool_type instead

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
    approved_at = Column(TIMESTAMP, nullable=True)  # When the property was approved
    approved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Admin who approved it

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

    @validates('builder_id')
    def validate_builder_id(self, key, value):
        """
        Validate that builder_id is provided and is not None.

        This validator provides runtime validation beyond the database constraint.
        Properties MUST belong to a builder from BuilderProfile table.
        """
        if value is None:
            raise ValueError(
                "Property must have a builder_id. "
                "Properties can only be created for builders in the BuilderProfile table."
            )
        return value

    @validates('community_id')
    def validate_community_id(self, key, value):
        """
        Validate that community_id is provided and is not None.

        This validator provides runtime validation beyond the database constraint.
        Properties MUST belong to a community.
        """
        if value is None:
            raise ValueError(
                "Property must have a community_id. "
                "Properties must be associated with a community."
            )
        return value

    def __repr__(self):
        return f"<Property(title='{self.title}', city='{self.city}', price={self.price})>"


# Optional favorites model to support save/like behavior in routes/property/property.py
class FavoriteProperty(Base):
    __tablename__ = "favorite_properties"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    # Basic relationships (not strictly necessary for the router but helpful)
    # Using lazy='selectin' to avoid N+1 queries in list endpoints
    user = relationship("Users", lazy="selectin")
    property = relationship("Property", lazy="selectin")