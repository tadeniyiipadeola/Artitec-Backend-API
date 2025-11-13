

from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional
from datetime import datetime

class SalesRepBase(BaseModel):
    full_name: str
    title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    region: Optional[str] = None
    office_address: Optional[str] = None
    verified: Optional[bool] = False
    builder_id: Optional[int] = None
    community_id: Optional[int] = None

class SalesRepCreate(SalesRepBase):
    builder_id: int

class SalesRepUpdate(BaseModel):
    full_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    region: Optional[str] = None
    office_address: Optional[str] = None
    verified: Optional[bool] = None
    builder_id: Optional[int] = None
    community_id: Optional[int] = None

class SalesRepOut(SalesRepBase):
    id: int
    sales_rep_id: str  # sales_reps.sales_rep_id (e.g., SLS-1699564234-P7Q8R9)
    user_id: Optional[str] = None  # FK to users.user_id (string, e.g., USR-xxx)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True