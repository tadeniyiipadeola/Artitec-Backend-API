# model/profiles/builder.py
from sqlalchemy import (
    Column, String, Float, Integer, Text, JSON, TIMESTAMP, ForeignKey
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from model.base import Base


class Builder(Base):
    """
    Mirrors SwiftUI Builder struct.
    Represents a home builder / construction firm with specialties and ratings.
    """
    __tablename__ = "builders"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    public_id = Column(String(64), unique=True, nullable=False)  # mirrors Swift 'id' (UUID/string)
    name = Column(String(255), nullable=False)
    website = Column(String(1024))  # Swift: URL? — stored as string
    specialties = Column(JSON)      # Swift: [String]
    rating = Column(Float)          # Swift: Double?
    communities_served = Column(JSON)  # Swift: hoasServed → communitiesServed

    # Optional extended fields
    about = Column(Text)
    phone = Column(String(64))
    email = Column(String(255))
    address = Column(String(255))
    verified = Column(Integer, default=0)  # 0 = not verified, 1 = verified

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationships
    sales_reps = relationship("SalesRep", back_populates="builder", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Builder(name='{self.name}', rating={self.rating})>"


class SalesRep(Base):
    """
    Represents a builder's assigned sales representative.
    Connects builders to their primary or regional reps.
    """
    __tablename__ = "sales_reps"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builders.id", ondelete="CASCADE"), nullable=False)

    full_name = Column(String(255), nullable=False)
    title = Column(String(128))
    email = Column(String(255))
    phone = Column(String(64))
    avatar_url = Column(String(1024))

    # Optional metadata
    region = Column(String(128))
    office_address = Column(String(255))
    verified = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    # Relationship
    builder = relationship("Builder", back_populates="sales_reps")

    def __repr__(self):
        return f"<SalesRep(name='{self.full_name}', builder='{self.builder_id}')>"