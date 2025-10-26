from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.db import get_db
from config.security import get_current_user, require_admin_or_self
from model.user import Users, Role
from src.schemas import UserOut
from src.schemas import UserRoleUpdate

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
    user = db.scalar(select(Users).where(Users.public_id == public_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.patch("/me/role", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_my_role(
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    me: Users = Depends(get_current_user),
):
    # Find the Role row by key (e.g., "buyer")
    role_row = db.scalar(select(Role).where(Role.key == payload.role))
    if not role_row:
        raise HTTPException(status_code=404, detail="Role not found.")

    # Prevent non-admins from self-promoting to admin
    if role_row.key == "admin" and getattr(me.role, "key", None) != "admin":
        raise HTTPException(status_code=403, detail="You cannot assign yourself an admin role.")

    me.role_id = role_row.id
    db.add(me)
    db.commit()
    db.refresh(me)
    return me


@router.patch("/{public_id}/role", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_role_by_public_id(
    public_id: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    caller: Users = Depends(get_current_user),
    _authz: bool = Depends(require_admin_or_self),
):
    user = db.scalar(select(Users).where(Users.public_id == public_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    role_row = db.scalar(select(Role).where(Role.key == payload.role))
    if not role_row:
        raise HTTPException(status_code=404, detail="Role not found.")

    # Only admins may assign the admin role
    if role_row.key == "admin":
        if getattr(getattr(caller, "role", None), "key", None) != "admin":
            raise HTTPException(status_code=403, detail="Only admins can assign the admin role.")

    user.role_id = role_row.id
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
