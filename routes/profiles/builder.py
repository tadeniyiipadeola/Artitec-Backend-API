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
from model.profiles.builder import (
    BuilderProfile as BuilderModel,
    BuilderAward as BuilderAwardModel,
    BuilderHomePlan as BuilderHomePlanModel,
    BuilderCredential as BuilderCredentialModel,
)
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
        BuilderAwardOut,
        BuilderAwardCreate,
        BuilderAwardUpdate,
        BuilderHomePlanOut,
        BuilderHomePlanCreate,
        BuilderHomePlanUpdate,
        BuilderCredentialOut,
        BuilderCredentialCreate,
        BuilderCredentialUpdate,
    )
except Exception as e:  # pragma: no cover
    raise ImportError("schema.builder.* Pydantic schemas are required") from e


router = APIRouter()

try:
    from model.enterprise import BuilderTeamMember
except Exception:
    BuilderTeamMember = None  # type: ignore


# ------------------------------ helpers -------------------------------------

def _ensure_user(db: Session, user_id: str) -> Users:
    """Resolve user_id (string) to Users model instance"""
    user = db.query(Users).filter(Users.user_id == user_id).first()
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

@router.get("/me/profiles", response_model=List[BuilderProfileOut])
def list_my_builder_profiles(
    *,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    List all builder profiles accessible by the authenticated user.
    Includes profiles owned by the user or where user is a team member.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = current_user.user_id
    profiles = []

    # Get profiles owned by this user
    owned = db.query(BuilderModel).filter(BuilderModel.user_id == user_id).all()
    profiles.extend(owned)

    # Get profiles where user is a team member (if BuilderTeamMember model exists)
    if BuilderTeamMember:
        team_memberships = db.query(BuilderTeamMember).filter(
            BuilderTeamMember.user_id == user_id
        ).all()

        for membership in team_memberships:
            # Get the builder profile by builder_id
            builder = db.query(BuilderModel).filter(
                BuilderModel.builder_id == membership.builder_id
            ).first()
            if builder and builder not in profiles:
                profiles.append(builder)

    return [BuilderProfileOut.model_validate(p) for p in profiles]


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
    uid = user.user_id

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
    uid = user.user_id

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
    uid = user.user_id

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
    uid = user.user_id

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
    """List all sales reps for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

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
    """Create a sales rep for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

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
    """Update a sales rep for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

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
    """Delete a sales rep for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

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


# --------------------------- awards (scoped by builder user_id) ---------------------------

@router.get("/{user_id}/awards", response_model=List[BuilderAwardOut])
def list_builder_awards(
    *,
    db: Session = Depends(get_db),
    user_id: str,
):
    """List all awards for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    rows = (
        db.query(BuilderAwardModel)
        .filter(BuilderAwardModel.builder_id == builder.id)
        .order_by(BuilderAwardModel.year.desc())
        .all()
    )
    return [BuilderAwardOut.model_validate(r) for r in rows]


@router.post("/{user_id}/awards", response_model=BuilderAwardOut, status_code=status.HTTP_201_CREATED)
def create_builder_award(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    payload: BuilderAwardCreate,
):
    """Create an award for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    # Force the builder_id to the resolved builder PK to prevent cross-builder creation
    data = payload.model_dump(exclude_none=True)
    data["builder_id"] = builder.id

    obj = BuilderAwardModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderAwardOut.model_validate(obj)


@router.put("/{user_id}/awards/{award_id}", response_model=BuilderAwardOut)
@router.patch("/{user_id}/awards/{award_id}", response_model=BuilderAwardOut)
def update_builder_award(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    award_id: int,
    payload: BuilderAwardUpdate,
):
    """Update an award for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    obj = db.query(BuilderAwardModel).filter(
        BuilderAwardModel.id == award_id,
        BuilderAwardModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Award not found for this builder")

    data = payload.model_dump(exclude_none=True)
    # Prevent reassignment to another builder_id via payload
    data.pop("builder_id", None)

    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderAwardOut.model_validate(obj)


@router.delete("/{user_id}/awards/{award_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_award(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    award_id: int,
):
    """Delete an award for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    obj = db.query(BuilderAwardModel).filter(
        BuilderAwardModel.id == award_id,
        BuilderAwardModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Award not found for this builder")

    db.delete(obj)
    db.commit()
    return None


# --------------------------- home plans (scoped by builder user_id) ---------------------------

@router.get("/{user_id}/home-plans", response_model=List[BuilderHomePlanOut])
def list_builder_home_plans(
    *,
    db: Session = Depends(get_db),
    user_id: str,
):
    """List all home plans for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    rows = (
        db.query(BuilderHomePlanModel)
        .filter(BuilderHomePlanModel.builder_id == builder.id)
        .order_by(BuilderHomePlanModel.name.asc())
        .all()
    )
    return [BuilderHomePlanOut.model_validate(r) for r in rows]


@router.post("/{user_id}/home-plans", response_model=BuilderHomePlanOut, status_code=status.HTTP_201_CREATED)
def create_builder_home_plan(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    payload: BuilderHomePlanCreate,
):
    """Create a home plan for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    # Force the builder_id to the resolved builder PK to prevent cross-builder creation
    data = payload.model_dump(exclude_none=True)
    data["builder_id"] = builder.id

    obj = BuilderHomePlanModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderHomePlanOut.model_validate(obj)


@router.put("/{user_id}/home-plans/{plan_id}", response_model=BuilderHomePlanOut)
@router.patch("/{user_id}/home-plans/{plan_id}", response_model=BuilderHomePlanOut)
def update_builder_home_plan(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    plan_id: int,
    payload: BuilderHomePlanUpdate,
):
    """Update a home plan for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    obj = db.query(BuilderHomePlanModel).filter(
        BuilderHomePlanModel.id == plan_id,
        BuilderHomePlanModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home plan not found for this builder")

    data = payload.model_dump(exclude_none=True)
    # Prevent reassignment to another builder_id via payload
    data.pop("builder_id", None)

    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderHomePlanOut.model_validate(obj)


@router.delete("/{user_id}/home-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_home_plan(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    plan_id: int,
):
    """Delete a home plan for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    obj = db.query(BuilderHomePlanModel).filter(
        BuilderHomePlanModel.id == plan_id,
        BuilderHomePlanModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Home plan not found for this builder")

    db.delete(obj)
    db.commit()
    return None


# --------------------------- credentials (scoped by builder user_id) ---------------------------

@router.get("/{user_id}/credentials", response_model=List[BuilderCredentialOut])
def list_builder_credentials(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    credential_type: Optional[str] = Query(None, description="Filter by credential type: license, certification, or membership"),
):
    """List all credentials for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    query = db.query(BuilderCredentialModel).filter(BuilderCredentialModel.builder_id == builder.id)

    if credential_type:
        query = query.filter(BuilderCredentialModel.credential_type == credential_type)

    rows = query.order_by(BuilderCredentialModel.credential_type.asc(), BuilderCredentialModel.name.asc()).all()
    return [BuilderCredentialOut.model_validate(r) for r in rows]


@router.post("/{user_id}/credentials", response_model=BuilderCredentialOut, status_code=status.HTTP_201_CREATED)
def create_builder_credential(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    payload: BuilderCredentialCreate,
):
    """Create a credential for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    # Force the builder_id to the resolved builder PK to prevent cross-builder creation
    data = payload.model_dump(exclude_none=True)
    data["builder_id"] = builder.id

    obj = BuilderCredentialModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderCredentialOut.model_validate(obj)


@router.put("/{user_id}/credentials/{credential_id}", response_model=BuilderCredentialOut)
@router.patch("/{user_id}/credentials/{credential_id}", response_model=BuilderCredentialOut)
def update_builder_credential(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    credential_id: int,
    payload: BuilderCredentialUpdate,
):
    """Update a credential for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    obj = db.query(BuilderCredentialModel).filter(
        BuilderCredentialModel.id == credential_id,
        BuilderCredentialModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found for this builder")

    data = payload.model_dump(exclude_none=True)
    # Prevent reassignment to another builder_id via payload
    data.pop("builder_id", None)

    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderCredentialOut.model_validate(obj)


@router.delete("/{user_id}/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_credential(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    credential_id: int,
):
    """Delete a credential for a specific builder (by builder's user user_id)"""
    user = _ensure_user(db, user_id)
    uid = user.user_id

    # Get builder profile
    builder = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not builder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    obj = db.query(BuilderCredentialModel).filter(
        BuilderCredentialModel.id == credential_id,
        BuilderCredentialModel.builder_id == builder.id
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found for this builder")

    db.delete(obj)
    db.commit()
    return None
