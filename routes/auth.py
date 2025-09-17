# routes/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from config.db import get_db
from config.settings import REFRESH_TTL_DAYS
from model.user import UserType, User, UserCredential, EmailVerification, SessionToken
from src.schemas import RegisterIn, LoginIn, AuthOut, UserOut
from src.utils import gen_public_id, gen_token_hex, hash_password, verify_password, make_access_token

router = APIRouter()

@router.post("/register", response_model=AuthOut)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    ut = db.query(UserType).filter(UserType.code == body.user_type).one_or_none()
    if not ut:
        raise HTTPException(status_code=400, detail="Invalid user_type")

    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already in use")

    u = User(
        public_id=gen_public_id(),
        email=body.email,
        full_name=body.full_name,
        phone_e164=body.phone_e164,
        user_type_id=ut.id
    )
    db.add(u)
    db.flush()

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
    db.refresh(u)

    access = make_access_token(u.public_id, u.id, u.email)
    return AuthOut(
        user=UserOut(
            public_id=u.public_id,
            full_name=u.full_name,
            email=u.email,
            user_type=ut.code,
            is_email_verified=u.is_email_verified,
            created_at=u.created_at
        ),
        access_token=access,
        refresh_token=refresh,
        requires_email_verification=True
    )

@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email, User.status == "active").one_or_none()
    if not u or not u.creds or not verify_password(body.password, u.creds.password_hash):
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

    return AuthOut(
        user=UserOut(
            public_id=u.public_id,
            full_name=u.full_name,
            email=u.email,
            user_type=u.user_type.code,
            is_email_verified=u.is_email_verified,
            created_at=u.created_at
        ),
        access_token=make_access_token(u.public_id, u.id, u.email),
        refresh_token=refresh,
        requires_email_verification=not u.is_email_verified
    )