# schema/password_reset.py
"""
Pydantic schemas for password reset functionality.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset flow."""
    email: EmailStr = Field(..., description="User's email address")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ForgotPasswordResponse(BaseModel):
    """Response after requesting password reset."""
    message: str = Field(
        default="If an account with that email exists, a password reset link has been sent.",
        description="Success message (same for existing and non-existing users for security)"
    )
    # Note: We don't reveal if email exists or not for security


class ResetPasswordRequest(BaseModel):
    """Request to reset password with token."""
    token: str = Field(..., min_length=32, max_length=255, description="Password reset token from email")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if len(v) > 128:
            raise ValueError('Password must not exceed 128 characters')

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        # Optional: Check for special character (uncomment if needed)
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        #     raise ValueError('Password must contain at least one special character')

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                "new_password": "NewSecurePassword123"
            }
        }


class ResetPasswordResponse(BaseModel):
    """Response after successfully resetting password."""
    message: str = Field(
        default="Password has been reset successfully. You can now log in with your new password.",
        description="Success message"
    )
    user_id: Optional[str] = Field(None, description="User ID (optional, for frontend redirect)")


class VerifyResetTokenRequest(BaseModel):
    """Request to verify if a reset token is valid."""
    token: str = Field(..., min_length=32, max_length=255, description="Password reset token")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
            }
        }


class VerifyResetTokenResponse(BaseModel):
    """Response for token verification."""
    valid: bool = Field(..., description="Whether token is valid")
    message: str = Field(..., description="Reason if invalid")
    expires_at: Optional[datetime] = Field(None, description="When token expires (if valid)")
    user_email: Optional[str] = Field(None, description="User email (if valid, for display)")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "message": "Token is valid",
                "expires_at": "2024-11-12T16:30:00",
                "user_email": "u***@example.com"
            }
        }


__all__ = [
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "VerifyResetTokenRequest",
    "VerifyResetTokenResponse",
]
