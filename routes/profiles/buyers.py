# routes/profiles/buyers.py
from __future__ import annotations
from typing import List
import base64
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.db import get_db
from model.profiles.buyer import BuyerProfile, BuyerTour, BuyerDocument
from model.user import Users
from schema.buyers import (
    BuyerProfileIn, BuyerProfileOut,
    BuyerTourIn as TourIn, BuyerTourOut as TourOut,
    BuyerDocumentIn as DocumentIn, BuyerDocumentOut as DocumentOut,
)

router = APIRouter() 

# ---------- Helpers ----------

def _resolve_user_id(db: Session, user_key: str | int) -> str | int:
    """
    Accept either an internal numeric users.id or a public_id string.
    Returns the internal integer users.id or raises 404 if not found.
    """
    # If already an int, pass through
    if isinstance(user_key, int):
        return user_key
    # Numeric string? allow it
    try:
        return int(user_key)
    except Exception:
        pass
    # Otherwise, treat as public_id
    user = db.query(Users).filter(Users.public_id == str(user_key)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return int(user.id)

def _ensure_user(db: Session, user_key: str | int) -> Users:
    uid = _resolve_user_id(db, user_key)
    user = db.query(Users).filter(Users.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# Resolve buyer_id (BuyerProfile.id) from a given internal users.id
def _resolve_buyer_id(db: Session, internal_user_id: int) -> int:
    """
    Resolve buyer profile ID from internal user ID (integer).
    Args:
        db: Database session
        internal_user_id: users.id (INTEGER, not string public_id)
    Returns:
        BuyerProfile.id (integer)
    """
    print(f"🔍 _resolve_buyer_id: Looking for user_id={internal_user_id} (type={type(internal_user_id)})")
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == internal_user_id).first()
    if not prof:
        print(f"❌ _resolve_buyer_id: No buyer profile found for user_id={internal_user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")
    print(f"✅ _resolve_buyer_id: Found buyer profile id={prof.id}")
    return int(prof.id)

def _build_buyer_profile_out(profile: BuyerProfile, user: Users) -> dict:
    """
    Build a BuyerProfileOut response by combining BuyerProfile data with User data.
    Returns a dict that FastAPI will serialize with the response_model.
    """
    print(f"🏗️ _build_buyer_profile_out: profile.display_name = {profile.display_name}")
    print(f"🏗️ _build_buyer_profile_out: profile.first_name = {profile.first_name}, profile.last_name = {profile.last_name}")
    print(f"🏗️ _build_buyer_profile_out: user.first_name = {user.first_name}, user.last_name = {user.last_name}")

    return {
        # Primary fields
        "id": profile.id,
        "user_id": user.public_id,

        # Identity / display
        "display_name": profile.display_name,
        "first_name": profile.first_name or user.first_name,
        "last_name": profile.last_name or user.last_name,
        "profile_image": profile.profile_image,
        "bio": profile.bio,
        "location": profile.location,
        "website_url": profile.website_url,

        # Contact - Canonical fields
        "email": profile.email or user.email,
        "phone": profile.phone,
        "phone_e164": user.phone_e164,

        # Contact - Legacy fields
        "contact_email": profile.contact_email,
        "contact_phone": profile.contact_phone,
        "contact_preferred": profile.contact_preferred,

        # Address
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "zip_code": profile.zip_code,

        # Core attributes
        "sex": profile.sex,
        "timeline": profile.timeline,

        # Financing snapshot
        "financing_status": profile.financing_status,
        "loan_program": profile.loan_program,
        "household_income_usd": profile.household_income_usd,
        "budget_min_usd": profile.budget_min_usd,
        "budget_max_usd": profile.budget_max_usd,
        "down_payment_percent": profile.down_payment_percent,
        "lender_name": profile.lender_name,
        "agent_name": profile.agent_name,

        # Flexible metadata
        "extra": profile.extra,

        # Timestamps
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }

# ---------- Routes: Buyer Profile ----------

@router.get("/{user_id}", response_model=BuyerProfileOut)
def get_buyer_profile(user_id: str, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")
    return _build_buyer_profile_out(prof, user)

@router.post("/{user_id}", response_model=BuyerProfileOut, status_code=status.HTTP_201_CREATED)
def create_buyer_profile(user_id: str, payload: BuyerProfileIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    existing = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Buyer profile already exists")

    # Smart defaults: use payload values, fall back to user data where applicable
    prof = BuyerProfile(
        user_id=uid,

        # Identity / display
        display_name=payload.display_name or f"{payload.first_name or user.first_name} {payload.last_name or user.last_name}".strip(),
        first_name=payload.first_name or user.first_name,
        last_name=payload.last_name or user.last_name,
        profile_image=payload.profile_image,
        bio=payload.bio,
        location=payload.location,
        website_url=payload.website_url,

        # Contact - Canonical fields (prioritize payload, fallback to user or legacy fields)
        email=payload.email or payload.contact_email or user.email,
        phone=payload.phone or payload.contact_phone or user.phone_e164,

        # Contact - Legacy fields (for backward compatibility)
        contact_email=payload.contact_email or payload.email or user.email,
        contact_phone=payload.contact_phone or payload.phone or user.phone_e164,
        contact_preferred=(payload.contact_preferred or "email"),

        # Address
        address=payload.address,
        city=payload.city,
        state=payload.state,
        zip_code=payload.zip_code,

        # Core attributes
        sex=payload.sex,
        timeline=(payload.timeline or "exploring"),

        # Financing snapshot
        financing_status=(payload.financing_status or "unknown"),
        loan_program=payload.loan_program,
        household_income_usd=payload.household_income_usd,
        budget_min_usd=payload.budget_min_usd,
        budget_max_usd=payload.budget_max_usd,
        down_payment_percent=payload.down_payment_percent,
        lender_name=payload.lender_name,
        agent_name=payload.agent_name,

        # Flexible metadata
        extra=payload.extra,
    )
    db.add(prof)

    # Mark onboarding as completed for this user
    user.onboarding_completed = True

    db.commit()
    db.refresh(prof)
    return _build_buyer_profile_out(prof, user)

@router.patch("/{user_id}", response_model=BuyerProfileOut)
def update_buyer_profile(user_id: str, payload: BuyerProfileIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")

    data = payload.model_dump(exclude_unset=True)
    print(f"🔍 PATCH /buyers/{user_id}: Received data: {data}")
    print(f"🔍 Before update - display_name: {prof.display_name}")

    for field, value in data.items():
        print(f"  Setting {field} = {value}")
        setattr(prof, field, value)

    print(f"🔍 After setattr - display_name: {prof.display_name}")

    # Mark onboarding as completed for this user (in case it wasn't set during creation)
    user.onboarding_completed = True

    db.add(prof)
    db.commit()
    db.refresh(prof)

    print(f"🔍 After commit/refresh - display_name: {prof.display_name}")

    return _build_buyer_profile_out(prof, user)

# ---------- Routes: Avatar Upload ----------

class AvatarUploadRequest(BaseModel):
    image_base64: str
    mime_type: str

class AvatarUploadResponse(BaseModel):
    profile_image: str

@router.post("/{user_id}/avatar", response_model=AvatarUploadResponse)
def upload_avatar(user_id: str, payload: AvatarUploadRequest, db: Session = Depends(get_db)):
    """
    Upload profile avatar image.
    TODO: Configure storage backend (S3, Cloudflare R2, local filesystem, etc.)
    """
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")

    try:
        # Decode base64 image
        image_data = base64.b64decode(payload.image_base64)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid base64 image: {str(e)}")

    # TODO: Replace this with actual storage upload (S3, R2, etc.)
    # For now, save to local filesystem as placeholder
    upload_dir = os.path.join(os.getcwd(), "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".jpg" if "jpeg" in payload.mime_type.lower() else ".png"
    filename = f"{user.public_id}_{timestamp}{ext}"
    filepath = os.path.join(upload_dir, filename)

    # Save file
    with open(filepath, "wb") as f:
        f.write(image_data)

    # Generate URL (replace with your CDN URL in production)
    profile_image_url = f"/uploads/avatars/{filename}"

    # Update database
    prof.profile_image = profile_image_url
    db.add(prof)
    db.commit()

    return AvatarUploadResponse(profile_image=profile_image_url)

# ---------- Routes: Tours ----------

@router.get("/{user_id}/tours", response_model=List[TourOut])
def list_tours(user_id: str, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    q = db.query(BuyerTour).filter(BuyerTour.buyer_id == buyer_id).order_by(BuyerTour.created_at.desc())
    return q.all()

@router.post("/{user_id}/tours", response_model=TourOut, status_code=status.HTTP_201_CREATED)
def create_tour(user_id: str, payload: TourIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    tour = BuyerTour(
        buyer_id=buyer_id,
        property_id=payload.property_id,  # if you support public_id resolution, do it here
        scheduled_at=payload.scheduled_at,
        status=(payload.status or "requested"),
        note=payload.note,
        agent_name=payload.agent_name,
        agent_phone=payload.agent_phone,
    )
    db.add(tour)
    db.commit()
    db.refresh(tour)
    return tour

@router.patch("/{user_id}/tours/{tour_id}", response_model=TourOut)
def update_tour(user_id: str, tour_id: int, payload: TourIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    tour = db.query(BuyerTour).filter(BuyerTour.id == tour_id, BuyerTour.buyer_id == buyer_id).first()
    if not tour:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(tour, field, value)

    db.add(tour)
    db.commit()
    db.refresh(tour)
    return tour

@router.delete("/{user_id}/tours/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tour(user_id: str, tour_id: int, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    tour = db.query(BuyerTour).filter(BuyerTour.id == tour_id, BuyerTour.buyer_id == buyer_id).first()
    if not tour:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour not found")
    db.delete(tour)
    db.commit()
    return None

# ---------- Routes: Documents ----------

@router.get("/{user_id}/documents", response_model=List[DocumentOut])
def list_documents(user_id: str, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    q = db.query(BuyerDocument).filter(BuyerDocument.buyer_id == buyer_id).order_by(BuyerDocument.created_at.desc())
    return q.all()

@router.post("/{user_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(user_id: str, payload: DocumentIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    doc = BuyerDocument(
        buyer_id=buyer_id,
        property_id=payload.property_id,
        filename=payload.filename,
        file_url=payload.file_url,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        note=payload.note,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@router.delete("/{user_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(user_id: str, doc_id: int, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    buyer_id = _resolve_buyer_id(db, int(user.id))
    doc = db.query(BuyerDocument).filter(BuyerDocument.id == doc_id, BuyerDocument.buyer_id == buyer_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(doc)
    db.commit()
    return None