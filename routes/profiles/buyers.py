# routes/profiles/buyers.py
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
def _resolve_buyer_id(db: Session, internal_user_id: int | str) -> int:
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == internal_user_id).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")
    return int(prof.id)

# ---------- Routes: Buyer Profile ----------

@router.get("/{user_id}", response_model=BuyerProfileOut)
def get_buyer_profile(user_id: str, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")
    return prof

@router.post("/{user_id}", response_model=BuyerProfileOut, status_code=status.HTTP_201_CREATED)
def create_buyer_profile(user_id: str, payload: BuyerProfileIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    existing = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Buyer profile already exists")

    prof = BuyerProfile(
        user_id=uid,
        display_name=payload.display_name,
        avatar_symbol=payload.avatar_symbol,
        location=payload.location,
        bio=payload.bio,
        sex=payload.sex,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        contact_preferred=(payload.contact_preferred or "email"),
        timeline=(payload.timeline or "exploring"),
        financing_status=(payload.financing_status or "unknown"),
        loan_program=payload.loan_program,
        household_income_usd=payload.household_income_usd,
        budget_min_usd=payload.budget_min_usd,
        budget_max_usd=payload.budget_max_usd,
        down_payment_percent=payload.down_payment_percent,
        lender_name=payload.lender_name,
        agent_name=payload.agent_name,
        extra=payload.extra,
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof

@router.patch("/{user_id}", response_model=BuyerProfileOut)
def update_buyer_profile(user_id: str, payload: BuyerProfileIn, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == uid).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(prof, field, value)

    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof

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