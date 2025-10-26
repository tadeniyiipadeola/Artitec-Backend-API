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
from sqlalchemy import select

from config.db import get_db
from model.user import Users  # adjust path if user model is elsewhere
# add (or fix) this import at the top with your other imports
from jose import JWTError, jwt
import os
import logging
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# JWT CONFIG
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()
# Prefer SECRET_KEY, fallback to JWT_SECRET (legacy), and finally a dev default
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "dev-secret-artitec-key"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# TOKEN HELPERS
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# verify_token() expects a JWT created by create_access_token() using the same SECRET_KEY and ALGORITHM
def verify_token(token: str) -> str:
    """
    Decode JWT and return the subject (user id).
    Raise HTTP 401 for any auth problem.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Ensure these exist in your module:
        # SECRET_KEY: str = "..." and ALGORITHM: str = "HS256" (or your algo)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        return user_id
    except JWTError:
        # Invalid signature, expired token, or malformed token
        raise credentials_exception
    except Exception as e:
        logging.getLogger("security").warning("JWT decode error: %s", e)
        raise credentials_exception

# ---------------------------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------------------------
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> Users:
    """Require valid JWT and return the user."""
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(Users).where(Users.public_id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


def get_current_user_optional(
    db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[Users]:
    """Return user if token is valid, otherwise None (no error)."""
    if not token:
        return None

    user_id = verify_token(token)
    if not user_id:
        return None

    return db.scalar(select(Users).where(Users.public_id == user_id))


# ---------------------------------------------------------------------------
# ADMIN OR SELF DEPENDENCY
# ---------------------------------------------------------------------------
def require_admin_or_self(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional),
    public_id: Optional[str] = None,
) -> bool:
    """Authorize request: allow if caller is admin or matches the target public_id.
    If no `public_id` is provided by the path, only admins are allowed.
    This function is designed to be used as a FastAPI dependency.
    """
    # If no token, reject
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    caller_public_id = verify_token(token)
    caller = db.scalar(select(Users).where(Users.public_id == caller_public_id))
    if not caller:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth")

    # Determine admin via role key, if relationship is present
    role_key = getattr(getattr(caller, "role", None), "key", None)
    is_admin = role_key == "admin"

    # If a target public_id is provided (from route path params), allow when self or admin
    if public_id is not None:
        if is_admin or caller.public_id == str(public_id):
            return True
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # No target id provided: only admins may proceed
    if is_admin:
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")