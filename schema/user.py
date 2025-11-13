from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from src.schemas import RoleOut


class UserBase(BaseModel):
    user_id: str  # users.user_id (e.g., USR-1699564234-A7K9M2)
    email: EmailStr
    first_name: str
    last_name: str
    phone_e164: Optional[str] = None
    # role_id removed - now using direct role string
    onboarding_completed: bool = False
    role: Optional[RoleOut] = None  # Dict with "key" and "name" or just string
    plan_tier: Optional[str] = "free"  # free, pro, enterprise
    is_email_verified: bool = False
    status: Optional[str] = "active"  # active, suspended, deleted
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserOut(UserBase):
    user_id: str  # users.user_id (string, e.g., USR-xxx)

    model_config = ConfigDict(from_attributes=True)