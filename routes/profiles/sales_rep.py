

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# DB/session
try:
    # common pattern in this codebase
    from config.db import get_db  # type: ignore
except Exception:
    # fallback if your project uses src.db
    from src.db import get_db  # type: ignore

# Models
try:
    from model.profiles.sales_rep import SalesRep as SalesRepModel  # separate file model
except Exception as e:  # pragma: no cover
    SalesRepModel = None  # type: ignore

# Schemas (we previously added SalesRep schemas alongside builder schemas)
try:
    from schema.builder import SalesRepCreate, SalesRepUpdate, SalesRepOut  # type: ignore
except Exception:
    # fallback if you placed them in a dedicated module
    from schema.sales_rep import SalesRepCreate, SalesRepUpdate, SalesRepOut  # type: ignore


router = APIRouter(prefix="/v1/profiles/sales-reps", tags=["Sales Representative Profiles"])


# ---------------------------- helpers ----------------------------
def _get_rep_or_404(db: Session, rep_id: int):
    obj = db.query(SalesRepModel).filter(SalesRepModel.id == rep_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales rep not found")
    return obj


# ----------------------------- routes -----------------------------
@router.get("/", response_model=List[SalesRepOut])
def list_sales_reps(
    *,
    db: Session = Depends(get_db),
    builder_id: Optional[int] = Query(None, description="Filter by builder_id"),
    community_id: Optional[int] = Query(None, description="Filter by community_id"),
    q: Optional[str] = Query(None, description="Case-insensitive search in full_name/title/email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    query = db.query(SalesRepModel)
    if builder_id is not None:
        query = query.filter(SalesRepModel.builder_id == builder_id)
    if community_id is not None:
        query = query.filter(SalesRepModel.community_id == community_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (SalesRepModel.full_name.ilike(like))
            | (SalesRepModel.title.ilike(like))
            | (SalesRepModel.email.ilike(like))
        )
    rows = query.order_by(SalesRepModel.full_name.asc()).offset(offset).limit(limit).all()
    return rows


@router.post("/", response_model=SalesRepOut, status_code=status.HTTP_201_CREATED)
def create_sales_rep(
    *,
    db: Session = Depends(get_db),
    payload: SalesRepCreate,
):
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    data = payload.model_dump(exclude_none=True)
    obj = SalesRepModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{rep_id}", response_model=SalesRepOut)
def get_sales_rep(
    *,
    db: Session = Depends(get_db),
    rep_id: int,
):
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")
    return _get_rep_or_404(db, rep_id)


@router.patch("/{rep_id}", response_model=SalesRepOut)
@router.put("/{rep_id}", response_model=SalesRepOut)
def update_sales_rep(
    *,
    db: Session = Depends(get_db),
    rep_id: int,
    payload: SalesRepUpdate,
):
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")

    obj = _get_rep_or_404(db, rep_id)
    data = payload.model_dump(exclude_none=True)
    # never allow id changes
    data.pop("id", None)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{rep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sales_rep(
    *,
    db: Session = Depends(get_db),
    rep_id: int,
):
    if SalesRepModel is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SalesRep model not available")
    obj = _get_rep_or_404(db, rep_id)
    db.delete(obj)
    db.commit()
    return None