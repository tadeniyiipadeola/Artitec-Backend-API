# routes/password_reset.py
"""
Password reset routes - forgot password and reset password functionality.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from config.db import get_db
from config.security import hash_password
from model.user import Users, UserCredential
from model.password_reset import PasswordResetToken
from schema.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyResetTokenRequest,
    VerifyResetTokenResponse,
)
from src.email_service import get_email_service

router = APIRouter()

# Configuration
TOKEN_EXPIRY_HOURS = 1
TOKEN_LENGTH = 32  # 32 bytes = 64 hex characters


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(TOKEN_LENGTH)


def hash_token(token: str) -> str:
    """Hash a token for database storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def mask_email(email: str) -> str:
    """Mask email for privacy (u***@example.com)."""
    local, domain = email.split('@')
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]
    return f"{masked_local}@{domain}"


def cleanup_expired_tokens(db: Session, user_id: str):
    """Clean up expired tokens for a user."""
    now = datetime.utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.expires_at < now
    ).delete()
    db.commit()


def invalidate_user_tokens(db: Session, user_id: str):
    """Invalidate all existing tokens for a user."""
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None)
    ).update({"used_at": datetime.utcnow()})
    db.commit()


@router.post("/forgot-password", response_model=ForgotPasswordResponse, tags=["Auth"])
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset link.

    Steps:
    1. Check if user with email exists
    2. Generate secure reset token
    3. Store token in database with expiration
    4. Send reset email
    5. Return success (same response regardless of email existence for security)

    **Rate Limiting:** Consider implementing rate limiting on this endpoint
    to prevent abuse (e.g., max 3 requests per email per hour).
    """
    # Look up user by email
    user = db.scalar(select(Users).where(Users.email == request.email))

    # Always return success message (don't reveal if email exists)
    response = ForgotPasswordResponse()

    if not user:
        # User doesn't exist - return success anyway for security
        # (prevents email enumeration attacks)
        return response

    # Clean up old expired tokens
    cleanup_expired_tokens(db, user.user_id)

    # Invalidate any existing unused tokens for this user
    # (security: only one active reset link at a time)
    invalidate_user_tokens(db, user.user_id)

    # Generate new token
    token = generate_reset_token()
    token_hash_value = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)

    # Save token to database
    reset_token = PasswordResetToken(
        user_id=user.user_id,
        token=token,  # Store plain for lookup (still secure as it's random)
        token_hash=token_hash_value,  # Store hash for verification
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()

    # Send reset email
    email_service = get_email_service()
    user_name = f"{user.first_name} {user.last_name}"

    success = email_service.send_password_reset_email(
        to_email=user.email,
        reset_token=token,
        user_name=user_name
    )

    if not success:
        # Log error but still return success to user
        print(f"❌ Failed to send reset email to {user.email}")
        # In production, you might want to log this to a monitoring service

    return response


@router.post("/verify-reset-token", response_model=VerifyResetTokenResponse, tags=["Auth"])
def verify_reset_token(
    request: VerifyResetTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Verify if a password reset token is valid.

    Useful for frontend to check token validity before showing reset form.

    Returns:
    - valid: Whether token is valid
    - message: Reason if invalid
    - expires_at: Expiration time if valid
    - user_email: Masked email if valid
    """
    # Look up token
    reset_token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token == request.token
        )
    )

    if not reset_token:
        return VerifyResetTokenResponse(
            valid=False,
            message="Invalid or expired token"
        )

    # Check if token is valid
    if not reset_token.is_valid():
        if reset_token.used_at:
            message = "This token has already been used"
        else:
            message = "This token has expired"

        return VerifyResetTokenResponse(
            valid=False,
            message=message
        )

    # Get user info
    user = db.scalar(select(Users).where(Users.user_id == reset_token.user_id))

    if not user:
        return VerifyResetTokenResponse(
            valid=False,
            message="User not found"
        )

    return VerifyResetTokenResponse(
        valid=True,
        message="Token is valid",
        expires_at=reset_token.expires_at,
        user_email=mask_email(user.email)
    )


@router.post("/reset-password", response_model=ResetPasswordResponse, tags=["Auth"])
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using a valid token.

    Steps:
    1. Verify token exists and is valid
    2. Update user's password
    3. Mark token as used
    4. Send confirmation email
    5. Return success

    **Security Note:** After successful reset, all active sessions
    should be invalidated (implement if session management exists).
    """
    # Look up token
    reset_token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token == request.token
        )
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Verify token is valid
    if not reset_token.is_valid():
        if reset_token.used_at:
            detail = "This reset link has already been used"
        else:
            detail = "This reset link has expired. Please request a new one."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

    # Get user
    user = db.scalar(select(Users).where(Users.user_id == reset_token.user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Hash new password
    new_password_hash = hash_password(request.new_password)

    # Update user credentials
    user_cred = db.scalar(
        select(UserCredential).where(UserCredential.user_id == user.id)
    )

    if user_cred:
        user_cred.password_hash = new_password_hash
        user_cred.last_password_change = datetime.utcnow()
    else:
        # Create credentials if they don't exist (edge case)
        user_cred = UserCredential(
            user_id=user.id,
            password_hash=new_password_hash,
            password_algo="bcrypt",
            last_password_change=datetime.utcnow()
        )
        db.add(user_cred)

    # Mark token as used
    reset_token.mark_as_used()

    # Commit changes
    db.commit()

    # Send confirmation email
    email_service = get_email_service()
    user_name = f"{user.first_name} {user.last_name}"

    email_service.send_password_changed_notification(
        to_email=user.email,
        user_name=user_name
    )

    # TODO: Invalidate all active sessions for this user (if session management exists)
    # This forces user to log in again with new password

    return ResetPasswordResponse(
        message="Password has been reset successfully. You can now log in with your new password.",
        user_id=user.user_id
    )


@router.post("/cancel-reset-token", tags=["Auth"])
def cancel_reset_token(
    request: VerifyResetTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Cancel/invalidate a reset token.

    Useful if user wants to cancel the reset request.
    """
    reset_token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token == request.token
        )
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )

    # Mark as used (invalidate)
    reset_token.mark_as_used()
    db.commit()

    return {"message": "Reset token has been cancelled"}


# Cleanup endpoint (admin only - implement auth check)
@router.delete("/cleanup-expired-tokens", tags=["Admin"])
def cleanup_all_expired_tokens(db: Session = Depends(get_db)):
    """
    Clean up all expired tokens (admin endpoint).

    **TODO:** Add admin authentication check.
    """
    now = datetime.utcnow()
    deleted_count = db.query(PasswordResetToken).filter(
        PasswordResetToken.expires_at < now
    ).delete()

    db.commit()

    return {
        "message": f"Cleaned up {deleted_count} expired tokens",
        "deleted_count": deleted_count
    }
