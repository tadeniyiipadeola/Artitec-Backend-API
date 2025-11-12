"""Builder Profile routes (v1)

Exposes CRUD and list/search endpoints for builder profiles.
- Path prefix: /v1/profiles/builders
- Response schemas: Pydantic v2 (schema/builder.py)
- DB: SQLAlchemy session via config.db.get_db
- Includes: optional eager-load of properties & communities

Routes follow the buyer profile pattern: /{user_id} where user_id is the public_id (UUID string).
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session, selectinload
from model.profiles.builder import BuilderProfile as BuilderModel
try:
    from model.profiles.builder import SalesRep as SalesRepModel
except Exception:
    SalesRepModel = None  # type: ignore
from model.user import Users
from config.db import get_db
from config.security import get_current_user_optional

try:
    from model.social.models import Follow  # for follower metrics
except Exception:
    Follow = None  # type: ignore

try:
    from schema.builder import (
        BuilderProfileOut,
        BuilderProfileCreate,
        BuilderProfileUpdate,
        SalesRepOut,
        SalesRepCreate,
        SalesRepUpdate,
    )
except Exception as e:  # pragma: no cover
    raise ImportError("schema.builder.* Pydantic schemas are required") from e


router = APIRouter()


# ------------------------------ helpers -------------------------------------

def _ensure_user(db: Session, user_id: str) -> Users:
    """Resolve public_id (string) to Users model instance"""
    user = db.query(Users).filter(Users.public_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _parse_include(include: Optional[str]) -> Set[str]:
    if not include:
        return set()
    return {part.strip().lower() for part in include.split(",") if part.strip()}


def _apply_includes(query, include: Set[str]):
    if "properties" in include and hasattr(BuilderModel, "properties"):
        query = query.options(selectinload(BuilderModel.properties))
    if "communities" in include and hasattr(BuilderModel, "communities"):
        query = query.options(selectinload(BuilderModel.communities))
    return query


# ------------------------------- routes -------------------------------------

@router.get("/", response_model=List[BuilderProfileOut])
def list_builder_profiles(
    *,
    db: Session = Depends(get_db),
    include: Optional[str] = Query(
        None,
        description="Comma-separated includes: properties,communities",
        examples=["properties,communities"],
    ),
    q: Optional[str] = Query(None, description="Free-text search across common fields"),
    specialty: Optional[str] = Query(None, description="Filter by a specialty tag"),
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user_optional),
):
    includes = _parse_include(include)
    query = db.query(BuilderModel)
    query = _apply_includes(query, includes)

    # Text search across typical columns where available
    if q:
        ors = []
        for col_name in ("name", "about"):
            if hasattr(BuilderModel, col_name):
                ors.append(getattr(BuilderModel, col_name).ilike(f"%{q}%"))
        if ors:
            query = query.filter(or_(*ors))

    # Specialty filter (JSON array in MariaDB)
    if specialty and hasattr(BuilderModel, "specialties"):
        query = query.filter(text("JSON_CONTAINS(specialties, :needle)")).params(needle=f'"{specialty}"')

    # City filter
    if city and hasattr(BuilderModel, "city"):
        query = query.filter(BuilderModel.city.ilike(f"%{city}%"))

    rows: Sequence[BuilderModel] = query.offset(offset).limit(limit).all()
    return [BuilderProfileOut.model_validate(r) for r in rows]


@router.get("/{user_id}", response_model=BuilderProfileOut)
def get_builder_profile(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    include: Optional[str] = Query(None, description="Comma-separated includes: properties,communities"),
    current_user=Depends(get_current_user_optional),
):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    includes = _parse_include(include)
    query = db.query(BuilderModel)
    query = _apply_includes(query, includes)

    obj = query.filter(BuilderModel.user_id == uid).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    return BuilderProfileOut.model_validate(obj)


@router.post("/{user_id}", response_model=BuilderProfileOut, status_code=status.HTTP_201_CREATED)
def create_builder_profile(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    payload: BuilderProfileCreate,
):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    # Check if builder profile already exists for this user
    existing = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Builder profile already exists for this user")

    # Create builder profile
    data = payload.model_dump(exclude_none=True)
    obj = BuilderModel(**data, user_id=uid)
    db.add(obj)

    # Mark onboarding as completed
    user.onboarding_completed = True

    db.commit()
    db.refresh(obj)
    return BuilderProfileOut.model_validate(obj)


@router.put("/{user_id}", response_model=BuilderProfileOut)
@router.patch("/{user_id}", response_model=BuilderProfileOut)
def update_builder_profile(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    payload: BuilderProfileUpdate,
):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    obj = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    # Mark onboarding as completed (in case it wasn't set during creation)
    user.onboarding_completed = True

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderProfileOut.model_validate(obj)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_profile(
    *,
    db: Session = Depends(get_db),
    user_id: str
):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    obj = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    db.delete(obj)
    db.commit()
    return None


# --------------------------- sales reps (scoped by builder user_id) ---------------------------

@router.get("/{user_id}/sales-reps", response_model=List[SalesRepOut])
def list_builder_sales_reps(
    *,
    db: Session = Depends(get_db),
    user_id: str,
):
    """List all sales reps for a specific builder (by builder's user public_id)"""
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    rows = (
        db.query(SalesRepModel)
        .filter(SalesRepModel.builder_id == builder.id)
        .order_by(SalesRepModel.full_name.asc())
        .all()
    )
    return [SalesRepOut.model_validate(r) for r in rows]


@router.post("/{user_id}/sales-reps", response_model=SalesRepOut, status_code=status.HTTP_201_CREATED)
def create_builder_sales_rep(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    payload: SalesRepCreate,
):
    """Create a sales rep for a specific builder (by builder's user public_id)"""
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    # Force the builder_id to the resolved builder PK to prevent cross-builder creation
    data = payload.model_dump(exclude_none=True)
    data["builder_id"] = builder.id

    obj = SalesRepModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return SalesRepOut.model_validate(obj)


@router.put("/{user_id}/sales-reps/{rep_id}", response_model=SalesRepOut)
@router.patch("/{user_id}/sales-reps/{rep_id}", response_model=SalesRepOut)
def update_builder_sales_rep(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    rep_id: int,
    payload: SalesRepUpdate,
):
    """Update a sales rep for a specific builder (by builder's user public_id)"""
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    obj = db.query(SalesRepModel).filter(
        SalesRepModel.id == rep_id,
        SalesRepModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales rep not found for this builder")

    data = payload.model_dump(exclude_none=True)
    # Prevent reassignment to another builder_id via payload
    data.pop("builder_id", None)

    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return SalesRepOut.model_validate(obj)


@router.delete("/{user_id}/sales-reps/{rep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_sales_rep(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    rep_id: int,
):
    """Delete a sales rep for a specific builder (by builder's user public_id)"""
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    obj = db.query(SalesRepModel).filter(
        SalesRepModel.id == rep_id,
        SalesRepModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales rep not found for this builder")

    db.delete(obj)
    db.commit()
    return None
