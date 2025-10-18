from __future__ import annotations

from typing import List, Optional, Set, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from config.db import get_db
from config.security import get_current_user_optional

# --- SQLAlchemy models -------------------------------------------------------
try:
    from model.profiles.community import (
        Community as CommunityModel,
        CommunityAmenity as AmenityModel,
        CommunityEvent as EventModel,
        CommunityBuilder as BuilderCardModel,
        CommunityAdmin as AdminModel,
        CommunityAward as AwardModel,
        CommunityTopic as TopicModel,
        CommunityPhase as PhaseModel,
    )
except Exception as e:  # pragma: no cover
    raise ImportError("Community-related models are missing: model/profiles/community.py") from e

# --- Pydantic schemas --------------------------------------------------------
try:
    from schema.community import (
        CommunityOut,
        CommunityCreate,
        CommunityUpdate,
        CommunityAmenityOut,
        CommunityAmenityCreate,
        CommunityAmenityUpdate,
        CommunityEventOut,
        CommunityEventCreate,
        CommunityEventUpdate,
        CommunityBuilderCardOut,
        CommunityBuilderCardCreate,
        CommunityBuilderCardUpdate,
        CommunityAdminOut,
        CommunityAdminCreate,
        CommunityAdminUpdate,
        CommunityAwardOut,
        CommunityAwardCreate,
        CommunityAwardUpdate,
        CommunityTopicOut,
        CommunityTopicCreate,
        CommunityTopicUpdate,
        CommunityPhaseOut,
        CommunityPhaseCreate,
        CommunityPhaseUpdate,
    )
except Exception as e:  # pragma: no cover
    raise ImportError("Community Pydantic schemas are missing: schema/community.py") from e


router = APIRouter()  # app mounts with /v1


# -------------------------------- helpers -----------------------------------

def _parse_include(include: Optional[str]) -> Set[str]:
    if not include:
        return set()
    return {p.strip().lower() for p in include.split(",") if p.strip()}


def _get_or_404(db: Session, community_id: int) -> CommunityModel:
    obj = db.query(CommunityModel).filter(CommunityModel.id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Community not found")
    return obj


def _apply_includes(q, include: Set[str]):
    if "amenities" in include:
        q = q.options(selectinload(CommunityModel.amenities))
    if "events" in include:
        q = q.options(selectinload(CommunityModel.events))
    if "builder_cards" in include:
        q = q.options(selectinload(CommunityModel.builder_cards))
    if "admins" in include:
        q = q.options(selectinload(CommunityModel.admins))
    if "awards" in include:
        q = q.options(selectinload(CommunityModel.awards))
    if "threads" in include:
        q = q.options(selectinload(CommunityModel.threads))
    if "phases" in include:
        q = q.options(selectinload(CommunityModel.phases))
    if "builders" in include and hasattr(CommunityModel, "builders"):
        q = q.options(selectinload(CommunityModel.builders))
    return q


# --------------------------------- CRUD -------------------------------------

@router.get("/", response_model=List[CommunityOut])
def list_communities(
    *,
    db: Session = Depends(get_db),
    include: Optional[str] = Query(None, description="Comma-separated includes: amenities,events,builder_cards,admins,awards,threads,phases,builders"),
    q: Optional[str] = Query(None, description="Search across name/about/city"),
    city: Optional[str] = Query(None, description="Filter by city"),
    postal_code: Optional[str] = Query(None, description="Filter by postal code"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user_optional),
):
    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)

    if q:
        ors = []
        for col in ("name", "about", "city"):
            if hasattr(CommunityModel, col):
                ors.append(getattr(CommunityModel, col).ilike(f"%{q}%"))
        if ors:
            query = query.filter(or_(*ors))

    if city and hasattr(CommunityModel, "city"):
        query = query.filter(CommunityModel.city.ilike(f"%{city}%"))
    if postal_code and hasattr(CommunityModel, "postal_code"):
        query = query.filter(CommunityModel.postal_code.ilike(f"%{postal_code}%"))

    rows: Sequence[CommunityModel] = query.offset(offset).limit(limit).all()
    return [CommunityOut.model_validate(r) for r in rows]


