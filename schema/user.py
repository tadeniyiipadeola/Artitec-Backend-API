

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class Users(BaseModel):
    public_id: str
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    role_id: Optional[int] = None
    is_email_verified: bool = False
    onboarding_complete: bool = False


class UserCreate(Users):
    password: str


class UserUpdate(Users):
    password: Optional[str] = None


class UserOut(Users):
    public_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True