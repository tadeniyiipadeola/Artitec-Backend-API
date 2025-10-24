

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class Users(BaseModel):
    public_id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone_e164: Optional[str] = None
    role_type_id: int
    onboarding_completed: bool = False
    role: Optional[str] = None  # buyer, builder, community_admin, salesrep, admin
    is_email_verified: bool = False
    status: Optional[str] = "active"  # active, suspended, deleted
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class UserCreate(Users):
    password: str


class UserUpdate(Users):
    password: Optional[str] = None


class UserOut(Users):
    public_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True