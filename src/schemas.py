# src/schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, constr

class RegisterIn(BaseModel):
    full_name: constr(min_length=2, max_length=120)
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    user_type: constr(strip_whitespace=True, to_lower=True)
    phone_e164: Optional[constr(max_length=32)] = None

class UserOut(BaseModel):
    public_id: str
    full_name: str
    email: EmailStr
    user_type: str
    is_email_verified: bool
    created_at: datetime

class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str
    requires_email_verification: bool = True

class LoginIn(BaseModel):
    email: EmailStr
    password: str