from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from src.schemas import RoleOut


class UserBase(BaseModel):
    public_id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone_e164: Optional[str] = None
    role_id: Optional[int] = None
    onboarding_completed: bool = False
    role: Optional[RoleOut] = None
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
    public_id: str  # ensure consistent with DB (VARCHAR/UUID)

    model_config = ConfigDict(from_attributes=True)