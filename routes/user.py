from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.db import get_db
from config.security import get_current_user
from model.user import Users
from src.schemas import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_me(current_user: Users = Depends(get_current_user)):
    """
    Returns the currently authenticated user.
    Requires a valid Bearer token.
    """
    return current_user


@router.get("/{public_id}", response_model=UserOut)
def get_user_by_public_id(public_id: str, db: Session = Depends(get_db)):
    """
    Returns a user by their public_id.
    Accessible without authentication (depending on your policy).
    """
    user = db.query(Users).filter(Users.public_id == public_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user