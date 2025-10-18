# routes/profiles/buyers.py
from __future__ import annotations
from typing import List, Optional, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Project imports (adjust paths if your app structure differs)
from config.db import get_db  # expects a Dependency that yields a SQLAlchemy Session
from model.profiles.buyer import BuyerProfile, BuyerTour, BuyerDocument, TourStatus, FinancingStatus, LoanProgram, BuyingTimeline, PreferredChannel
from model.user import User
from schema.buyers import BuyerProfileIn, BuyerProfileOut, TourIn, TourOut, DocumentIn, DocumentOut

router = APIRouter() 

# ---------- Helpers ----------

def _ensure_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# ---------- Routes: Buyer Profile ----------

@router.get("/{user_id}", response_model=BuyerProfileOut)
def get_buyer_profile(user_id: int, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")
    return prof

@router.post("/{user_id}", response_model=BuyerProfileOut, status_code=status.HTTP_201_CREATED)
def create_buyer_profile(user_id: int, payload: BuyerProfileIn, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    existing = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Buyer profile already exists")

    prof = BuyerProfile(
        user_id=user_id,
        display_name=payload.display_name,
        avatar_symbol=payload.avatar_symbol,
        location=payload.location,
        bio=payload.bio,
        sex=payload.sex,
        contact_email=payload.contact.email if payload.contact else None,
        contact_phone=payload.contact.phone if payload.contact else None,
        contact_preferred=payload.contact.preferred if payload.contact else "email",
        timeline=payload.timeline,
        financing_status=(payload.finance.financing_status if payload.finance else "unknown"),
        loan_program=(payload.finance.loan_program if payload.finance else None),
        budget_max_usd=(payload.finance.budget_max_usd if payload.finance else None),
        down_payment_percent=(payload.finance.down_payment_percent if payload.finance else None),
        lender_name=(payload.finance.lender_name if payload.finance else None),
        agent_name=(payload.finance.agent_name if payload.finance else None),
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof

@router.patch("/{user_id}", response_model=BuyerProfileOut)
def update_buyer_profile(user_id: int, payload: BuyerProfileIn, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    prof = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")

    # Partial update
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "contact" and value is not None:
            if "email" in value:
                prof.contact_email = value["email"]
            if "phone" in value:
                prof.contact_phone = value["phone"]
            if "preferred" in value and value["preferred"] is not None:
                prof.contact_preferred = value["preferred"]
            continue
        if field == "finance" and value is not None:
            if "financing_status" in value and value["financing_status"] is not None:
                prof.financing_status = value["financing_status"]
            if "loan_program" in value:
                prof.loan_program = value["loan_program"]
            if "budget_max_usd" in value:
                prof.budget_max_usd = value["budget_max_usd"]
            if "down_payment_percent" in value:
                prof.down_payment_percent = value["down_payment_percent"]
            if "lender_name" in value:
                prof.lender_name = value["lender_name"]
            if "agent_name" in value:
                prof.agent_name = value["agent_name"]
            continue
        setattr(prof, field, value)

    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof

# ---------- Routes: Tours ----------

@router.get("/{user_id}/tours", response_model=List[TourOut])
def list_tours(user_id: int, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    q = db.query(BuyerTour).filter(BuyerTour.user_id == user_id).order_by(BuyerTour.created_at.desc())
    return q.all()

@router.post("/{user_id}/tours", response_model=TourOut, status_code=status.HTTP_201_CREATED)
def create_tour(user_id: int, payload: TourIn, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    tour = BuyerTour(
        user_id=user_id,
        property_public_id=payload.property_public_id,
        status=payload.status,
        notes=payload.notes,
        preferred_slots=[s.model_dump() for s in (payload.preferred_slots or [])]
    )
    db.add(tour)
    db.commit()
    db.refresh(tour)
    return tour

@router.patch("/{user_id}/tours/{tour_id}", response_model=TourOut)
def update_tour(user_id: int, tour_id: int, payload: TourIn, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    tour = db.query(BuyerTour).filter(BuyerTour.id == tour_id, BuyerTour.user_id == user_id).first()
    if not tour:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour not found")

    data = payload.model_dump(exclude_unset=True)
    if "preferred_slots" in data:
        tour.preferred_slots = [s.model_dump() for s in (payload.preferred_slots or [])]
    if "status" in data and data["status"] is not None:
        tour.status = data["status"]
    if "notes" in data:
        tour.notes = data["notes"]
    if "property_public_id" in data:
        tour.property_public_id = data["property_public_id"]

    db.add(tour)
    db.commit()
    db.refresh(tour)
    return tour

@router.delete("/{user_id}/tours/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tour(user_id: int, tour_id: int, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    tour = db.query(BuyerTour).filter(BuyerTour.id == tour_id, BuyerTour.user_id == user_id).first()
    if not tour:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour not found")
    db.delete(tour)
    db.commit()
    return None

# ---------- Routes: Documents ----------

@router.get("/{user_id}/documents", response_model=List[DocumentOut])
def list_documents(user_id: int, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    q = db.query(BuyerDocument).filter(BuyerDocument.user_id == user_id).order_by(BuyerDocument.uploaded_at.desc())
    return q.all()

@router.post("/{user_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(user_id: int, payload: DocumentIn, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    doc = BuyerDocument(
        user_id=user_id,
        kind=payload.kind,
        name=payload.name,
        file_url=payload.file_url,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@router.delete("/{user_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(user_id: int, doc_id: int, db: Session = Depends(get_db)):
    _ensure_user(db, user_id)
    doc = db.query(BuyerDocument).filter(BuyerDocument.id == doc_id, BuyerDocument.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(doc)
    db.commit()
    return None