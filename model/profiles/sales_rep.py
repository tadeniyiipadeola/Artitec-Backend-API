from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, func, Boolean, BigInteger as MyBIGINT
from sqlalchemy.orm import relationship
from model.base import Base  # or your declarative base import

class SalesRep(Base):
    __tablename__ = "sales_reps"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=True)

    full_name = Column(String(255), nullable=False)
    title = Column(String(128))
    email = Column(String(255))
    phone = Column(String(64))
    avatar_url = Column(String(1024))
    region = Column(String(128))
    office_address = Column(String(255))
    verified = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    builder = relationship("BuilderProfile", back_populates="sales_reps")
    community = relationship("Community", back_populates="sales_reps")