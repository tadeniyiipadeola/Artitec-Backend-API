

"""Community routes (v1)

Exposes CRUD and list/search endpoints for communities, plus a helper route
for listing active builders in a given community.

- Path prefix: /v1/communities
- Response schemas: Pydantic v2 (schema/community.py)
- DB: SQLAlchemy session via core.db.get_db
- Includes: optional eager-load of builders via `include=builders`
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

# --- Project imports (adjust if your paths differ) ---------------------------
try:
    from core.db import get_db
except Exception as e:  # pragma: no cover
    raise ImportError("core.db.get_db is required for DB session dependency") from e

# Optional auth (graceful fallback to None)
try:
    from core.security import get_current_user_optional  # returns User | None
except Exception:  # pragma: no cover
    def get_current_user_optional():  # type: ignore
        return None

try:
    from model.profiles.community import Community as CommunityModel  # SQLAlchemy model
except Exception as e:  # pragma: no cover
    raise ImportError("model.profiles.community.Community model not found") from e

try:
    from model.profiles.builder import Builder as BuilderModel  # for /{id}/builders endpoint
except Exception as e:  # pragma: no cover
    raise ImportError("model.profiles.builder.Builder model not found (needed for listing builders)") from e

try:
    from schema.community import (
        CommunityOut,
        CommunityCreate,
        CommunityUpdate,
    )
except Exception as e:  # pragma: no cover
    raise ImportError("schema.community.* Pydantic schemas are required") from e

try:
    from schema.builder import BuilderProfileOut
except Exception as e:  # pragma: no cover
    raise ImportError("schema.builder.BuilderProfileOut is required for /{id}/builders") from e


router = APIRouter(prefix="/v1/communities", tags=["Communities"])


# ------------------------------ helpers -------------------------------------

def _parse_include(include: Optional[str]) -> Set[str]:
    if not include:
        return set()
    return {part.strip().lower() for part in include.split(",") if part.strip()}


def _get_or_404(db: Session, community_id: int) -> CommunityModel:
    obj = db.query(CommunityModel).filter(CommunityModel.id == community_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return obj


def _apply_includes(query, include: Set[str]):
    if "builders" in include and hasattr(CommunityModel, "builders"):
        query = query.options(selectinload(CommunityModel.builders))
    return query


# ------------------------------- routes -------------------------------------

@router.get("/", response_model=List[CommunityOut])
def list_communities(
    *,
    db: Session = Depends(get_db),
    include: Optional[str] = Query(None, description="Comma-separated includes: builders"),
    q: Optional[str] = Query(None, description="Free-text search across name/description/notes"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user_optional),  # reserved for future auth-aware fields
):
    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)

    # Text search
    if q:
        ors = []
        for col_name in ("name", "description", "notes"):
            if hasattr(CommunityModel, col_name):
                ors.append(getattr(CommunityModel, col_name).ilike(f"%{q}%"))
        if ors:
            query = query.filter(or_(*ors))

    if city and hasattr(CommunityModel, "city"):
        query = query.filter(CommunityModel.city.ilike(f"%{city}%"))
    if state and hasattr(CommunityModel, "state"):
        query = query.filter(CommunityModel.state.ilike(f"%{state}%"))

    rows: Sequence[CommunityModel] = query.offset(offset).limit(limit).all()
    return [CommunityOut.model_validate(r) for r in rows]


@router.get("/{community_id}", response_model=CommunityOut)
def get_community(
    *,
    db: Session = Depends(get_db),
    community_id: int,
    include: Optional[str] = Query(None, description="Comma-separated includes: builders"),
    current_user=Depends(get_current_user_optional),
):
    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)

    obj = query.filter(CommunityModel.id == community_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")

    return CommunityOut.model_validate(obj)


@router.post("/", response_model=CommunityOut, status_code=status.HTTP_201_CREATED)
def create_community(
    *,
    db: Session = Depends(get_db),
    payload: CommunityCreate,
):
    obj = CommunityModel(**payload.model_dump(exclude_none=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityOut.model_validate(obj)


@router.put("/{community_id}", response_model=CommunityOut)
@router.patch("/{community_id}", response_model=CommunityOut)
def update_community(
    *,
    db: Session = Depends(get_db),
    community_id: int,
    payload: CommunityUpdate,
):
    obj = _get_or_404(db, community_id)

    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityOut.model_validate(obj)


@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_community(*, db: Session = Depends(get_db), community_id: int):
    obj = _get_or_404(db, community_id)
    db.delete(obj)
    db.commit()
    return None


# --- Helper routes -----------------------------------------------------------

@router.get("/{community_id}/builders", response_model=List[BuilderProfileOut])
def list_community_builders(
    *,
    db: Session = Depends(get_db),
    community_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # Ensure community exists (and eager load builders)
    comm = (
        db.query(CommunityModel)
        .options(selectinload(CommunityModel.builders))
        .filter(CommunityModel.id == community_id)
        .first()
    )
    if not comm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")

    # slice builders list manually for now (could be a dedicated query if very large)
    builders = comm.builders[offset : offset + limit]
    return [BuilderProfileOut.model_validate(b) for b in builders]