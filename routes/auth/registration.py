# routes/auth/registration.py
"""
User registration endpoints - Signup and user creation
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging

from config.db import get_db
from config.settings import REFRESH_TTL_DAYS
from model.user import Users, UserCredential, EmailVerification, SessionToken, Role, get_role_display_name
from src.schemas import RegisterIn, AuthOut, UserOut
from src.utils import gen_public_id, gen_token_hex, hash_password, make_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/register",
    response_model=AuthOut,
    responses={
        200: {"description": "Registration successful"},
        400: {"description": "Bad Request - Passwords do not match"},
        401: {"description": "Unauthorized"},
        409: {"description": "Conflict - Email already in use"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error - Default user type not seeded or unexpected error"}
    },
    openapi_extra={"security": []}
)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    logger.info("Register endpoint called with email=%s", body.email)
    logger.debug("Handling /register request body: %s", body.dict(exclude={'password','confirm_password'}))
    # Pick a temporary default role so we can create the record now; update on next step
    role_row = db.query(Role).filter(Role.key == "buyer").one_or_none()
    if not role_row:
        # Fallback to any available role
        role_row = db.query(Role).first()
    if not role_row:
        logger.error("Default role not found")
        raise HTTPException(
            status_code=500,
            detail="Default roles not seeded. Seed roles with at least one entry (e.g., 'buyer')."
        )

    logger.debug("Checking if email already exists: %s", body.email)
    if db.query(Users).filter(Users.email == body.email).first():
        logger.warning("Email already in use: %s", body.email)
        raise HTTPException(status_code=409, detail="Email already in use")

    logger.debug("Validating password confirmation")
    # Ensure password and confirmation match (defensive, even though schema validates it)
    if body.password != body.confirm_password:
        logger.warning("Passwords do not match for email=%s", body.email)
        raise HTTPException(status_code=400, detail="Passwords do not match")

    u = Users(
        user_id=gen_public_id(),
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        phone_e164=body.phone_e164,
        role=role_row.key  # Direct role string instead of FK
    )
    db.add(u)
    db.flush()
    logger.info("User created with id=%s, user_id=%s", u.id, u.user_id)

    creds = UserCredential(
        user_id=u.id,
        password_hash=hash_password(body.password),
        last_password_change=datetime.utcnow()
    )
    db.add(creds)

    ver = EmailVerification(
        user_id=u.id,
        token=gen_token_hex(32),
        expires_at=datetime.utcnow() + timedelta(days=2)
    )
    db.add(ver)

    refresh = gen_token_hex(32)
    sess = SessionToken(
        user_id=u.id,
        refresh_token=refresh,
        user_agent=request.headers.get("user-agent"),
        ip_addr=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TTL_DAYS)
    )
    db.add(sess)
    db.commit()

    # Send verification email after commit (so token is saved)
    from src.email_service import get_email_service
    email_service = get_email_service()
    user_name = f"{u.first_name} {u.last_name}"
    email_service.send_email_verification(
        to_email=u.email,
        verification_token=ver.token,
        user_name=user_name
    )
    logger.info("Registration committed for user id=%s", u.id)
    db.refresh(u)

    access = make_access_token(u.user_id, u.id, u.email)
    logger.info("Registration successful for user email=%s", body.email)
    # Build role dict for response
    if u.role:
        role_out = {"key": u.role, "name": get_role_display_name(u.role)}
    else:
        role_out = None

    return AuthOut(
        user=UserOut(
            public_id=u.user_id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            phone_e164=u.phone_e164,
            role=role_out,
            is_email_verified=u.is_email_verified,
            onboarding_completed=u.onboarding_completed,
            plan_tier=u.plan_tier,
            created_at=u.created_at,
            updated_at=u.updated_at
        ),
        access_token=access,
        refresh_token=refresh,
        requires_email_verification=True
    )
