# routes/email_verification.py
"""
Email verification routes - verify email address after registration.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from config.db import get_db
from model.user import Users, EmailVerification
from src.email_service import get_email_service

router = APIRouter()


# MARK: - Schemas
class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    message: str
    email_verified: bool


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    message: str


# MARK: - Endpoints
@router.post("/verify-email", response_model=VerifyEmailResponse, tags=["Auth"])
def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verify email address using token from verification email.

    Steps:
    1. Look up token in database
    2. Check if token is valid (not expired, not used)
    3. Mark user's email as verified
    4. Mark token as used
    5. Return success

    **Security:** Token is single-use and expires after 48 hours.
    """
    # Look up verification token
    verification = db.scalar(
        select(EmailVerification).where(
            EmailVerification.token == request.token
        )
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    # Check if token is valid (not expired and not used)
    now = datetime.utcnow()
    if verification.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link has expired. Please request a new one."
        )

    if verification.used_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link has already been used"
        )

    # Get user
    user = db.scalar(
        select(Users).where(Users.id == verification.user_id)
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already verified
    if user.is_email_verified:
        return VerifyEmailResponse(
            message="Email address is already verified",
            email_verified=True
        )

    # Mark email as verified
    user.is_email_verified = True

    # Mark token as used
    verification.used_at = datetime.utcnow()

    # Commit changes
    db.commit()

    return VerifyEmailResponse(
        message="Email address verified successfully! You can now access all features.",
        email_verified=True
    )


@router.post("/resend-verification", response_model=ResendVerificationResponse, tags=["Auth"])
def resend_verification_email(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Resend email verification link.

    Always returns success (prevents email enumeration).

    Steps:
    1. Look up user by email
    2. If user exists and not verified:
       - Invalidate old tokens
       - Generate new token
       - Send new verification email
    3. Always return success message

    **Rate Limiting:** Consider implementing rate limiting on this endpoint
    to prevent abuse (e.g., max 3 requests per email per hour).
    """
    # Look up user by email
    user = db.scalar(select(Users).where(Users.email == request.email))

    # Always return success message (prevents email enumeration)
    response = ResendVerificationResponse(
        message="If an unverified account exists with that email, a verification link has been sent."
    )

    if not user:
        # User doesn't exist - return success anyway for security
        return response

    if user.is_email_verified:
        # Already verified - return success anyway
        return response

    # Invalidate old verification tokens for this user
    db.query(EmailVerification).filter(
        EmailVerification.user_id == user.id,
        EmailVerification.used_at.is_(None)
    ).update({"used_at": datetime.utcnow()})

    # Generate new token
    from datetime import timedelta
    from src.utils import gen_token_hex

    new_verification = EmailVerification(
        user_id=user.id,
        token=gen_token_hex(32),
        expires_at=datetime.utcnow() + timedelta(days=2)
    )
    db.add(new_verification)
    db.commit()

    # Send verification email
    email_service = get_email_service()
    user_name = f"{user.first_name} {user.last_name}"

    success = email_service.send_email_verification(
        to_email=user.email,
        verification_token=new_verification.token,
        user_name=user_name
    )

    if not success:
        # Log error but still return success to user
        print(f"❌ Failed to send verification email to {user.email}")
        # In production, you might want to log this to a monitoring service

    return response


@router.get("/check-verification-status/{email}", tags=["Auth"])
def check_verification_status(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Check if an email address is verified.

    **Note:** This endpoint reveals if an email exists in the system.
    Consider if you want to make this public or require authentication.
    """
    user = db.scalar(select(Users).where(Users.email == email))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "email": user.email,
        "is_verified": user.is_email_verified
    }
