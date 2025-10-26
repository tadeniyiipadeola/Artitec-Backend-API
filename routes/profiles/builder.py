"""Builder Profile routes (v1)

Exposes CRUD and list/search endpoints for builder profiles.
- Path prefix: /v1/profiles/builders
- Response schemas: Pydantic v2 (schema/builder.py)
- DB: SQLAlchemy session via config.db.get_db
- Includes: optional eager-load of properties & communities, follower metrics

If an auth dependency is not available yet, `current_user` will be None and
`is_following` will remain null in responses.
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
from config.db import get_db
from config.security import get_current_user_optional

# --- Project imports (adjust if your paths differ) ---------------------------
try:
    from config.db import get_db
except Exception as e:  # pragma: no cover
    raise ImportError("config.db.get_db is required for DB session dependency") from e

# Optional auth (graceful fallback to None)
try:
    from config.security import get_current_user_optional  # returns User | None
except Exception:  # pragma: no cover
    def get_current_user_optional():  # type: ignore
        return None


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

def _parse_include(include: Optional[str]) -> Set[str]:
    if not include:
        return set()
    return {part.strip().lower() for part in include.split(",") if part.strip()}


def _get_or_404(db: Session, org_id: int) -> BuilderModel:
    obj = db.query(BuilderModel).filter(BuilderModel.org_id == org_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")
    return obj


def _builder_id_by_org(db: Session, org_id: int) -> Optional[int]:
    """Resolve BuilderProfile.id from external org_id. Returns None if not found."""
    bp = db.query(BuilderModel.id).filter(BuilderModel.org_id == org_id).first()
    return bp[0] if bp else None


def _apply_includes(query, include: Set[str]):
    if "properties" in include and hasattr(BuilderModel, "properties"):
        query = query.options(selectinload(BuilderModel.properties))
    if "communities" in include and hasattr(BuilderModel, "communities"):
        query = query.options(selectinload(BuilderModel.communities))
    return query


def _attach_social_fields(
    db: Session,
    org_id: int,
    out_obj: BuilderProfileOut,
    current_user_id: Optional[int],
) -> None:
    """Mutates `out_obj` to set followers_count and is_following if Follow is available."""
    if Follow is None:
        return
    # followers_count
    followers_count = (
        db.query(func.count())
        .select_from(Follow)
        .filter(Follow.target_type == "builder", Follow.target_id == org_id)
        .scalar()
    )
    out_obj.followers_count = int(followers_count or 0)

    # is_following (only if caller is authenticated)
    if current_user_id:
        exists_q = (
            db.query(func.count())
            .select_from(Follow)
            .filter(
                Follow.target_type == "builder",
                Follow.target_id == org_id,
                Follow.follower_user_id == current_user_id,
            )
            .scalar()
        )
        out_obj.is_following = bool(exists_q)


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
        for col_name in ("company_name", "about", "notes"):
            if hasattr(BuilderModel, col_name):
                ors.append(getattr(BuilderModel, col_name).ilike(f"%{q}%"))
        if ors:
            query = query.filter(or_(*ors))

    # Specialty filter (JSON array in MariaDB)
    if specialty and hasattr(BuilderModel, "specialties"):
        query = query.filter(text("JSON_CONTAINS(specialties, :needle)")).params(needle=f'"{specialty}"')

    # City filter (either denormalized column or JSON search)
    if city:
        if hasattr(BuilderModel, "city"):
            query = query.filter(BuilderModel.city.ilike(f"%{city}%"))
        elif hasattr(BuilderModel, "service_areas"):
            query = query.filter(text("JSON_SEARCH(service_areas, 'one', :c) IS NOT NULL")).params(c=city)

    rows: Sequence[BuilderModel] = query.offset(offset).limit(limit).all()

    out_list: List[BuilderProfileOut] = []
    current_user_id = getattr(current_user, "id", None) if current_user else None
    for r in rows:
        out = BuilderProfileOut.model_validate(r)
        # Attach social metrics
        _attach_social_fields(db, getattr(r, "org_id"), out, current_user_id)
        out_list.append(out)

    return out_list


@router.get("/{org_id}", response_model=BuilderProfileOut)
def get_builder_profile(
    *,
    db: Session = Depends(get_db),
    org_id: int,
    include: Optional[str] = Query(None, description="Comma-separated includes: properties,communities"),
    current_user=Depends(get_current_user_optional),
):
    includes = _parse_include(include)
    query = db.query(BuilderModel)
    query = _apply_includes(query, includes)
    obj = query.filter(BuilderModel.org_id == org_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")

    out = BuilderProfileOut.model_validate(obj)
    _attach_social_fields(db, org_id, out, getattr(current_user, "id", None) if current_user else None)
    return out


@router.post("/", response_model=BuilderProfileOut, status_code=status.HTTP_201_CREATED)
def create_builder_profile(
    *,
    db: Session = Depends(get_db),
    payload: BuilderProfileCreate,
):
    # Ensure unique org_id
    exists = db.query(BuilderModel).filter(BuilderModel.org_id == payload.org_id).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile for this org_id already exists")

    obj = BuilderModel(**payload.model_dump(exclude_none=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderProfileOut.model_validate(obj)


@router.put("/{org_id}", response_model=BuilderProfileOut)
@router.patch("/{org_id}", response_model=BuilderProfileOut)
def update_builder_profile(
    *,
    db: Session = Depends(get_db),
    org_id: int,
    payload: BuilderProfileUpdate,
):
    obj = _get_or_404(db, org_id)

    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuilderProfileOut.model_validate(obj)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_profile(*, db: Session = Depends(get_db), org_id: int):
    obj = _get_or_404(db, org_id)
    db.delete(obj)
    db.commit()
    return None

# --------------------------- sales reps (scoped) ---------------------------

@router.get("/{org_id}/sales-reps", response_model=List[SalesRepOut])
def list_sales_reps(
    *,
    db: Session = Depends(get_db),
    org_id: int,
):
    builder_pk = _builder_id_by_org(db, org_id)
    if not builder_pk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    rows = (
        db.query(SalesRepModel)
        .filter(SalesRepModel.builder_id == builder_pk)
        .order_by(SalesRepModel.full_name.asc())
        .all()
    )
    return [SalesRepOut.model_validate(r) for r in rows]


@router.post("/{org_id}/sales-reps", response_model=SalesRepOut, status_code=status.HTTP_201_CREATED)
def create_sales_rep(
    *,
    db: Session = Depends(get_db),
    org_id: int,
    payload: SalesRepCreate,
):
    builder_pk = _builder_id_by_org(db, org_id)
    if not builder_pk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    # Force the builder_id to the resolved builder PK to prevent cross-org creation
    data = payload.model_dump(exclude_none=True)
    data["builder_id"] = builder_pk

    obj = SalesRepModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return SalesRepOut.model_validate(obj)


@router.put("/{org_id}/sales-reps/{rep_id}", response_model=SalesRepOut)
@router.patch("/{org_id}/sales-reps/{rep_id}", response_model=SalesRepOut)
def update_sales_rep(
    *,
    db: Session = Depends(get_db),
    org_id: int,
    rep_id: int,
    payload: SalesRepUpdate,
):
    builder_pk = _builder_id_by_org(db, org_id)
    if not builder_pk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    obj = db.query(SalesRepModel).filter(
        SalesRepModel.id == rep_id,
        SalesRepModel.builder_id == builder_pk
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


@router.delete("/{org_id}/sales-reps/{rep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sales_rep(
    *,
    db: Session = Depends(get_db),
    org_id: int,
    rep_id: int,
):
    builder_pk = _builder_id_by_org(db, org_id)
    if not builder_pk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Builder profile not found")
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    obj = db.query(SalesRepModel).filter(
        SalesRepModel.id == rep_id,
        SalesRepModel.builder_id == builder_pk
    ).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales rep not found for this builder")

    db.delete(obj)
    db.commit()
    return None