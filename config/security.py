"""
config.security
---------------
Centralized authentication helpers for FastAPI routes.

This module defines:
- JWT handling utilities (encode/decode)
- get_current_user()  → requires auth
- get_current_user_optional()  → returns user or None if not logged in
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config.db import get_db
from model.user import User  # adjust path if user model is elsewhere

# ---------------------------------------------------------------------------
# JWT CONFIG
# ---------------------------------------------------------------------------
SECRET_KEY = "supersecretkey_change_this"  # ⚠️ Replace with environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


# ---------------------------------------------------------------------------
# TOKEN HELPERS
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        return int(user_id) if user_id else None
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------------------------
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """Require valid JWT and return the user."""
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


def get_current_user_optional(
    db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """Return user if token is valid, otherwise None (no error)."""
    if not token:
        return None

    user_id = verify_token(token)
    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()