@router.get("/{community_id}", response_model=CommunityOut)
def get_community(
    *,
    db: Session = Depends(get_db),
    community_id: int,
    include: Optional[str] = Query(None),
    current_user=Depends(get_current_user_optional),
):
    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)
    obj = query.filter(CommunityModel.id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Community not found")
    return CommunityOut.model_validate(obj)


@router.post("/", response_model=CommunityOut, status_code=status.HTTP_201_CREATED)
def create_community(
    *, db: Session = Depends(get_db), payload: CommunityCreate
):
    obj = CommunityModel(**payload.model_dump(exclude_none=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityOut.model_validate(obj)


@router.put("/{community_id}", response_model=CommunityOut)
@router.patch("/{community_id}", response_model=CommunityOut)
def update_community(
    *, db: Session = Depends(get_db), community_id: int, payload: CommunityUpdate
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


# ------------------------------ Nested: Amenities ---------------------------

@router.get("/{community_id}/amenities", response_model=List[CommunityAmenityOut])
def list_amenities(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(AmenityModel).filter(AmenityModel.community_id == community_id).all()
    return [CommunityAmenityOut.model_validate(r) for r in rows]


@router.post("/{community_id}/amenities", response_model=CommunityAmenityOut, status_code=status.HTTP_201_CREATED)
def add_amenity(*, db: Session = Depends(get_db), community_id: int, payload: CommunityAmenityCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = AmenityModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityAmenityOut.model_validate(obj)


@router.patch("/{community_id}/amenities/{amenity_id}", response_model=CommunityAmenityOut)
def update_amenity(*, db: Session = Depends(get_db), community_id: int, amenity_id: int, payload: CommunityAmenityUpdate):
    _get_or_404(db, community_id)
    obj = db.query(AmenityModel).filter(AmenityModel.id == amenity_id, AmenityModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Amenity not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityAmenityOut.model_validate(obj)


@router.delete("/{community_id}/amenities/{amenity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_amenity(*, db: Session = Depends(get_db), community_id: int, amenity_id: int):
    _get_or_404(db, community_id)
    obj = db.query(AmenityModel).filter(AmenityModel.id == amenity_id, AmenityModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Amenity not found")
    db.delete(obj)
    db.commit()
    return None


# ------------------------------ Nested: Events ------------------------------

@router.get("/{community_id}/events", response_model=List[CommunityEventOut])
def list_events(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(EventModel).filter(EventModel.community_id == community_id).all()
    return [CommunityEventOut.model_validate(r) for r in rows]


@router.post("/{community_id}/events", response_model=CommunityEventOut, status_code=status.HTTP_201_CREATED)
def add_event(*, db: Session = Depends(get_db), community_id: int, payload: CommunityEventCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = EventModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityEventOut.model_validate(obj)


@router.patch("/{community_id}/events/{event_id}", response_model=CommunityEventOut)
def update_event(*, db: Session = Depends(get_db), community_id: int, event_id: int, payload: CommunityEventUpdate):
    _get_or_404(db, community_id)
    obj = db.query(EventModel).filter(EventModel.id == event_id, EventModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityEventOut.model_validate(obj)


@router.delete("/{community_id}/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(*, db: Session = Depends(get_db), community_id: int, event_id: int):
    _get_or_404(db, community_id)
    obj = db.query(EventModel).filter(EventModel.id == event_id, EventModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(obj)
    db.commit()
    return None


# --------------------------- Nested: Builder Cards --------------------------

@router.get("/{community_id}/builder-cards", response_model=List[CommunityBuilderCardOut])
def list_builder_cards(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(BuilderCardModel).filter(BuilderCardModel.community_id == community_id).all()
    return [CommunityBuilderCardOut.model_validate(r) for r in rows]


@router.post("/{community_id}/builder-cards", response_model=CommunityBuilderCardOut, status_code=status.HTTP_201_CREATED)
def add_builder_card(*, db: Session = Depends(get_db), community_id: int, payload: CommunityBuilderCardCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = BuilderCardModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityBuilderCardOut.model_validate(obj)


@router.patch("/{community_id}/builder-cards/{card_id}", response_model=CommunityBuilderCardOut)
def update_builder_card(*, db: Session = Depends(get_db), community_id: int, card_id: int, payload: CommunityBuilderCardUpdate):
    _get_or_404(db, community_id)
    obj = db.query(BuilderCardModel).filter(BuilderCardModel.id == card_id, BuilderCardModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Builder card not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityBuilderCardOut.model_validate(obj)


@router.delete("/{community_id}/builder-cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_card(*, db: Session = Depends(get_db), community_id: int, card_id: int):
    _get_or_404(db, community_id)
    obj = db.query(BuilderCardModel).filter(BuilderCardModel.id == card_id, BuilderCardModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Builder card not found")
    db.delete(obj)
    db.commit()
    return None


# ------------------------------- Nested: Admins -----------------------------

@router.get("/{community_id}/admins", response_model=List[CommunityAdminOut])
def list_admins(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(AdminModel).filter(AdminModel.community_id == community_id).all()
    return [CommunityAdminOut.model_validate(r) for r in rows]


@router.post("/{community_id}/admins", response_model=CommunityAdminOut, status_code=status.HTTP_201_CREATED)
def add_admin(*, db: Session = Depends(get_db), community_id: int, payload: CommunityAdminCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = AdminModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityAdminOut.model_validate(obj)


@router.patch("/{community_id}/admins/{admin_id}", response_model=CommunityAdminOut)
def update_admin(*, db: Session = Depends(get_db), community_id: int, admin_id: int, payload: CommunityAdminUpdate):
    _get_or_404(db, community_id)
    obj = db.query(AdminModel).filter(AdminModel.id == admin_id, AdminModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Admin not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityAdminOut.model_validate(obj)


@router.delete("/{community_id}/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin(*, db: Session = Depends(get_db), community_id: int, admin_id: int):
    _get_or_404(db, community_id)
    obj = db.query(AdminModel).filter(AdminModel.id == admin_id, AdminModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Admin not found")
    db.delete(obj)
    db.commit()
    return None


# ------------------------------- Nested: Awards -----------------------------

@router.get("/{community_id}/awards", response_model=List[CommunityAwardOut])
def list_awards(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(AwardModel).filter(AwardModel.community_id == community_id).all()
    return [CommunityAwardOut.model_validate(r) for r in rows]


@router.post("/{community_id}/awards", response_model=CommunityAwardOut, status_code=status.HTTP_201_CREATED)
def add_award(*, db: Session = Depends(get_db), community_id: int, payload: CommunityAwardCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = AwardModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityAwardOut.model_validate(obj)


@router.patch("/{community_id}/awards/{award_id}", response_model=CommunityAwardOut)
def update_award(*, db: Session = Depends(get_db), community_id: int, award_id: int, payload: CommunityAwardUpdate):
    _get_or_404(db, community_id)
    obj = db.query(AwardModel).filter(AwardModel.id == award_id, AwardModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Award not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityAwardOut.model_validate(obj)


@router.delete("/{community_id}/awards/{award_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_award(*, db: Session = Depends(get_db), community_id: int, award_id: int):
    _get_or_404(db, community_id)
    obj = db.query(AwardModel).filter(AwardModel.id == award_id, AwardModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Award not found")
    db.delete(obj)
    db.commit()
    return None


# ------------------------------- Nested: Topics -----------------------------

@router.get("/{community_id}/topics", response_model=List[CommunityTopicOut])
def list_topics(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(TopicModel).filter(TopicModel.community_id == community_id).all()
    return [CommunityTopicOut.model_validate(r) for r in rows]


@router.post("/{community_id}/topics", response_model=CommunityTopicOut, status_code=status.HTTP_201_CREATED)
def add_topic(*, db: Session = Depends(get_db), community_id: int, payload: CommunityTopicCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = TopicModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityTopicOut.model_validate(obj)


@router.patch("/{community_id}/topics/{topic_id}", response_model=CommunityTopicOut)
def update_topic(*, db: Session = Depends(get_db), community_id: int, topic_id: int, payload: CommunityTopicUpdate):
    _get_or_404(db, community_id)
    obj = db.query(TopicModel).filter(TopicModel.id == topic_id, TopicModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Topic not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityTopicOut.model_validate(obj)


@router.delete("/{community_id}/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(*, db: Session = Depends(get_db), community_id: int, topic_id: int):
    _get_or_404(db, community_id)
    obj = db.query(TopicModel).filter(TopicModel.id == topic_id, TopicModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Topic not found")
    db.delete(obj)
    db.commit()
    return None


# -------------------------------- Nested: Phases ----------------------------

@router.get("/{community_id}/phases", response_model=List[CommunityPhaseOut])
def list_phases(*, db: Session = Depends(get_db), community_id: int):
    _get_or_404(db, community_id)
    rows = db.query(PhaseModel).filter(PhaseModel.community_id == community_id).all()
    return [CommunityPhaseOut.model_validate(r) for r in rows]


@router.post("/{community_id}/phases", response_model=CommunityPhaseOut, status_code=status.HTTP_201_CREATED)
def add_phase(*, db: Session = Depends(get_db), community_id: int, payload: CommunityPhaseCreate):
    _get_or_404(db, community_id)
    data = payload.model_dump(exclude_none=True)
    data["community_id"] = community_id
    obj = PhaseModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityPhaseOut.model_validate(obj)


@router.patch("/{community_id}/phases/{phase_id}", response_model=CommunityPhaseOut)
def update_phase(*, db: Session = Depends(get_db), community_id: int, phase_id: int, payload: CommunityPhaseUpdate):
    _get_or_404(db, community_id)
    obj = db.query(PhaseModel).filter(PhaseModel.id == phase_id, PhaseModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Phase not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return CommunityPhaseOut.model_validate(obj)


@router.delete("/{community_id}/phases/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phase(*, db: Session = Depends(get_db), community_id: int, phase_id: int):
    _get_or_404(db, community_id)
    obj = db.query(PhaseModel).filter(PhaseModel.id == phase_id, PhaseModel.community_id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Phase not found")
    db.delete(obj)
    db.commit()
    return None