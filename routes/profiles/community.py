from __future__ import annotations

from typing import List, Optional, Set, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from config.db import get_db
from config.security import get_current_user_optional
from model.user import Users
from model.profiles.community_admin_profile import CommunityAdminProfile
from schema.user import UserOut

# --- SQLAlchemy models -------------------------------------------------------
try:
    from model.profiles.community import (
        Community as CommunityModel,
        CommunityAmenity as AmenityModel,
        CommunityEvent as EventModel,
        CommunityBuilder as BuilderCardModel,
        CommunityAdmin as AdminModel,
        CommunityAdminLink as AdminLinkModel,
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


def _get_or_404(db: Session, community_id: str) -> CommunityModel:
    """Get community by public string ID (e.g., CMY-xxx) or by name (case-insensitive)."""
    # First try exact match by community_id
    obj = db.query(CommunityModel).filter(CommunityModel.community_id == community_id).first()

    # If not found, try case-insensitive name lookup (handle URL slugs like "highlands")
    if not obj:
        obj = db.query(CommunityModel).filter(
            CommunityModel.name.ilike(f"%{community_id}%")
        ).first()

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


@router.get("/for-user/{user_id}", response_model=CommunityOut)
def get_community_for_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    include: Optional[str] = Query(None, description="Comma-separated includes: amenities,events,builder_cards,admins,awards,threads,phases,builders"),
):
    """
    Get the community associated with a user (via CommunityAdminProfile).
    Works with user user_id (USR-xxx) or internal user ID.
    """
    # Resolve user by user_id or internal ID
    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        # Try as integer ID for legacy support
        try:
            user = db.query(Users).filter(Users.id == int(user_id)).first()
        except ValueError:
            pass

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find community admin profile for this user
    admin_profile = db.query(CommunityAdminProfile).filter(
        CommunityAdminProfile.user_id == user.user_id
    ).first()

    if not admin_profile:
        raise HTTPException(
            status_code=404,
            detail="No community found for this user. User must be a community admin."
        )

    # Get the community with optional includes
    from model.media import Media

    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)
    community = query.filter(CommunityModel.id == admin_profile.community_id).first()

    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    # Get avatar and cover URLs from media table
    avatar_media = db.query(Media).filter(
        Media.entity_type == 'community',
        Media.entity_id == community.id,
        Media.entity_field == 'avatar'
    ).first()

    cover_media = db.query(Media).filter(
        Media.entity_type == 'community',
        Media.entity_id == community.id,
        Media.entity_field == 'cover'
    ).first()

    # Convert to dict and add media URLs
    community_dict = community.__dict__.copy()
    community_dict['avatar_url'] = avatar_media.medium_url if avatar_media else None
    # Use medium_url for cover if available, fallback to original_url
    community_dict['cover_url'] = (cover_media.medium_url or cover_media.original_url) if cover_media else None

    return CommunityOut.model_validate(community_dict)


