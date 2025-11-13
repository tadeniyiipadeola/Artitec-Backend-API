from sqlalchemy import Column, String, ForeignKey,Boolean, TIMESTAMP, func
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.orm import relationship
from model.base import Base

class SalesRep(Base):
    __tablename__ = "sales_reps"

    # Primary key (internal DB ID)
    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    # Sales Rep ID for API (e.g., SLS-1699564234-P7Q8R9)
    sales_rep_id = Column(String(50), unique=True, nullable=False, index=True)
    # FK to users.user_id (String) - the user account for this sales rep
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    # FK to builder_profiles.id (internal DB ID)
    builder_id = Column(MyBIGINT(unsigned=True), ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False)
    # FK to communities.id (internal DB ID)
    community_id = Column(MyBIGINT(unsigned=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=True)

    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
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