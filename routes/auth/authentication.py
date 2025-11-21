# routes/auth/authentication.py
"""
Authentication endpoints - Login, logout, session management
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging

from config.db import get_db
from config.settings import REFRESH_TTL_DAYS
from model.user import Users, SessionToken, get_role_display_name
from src.schemas import LoginIn, AuthOut, UserOut
from src.utils import gen_token_hex, verify_password, make_access_token

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/login",
    response_model=AuthOut,
    responses={
        200: {"description": "Login successful"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized - Invalid email or password"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error"}
    },
    openapi_extra={"security": []}
)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    logger.info("Login attempt for email=%s", body.email)
    logger.debug("Handling /login request body: %s", body.dict(exclude={'password'}))
    u = db.query(Users).filter(Users.email == body.email, Users.status == "active").one_or_none()
    if not u or not u.creds or not verify_password(body.password, u.creds.password_hash):
        logger.warning("Invalid login attempt for email=%s", body.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

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
    logger.info("Login successful for user id=%s", u.id)

    logger.info("Login completed successfully for email=%s", body.email)
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
        access_token=make_access_token(u.user_id, u.id, u.email),
        refresh_token=refresh,
        requires_email_verification=not u.is_email_verified
    )