@router.get("/public/{public_id}", response_model=CommunityOut)
def get_community_by_public_id(
    *,
    db: Session = Depends(get_db),
    public_id: str,
    include: Optional[str] = Query(None),
    current_user=Depends(get_current_user_optional),
):
    """Get community by public community_id (e.g., CMY-xxx)"""
    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)

    community = query.filter(CommunityModel.community_id == public_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    return CommunityOut.model_validate(community)


@router.get("/{community_id}", response_model=CommunityOut, response_model_by_alias=True)
def get_community(
    *,
    db: Session = Depends(get_db),
    community_id: int,
    include: Optional[str] = Query(None),
    current_user=Depends(get_current_user_optional),
):
    from model.media import Media

    includes = _parse_include(include)
    query = db.query(CommunityModel)
    query = _apply_includes(query, includes)
    obj = query.filter(CommunityModel.id == community_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Community not found")

    # Get avatar and cover URLs from media table
    avatar_media = db.query(Media).filter(
        Media.entity_type == 'community',
        Media.entity_id == community_id,
        Media.entity_field == 'avatar'
    ).first()

    cover_media = db.query(Media).filter(
        Media.entity_type == 'community',
        Media.entity_id == community_id,
        Media.entity_field == 'cover'
    ).first()

    # Convert to dict and add media URLs
    community_dict = obj.__dict__.copy()
    community_dict['avatar_url'] = avatar_media.medium_url if avatar_media else None
    # Use medium_url for cover if available, fallback to original_url
    community_dict['cover_url'] = (cover_media.medium_url or cover_media.original_url) if cover_media else None

    return CommunityOut.model_validate(community_dict)


@router.post("/", response_model=CommunityOut, status_code=status.HTTP_201_CREATED)
def create_community(
    *, db: Session = Depends(get_db), payload: CommunityCreate
):
    # Extract amenity_names before creating community
    amenity_names = payload.amenity_names if hasattr(payload, 'amenity_names') else []

    # Create community (exclude amenity_names from model_dump)
    data = payload.model_dump(exclude_none=True, exclude={'amenity_names'})
    obj = CommunityModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Create amenity records if any provided
    if amenity_names:
        for name in amenity_names:
            if name and name.strip():  # Skip empty strings
                amenity = AmenityModel(community_id=obj.id, name=name.strip())
                db.add(amenity)
        db.commit()
        db.refresh(obj)

    return CommunityOut.model_validate(obj)


@router.put("/{community_id}", response_model=CommunityOut)
@router.patch("/{community_id}", response_model=CommunityOut)
def update_community(
    *, db: Session = Depends(get_db), community_id: int, payload: CommunityUpdate
):
    obj = _get_or_404(db, community_id)

    # Extract amenity_names if provided
    amenity_names = None
    if hasattr(payload, 'amenity_names') and payload.amenity_names is not None:
        amenity_names = payload.amenity_names

    # Update community fields (exclude amenity_names)
    data = payload.model_dump(exclude_none=True, exclude={'amenity_names'})
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.add(obj)
    db.commit()

    # If amenity_names provided, replace all amenities
    if amenity_names is not None:
        # Delete existing amenities
        db.query(AmenityModel).filter(AmenityModel.community_id == community_id).delete()

        # Create new amenities
        for name in amenity_names:
            if name and name.strip():
                amenity = AmenityModel(community_id=obj.id, name=name.strip())
                db.add(amenity)
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
def list_builder_cards(*, db: Session = Depends(get_db), community_id: str):
    """List all builder cards for a community. Use string community_id (e.g., CMY-xxx)."""
    from model.profiles.builder import BuilderProfile, builder_communities
    from model.profiles.community import CommunityBuilder

    # Get community to retrieve numeric ID for builder_communities join
    community = _get_or_404(db, community_id)

    # Query all builders associated with this community via builder_communities
    # Include both active and inactive builders so users know who is not yet on the platform
    # Note: builder_communities uses numeric community ID (community.id)
    builders = (
        db.query(BuilderProfile)
        .join(builder_communities, BuilderProfile.id == builder_communities.c.builder_id)
        .filter(builder_communities.c.community_id == community.id)
        .all()
    )

    # Transform BuilderProfile objects to CommunityBuilderCardOut format
    result = []
    for builder in builders:
        # Map builder profile fields to builder card fields
        subtitle = None
        if builder.title:
            subtitle = builder.title
        elif builder.specialties and isinstance(builder.specialties, list) and len(builder.specialties) > 0:
            subtitle = builder.specialties[0]

        # For inactive builders, the card will be shown but clicking won't navigate to profile
        # The iOS app should check is_verified to determine if navigation is enabled
        # is_verified is True only if builder is both verified AND active on platform
        result.append(CommunityBuilderCardOut(
            id=builder.id,
            community_id=community.community_id,  # Public CMY-XXX ID
            name=builder.name,
            icon=None,  # BuilderProfile doesn't have icon field - could add later
            subtitle=subtitle,
            followers=0,  # BuilderProfile doesn't have follower_count - could add later
            is_verified=builder.verified == 1 and builder.is_active  # Only verified if both verified AND active
        ))

    # Fallback: If no BuilderProfile entities found, try legacy community_builders table
    if not result:
        legacy_cards = (
            db.query(CommunityBuilder)
            .filter(CommunityBuilder.community_id == community.community_id)
            .all()
        )

        for card in legacy_cards:
            result.append(CommunityBuilderCardOut(
                id=card.id,
                community_id=community.community_id,
                name=card.name,
                icon=card.icon,
                subtitle=card.subtitle,
                followers=card.followers or 0,
                is_verified=card.is_verified or False
            ))

    return result


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

@router.get("/{community_id}/admins")
def list_admins(*, db: Session = Depends(get_db), community_id: str):
    """Get all users with admin roles for this community via CommunityAdminLink."""
    community = _get_or_404(db, community_id)

    # Query admin links and join with users
    admin_links = (
        db.query(AdminLinkModel)
        .filter(AdminLinkModel.community_id == community.id)
        .options(selectinload(AdminLinkModel.user))
        .all()
    )

    # Extract and return users as simple dicts
    users = []
    for link in admin_links:
        if link.user:
            users.append({
                "id": link.user.user_id,
                "email": link.user.email,
                "first_name": link.user.first_name,
                "last_name": link.user.last_name,
                "role": link.user.role,
            })

    return users


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
def list_topics(*, db: Session = Depends(get_db), community_id: str):
    """List all topics/threads for a community. Use string community_id (e.g., CMY-xxx)."""
    _get_or_404(db, community_id)
    rows = db.query(TopicModel).filter(TopicModel.community_id == community_id).all()
    return [CommunityTopicOut.model_validate(r) for r in rows]


@router.post("/{community_id}/topics", response_model=CommunityTopicOut, status_code=status.HTTP_201_CREATED)
def add_topic(*, db: Session = Depends(get_db), community_id: str, payload: CommunityTopicCreate):
    """Create a new topic/thread for a community. Use string community_id (e.g., CMY-xxx)."""
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