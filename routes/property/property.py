from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from config.db import get_db
from config.security import get_current_user

# Schemas (Pydantic)
from schema.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyOut,
    PropertyRelationsOut,
    LinkedBuilderOut,
    LinkedCommunityOut,
)

# Models (SQLAlchemy)
from model.property.property import Property  # correct import path
from model.user import Users

# Optional models (only used if present in your codebase)
try:  # favorites/saves are optional; guarded to avoid import errors if not yet created
    from model.property import FavoriteProperty  # type: ignore
except Exception:  # pragma: no cover
    FavoriteProperty = None  # type: ignore

router = APIRouter(prefix="/v1/properties", tags=["Properties"])


# ----------------------------------------------------------------------------
# Create
# ----------------------------------------------------------------------------
@router.post("/", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """Create a new property listing owned by the current user."""
    prop = Property(**payload.model_dump(exclude_none=True), owner_id=current_user.id)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


# ----------------------------------------------------------------------------
# Read (list with filters)
# ----------------------------------------------------------------------------
@router.get("/", response_model=List[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(20, le=100),
    # Common filters
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_beds: Optional[int] = None,
    min_baths: Optional[float] = None,
    builder_id: Optional[int] = None,
    community_id: Optional[int] = None,
    has_pool: Optional[bool] = None,
    sort: str = Query("listed_at_desc", pattern=r"^(listed_at|price|beds)_(asc|desc)$"),
):
    """List properties with basic search and filters.

    Sort options: `listed_at_desc` (default), `listed_at_asc`, `price_asc`, `price_desc`,
    `beds_asc`, `beds_desc`.
    """
    q = db.query(Property)

    if city:
        q = q.filter(Property.city.ilike(f"%{city}%"))
    if state:
        q = q.filter(Property.state.ilike(f"%{state}%"))
    if min_price is not None:
        q = q.filter(Property.price >= min_price)
    if max_price is not None:
        q = q.filter(Property.price <= max_price)
    if min_beds is not None:
        q = q.filter(Property.bedrooms >= min_beds)
    if min_baths is not None:
        q = q.filter(Property.bathrooms >= min_baths)
    if builder_id is not None:
        q = q.filter(Property.builder_id == builder_id)
    if community_id is not None:
        q = q.filter(Property.community_id == community_id)
    if has_pool is not None:
        q = q.filter(Property.has_pool == has_pool)

    field, direction = sort.split("_")
    order_col = {
        "listed_at": getattr(Property, "listed_at", getattr(Property, "created_at")),
        "price": Property.price,
        "beds": Property.bedrooms,
    }[field]
    if direction == "desc":
        order_col = order_col.desc()

    items = q.order_by(order_col).offset(skip).limit(limit).all()
    return items


# ----------------------------------------------------------------------------
# Read (by id)
# ----------------------------------------------------------------------------
@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


# ----------------------------------------------------------------------------
# Relations (community & builders)
# ----------------------------------------------------------------------------
@router.get("/{property_id}/relations", response_model=PropertyRelationsOut)
def get_property_relations(property_id: int, db: Session = Depends(get_db)):
    prop = (
        db.query(Property)
        .options(
            selectinload(Property.primary_builder),
            selectinload(Property.builders),
            selectinload(Property.community),
        )
        .filter(Property.id == property_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    primary = LinkedBuilderOut.from_orm(prop.primary_builder) if getattr(prop, "primary_builder", None) else None
    builders = [LinkedBuilderOut.from_orm(b) for b in (prop.builders or [])]
    community = (
        LinkedCommunityOut.from_orm(prop.community) if getattr(prop, "community", None) else None
    )

    return PropertyRelationsOut(
        property_id=prop.id,
        primary_builder=primary,
        builders=builders,
        community=community,
    )


# ----------------------------------------------------------------------------
# Update (owner only)
# ----------------------------------------------------------------------------
@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this property")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(prop, k, v)

    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


# ----------------------------------------------------------------------------
# Delete (owner only)
# ----------------------------------------------------------------------------
@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this property")

    db.delete(prop)
    db.commit()
    return


# ----------------------------------------------------------------------------
# Favorite / Save toggle (optional; only registers if FavoriteProperty model exists)
# ----------------------------------------------------------------------------
if FavoriteProperty is not None:  # type: ignore

    @router.post("/{property_id}/favorite", status_code=status.HTTP_200_OK)
    def toggle_favorite_property(
        property_id: int,
        db: Session = Depends(get_db),
        current_user: Users = Depends(get_current_user),
    ):
        prop = db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        fav = (
            db.query(FavoriteProperty)  # type: ignore
            .filter(
                FavoriteProperty.property_id == property_id,  # type: ignore
                FavoriteProperty.user_id == current_user.id,  # type: ignore
            )
            .first()
        )
        if fav:
            db.delete(fav)
            db.commit()
            return {"message": "Removed from favorites"}
        else:
            fav = FavoriteProperty(property_id=property_id, user_id=current_user.id)  # type: ignore
            db.add(fav)
            db.commit()
            return {"message": "Added to favorites"}

    @router.get("/me/favorites", response_model=List[PropertyOut])
    def list_my_favorite_properties(
        db: Session = Depends(get_db),
        current_user: Users = Depends(get_current_user),
    ):
        # Join FavoriteProperty -> Property
        subq = (
            db.query(Property)
            .join(FavoriteProperty, FavoriteProperty.property_id == Property.id)  # type: ignore
            .filter(FavoriteProperty.user_id == current_user.id)  # type: ignore
        )
        return subq.order_by(getattr(Property, "listed_at", Property.created_at).desc()).all()