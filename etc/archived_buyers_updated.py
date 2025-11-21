# routes/profiles/buyers_updated.py
"""
Updated Buyer Profile Routes with Public ID Support

NEW ENDPOINTS (Recommended):
- GET    /buyers/{buyer_id}              - Get buyer by BYR-xxx ID
- PATCH  /buyers/{buyer_id}              - Update buyer by BYR-xxx ID
- DELETE /buyers/{buyer_id}              - Delete buyer by BYR-xxx ID
- GET    /buyers/{buyer_id}/tours        - List tours for buyer
- POST   /buyers/{buyer_id}/tours        - Create tour for buyer

LEGACY ENDPOINTS (User-based, keep for backward compatibility):
- GET    /users/{user_id}/buyer          - Get buyer by USR-xxx ID
- POST   /users/{user_id}/buyer          - Create buyer for user
- PATCH  /users/{user_id}/buyer          - Update buyer by user ID
"""

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

# Import our new helper utilities
from src.route_helpers import (
    get_user_by_public_id,
    get_buyer_by_public_id,
    get_buyer_by_user_id,
    build_buyer_profile_response,
)
from src.id_generator import generate_buyer_id


router = APIRouter()


# =============================================================================
# NEW: Direct Buyer Resource Endpoints (Recommended)
# =============================================================================

@router.get("/buyers/{buyer_id}", response_model=BuyerProfileOut, tags=["Buyers"])
def get_buyer_profile_by_id(buyer_id: str, db: Session = Depends(get_db)):
    """
    Get buyer profile by buyer buyer_id.

    **New endpoint** - Direct resource access

    Args:
        buyer_id: Buyer buyer_id (e.g., BYR-1699564234-A7K9M2)

    Returns:
        BuyerProfileOut with buyer_id as id field

    Example:
        GET /buyers/BYR-1699564234-A7K9M2
    """
    buyer = get_buyer_by_public_id(db, buyer_id)
    user = db.query(Users).filter(Users.user_id == buyer.user_id).first()

    return build_buyer_profile_response(buyer, user)


@router.patch("/buyers/{buyer_id}", response_model=BuyerProfileOut, tags=["Buyers"])
def update_buyer_profile_by_id(
    buyer_id: str,
    payload: BuyerProfileIn,
    db: Session = Depends(get_db)
):
    """
    Update buyer profile by buyer buyer_id.

    **New endpoint** - Direct resource access

    Args:
        buyer_id: Buyer buyer_id (e.g., BYR-1699564234-A7K9M2)
        payload: Fields to update

    Returns:
        Updated BuyerProfileOut

    Example:
        PATCH /buyers/BYR-1699564234-A7K9M2
        Body: {"display_name": "John Doe", "budget_max_usd": 500000}
    """
    buyer = get_buyer_by_public_id(db, buyer_id)
    user = db.query(Users).filter(Users.user_id == buyer.user_id).first()

    # Update only fields provided in payload
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(buyer, field, value)

    db.add(buyer)
    db.commit()
    db.refresh(buyer)

    return build_buyer_profile_response(buyer, user)


@router.delete("/buyers/{buyer_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Buyers"])
def delete_buyer_profile_by_id(buyer_id: str, db: Session = Depends(get_db)):
    """
    Delete buyer profile by buyer buyer_id.

    **New endpoint** - Direct resource access

    Args:
        buyer_id: Buyer buyer_id (e.g., BYR-1699564234-A7K9M2)

    Returns:
        204 No Content on success

    Example:
        DELETE /buyers/BYR-1699564234-A7K9M2
    """
    buyer = get_buyer_by_public_id(db, buyer_id)

    db.delete(buyer)
    db.commit()

    return None


# =============================================================================
# NEW: Buyer Tours (using buyer_id directly)
# =============================================================================

@router.get("/buyers/{buyer_id}/tours", response_model=List[TourOut], tags=["Buyer Tours"])
def list_buyer_tours(buyer_id: str, db: Session = Depends(get_db)):
    """
    List all tours for a buyer.

    Args:
        buyer_id: Buyer public_id (e.g., BYR-1699564234-A7K9M2)

    Returns:
        List of tours

    Example:
        GET /buyers/BYR-1699564234-A7K9M2/tours
    """
    buyer = get_buyer_by_public_id(db, buyer_id)

    tours = db.query(BuyerTour).filter(
        BuyerTour.buyer_id == buyer.id
    ).order_by(BuyerTour.created_at.desc()).all()

    return tours


@router.post("/buyers/{buyer_id}/tours", response_model=TourOut, status_code=status.HTTP_201_CREATED, tags=["Buyer Tours"])
def create_buyer_tour(
    buyer_id: str,
    payload: TourIn,
    db: Session = Depends(get_db)
):
    """
    Create a tour for a buyer.

    Args:
        buyer_id: Buyer public_id (e.g., BYR-1699564234-A7K9M2)
        payload: Tour details

    Returns:
        Created tour

    Example:
        POST /buyers/BYR-1699564234-A7K9M2/tours
        Body: {"property_id": 123, "scheduled_at": "2025-12-01T10:00:00Z"}
    """
    buyer = get_buyer_by_public_id(db, buyer_id)

    tour = BuyerTour(
        buyer_id=buyer.id,  # Internal DB ID
        property_id=payload.property_id,
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


@router.patch("/buyers/{buyer_id}/tours/{tour_id}", response_model=TourOut, tags=["Buyer Tours"])
def update_buyer_tour(
    buyer_id: str,
    tour_id: int,
    payload: TourIn,
    db: Session = Depends(get_db)
):
    """Update a specific tour for a buyer."""
    buyer = get_buyer_by_public_id(db, buyer_id)

    tour = db.query(BuyerTour).filter(
        BuyerTour.id == tour_id,
        BuyerTour.buyer_id == buyer.id
    ).first()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tour {tour_id} not found for buyer {buyer_id}"
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(tour, field, value)

    db.add(tour)
    db.commit()
    db.refresh(tour)

    return tour


@router.delete("/buyers/{buyer_id}/tours/{tour_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Buyer Tours"])
def delete_buyer_tour(buyer_id: str, tour_id: int, db: Session = Depends(get_db)):
    """Delete a specific tour for a buyer."""
    buyer = get_buyer_by_public_id(db, buyer_id)

    tour = db.query(BuyerTour).filter(
        BuyerTour.id == tour_id,
        BuyerTour.buyer_id == buyer.id
    ).first()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tour {tour_id} not found for buyer {buyer_id}"
        )

    db.delete(tour)
    db.commit()

    return None


# =============================================================================
# NEW: Buyer Documents (using buyer_id directly)
# =============================================================================

@router.get("/buyers/{buyer_id}/documents", response_model=List[DocumentOut], tags=["Buyer Documents"])
def list_buyer_documents(buyer_id: str, db: Session = Depends(get_db)):
    """List all documents for a buyer."""
    buyer = get_buyer_by_public_id(db, buyer_id)

    docs = db.query(BuyerDocument).filter(
        BuyerDocument.buyer_id == buyer.id
    ).order_by(BuyerDocument.created_at.desc()).all()

    return docs


@router.post("/buyers/{buyer_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED, tags=["Buyer Documents"])
def create_buyer_document(
    buyer_id: str,
    payload: DocumentIn,
    db: Session = Depends(get_db)
):
    """Upload/create a document for a buyer."""
    buyer = get_buyer_by_public_id(db, buyer_id)

    doc = BuyerDocument(
        buyer_id=buyer.id,  # Internal DB ID
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


@router.delete("/buyers/{buyer_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Buyer Documents"])
def delete_buyer_document(buyer_id: str, doc_id: int, db: Session = Depends(get_db)):
    """Delete a specific document for a buyer."""
    buyer = get_buyer_by_public_id(db, buyer_id)

    doc = db.query(BuyerDocument).filter(
        BuyerDocument.id == doc_id,
        BuyerDocument.buyer_id == buyer.id
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found for buyer {buyer_id}"
        )

    db.delete(doc)
    db.commit()

    return None


# =============================================================================
# LEGACY: User-Based Endpoints (Backward Compatibility)
# =============================================================================

@router.get("/users/{user_id}/buyer", response_model=BuyerProfileOut, tags=["Buyers (Legacy)"])
def get_buyer_by_user(user_id: str, db: Session = Depends(get_db)):
    """
    **LEGACY ENDPOINT** - Get buyer profile by user ID.

    Use `/buyers/{buyer_id}` for new implementations.

    Args:
        user_id: User user_id (e.g., USR-1699564234-A7K9M2)

    Returns:
        BuyerProfileOut

    Example:
        GET /users/USR-1699564234-A7K9M2/buyer
    """
    buyer = get_buyer_by_user_id(db, user_id)
    user = db.query(Users).filter(Users.user_id == buyer.user_id).first()

    return build_buyer_profile_response(buyer, user)


@router.post("/users/{user_id}/buyer", response_model=BuyerProfileOut, status_code=status.HTTP_201_CREATED, tags=["Buyers (Legacy)"])
def create_buyer_for_user(
    user_id: str,
    payload: BuyerProfileIn,
    db: Session = Depends(get_db)
):
    """
    **LEGACY ENDPOINT** - Create buyer profile for a user.

    Creates a buyer profile and generates a unique buyer_id.

    Args:
        user_id: User user_id (e.g., USR-1699564234-A7K9M2)
        payload: Buyer profile data

    Returns:
        Created BuyerProfileOut with buyer_id

    Example:
        POST /users/USR-1699564234-A7K9M2/buyer
    """
    user = get_user_by_public_id(db, user_id)

    # Check if buyer profile already exists
    existing = db.query(BuyerProfile).filter(BuyerProfile.user_id == user.user_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Buyer profile already exists for user {user_id}"
        )

    # Create buyer profile with generated buyer_id
    buyer = BuyerProfile(
        buyer_id=generate_buyer_id(),  # NEW: Generate typed buyer_id
        user_id=user.user_id,

        # Identity / display
        display_name=payload.display_name or f"{payload.first_name or user.first_name} {payload.last_name or user.last_name}".strip(),
        first_name=payload.first_name or user.first_name,
        last_name=payload.last_name or user.last_name,
        profile_image=payload.profile_image,
        bio=payload.bio,
        location=payload.location,
        website_url=payload.website_url,

        # Contact - Canonical fields
        email=payload.email or payload.contact_email or user.email,
        phone=payload.phone or payload.contact_phone or user.phone_e164,

        # Contact - Legacy fields
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

    db.add(buyer)

    # Mark onboarding as completed
    user.onboarding_completed = True

    db.commit()
    db.refresh(buyer)

    return build_buyer_profile_response(buyer, user)


@router.patch("/users/{user_id}/buyer", response_model=BuyerProfileOut, tags=["Buyers (Legacy)"])
def update_buyer_by_user(
    user_id: str,
    payload: BuyerProfileIn,
    db: Session = Depends(get_db)
):
    """
    **LEGACY ENDPOINT** - Update buyer profile by user ID.

    Use `PATCH /buyers/{buyer_id}` for new implementations.
    """
    buyer = get_buyer_by_user_id(db, user_id)
    user = db.query(Users).filter(Users.user_id == buyer.user_id).first()

    # Update only provided fields
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(buyer, field, value)

    # Mark onboarding as completed
    user.onboarding_completed = True

    db.add(buyer)
    db.commit()
    db.refresh(buyer)

    return build_buyer_profile_response(buyer, user)


# =============================================================================
# Avatar Upload
# =============================================================================

class AvatarUploadRequest(BaseModel):
    image_base64: str
    mime_type: str


class AvatarUploadResponse(BaseModel):
    profile_image: str


@router.post("/buyers/{buyer_id}/avatar", response_model=AvatarUploadResponse, tags=["Buyer Avatar"])
def upload_buyer_avatar(
    buyer_id: str,
    payload: AvatarUploadRequest,
    db: Session = Depends(get_db)
):
    """
    Upload avatar image for buyer profile.

    Args:
        buyer_id: Buyer buyer_id (e.g., BYR-1699564234-A7K9M2)
        payload: Base64 encoded image and mime type

    Returns:
        URL to uploaded image

    TODO: Configure cloud storage (S3, R2, etc.)
    """
    buyer = get_buyer_by_public_id(db, buyer_id)

    try:
        # Decode base64 image
        image_data = base64.b64decode(payload.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image: {str(e)}"
        )

    # TODO: Replace with cloud storage upload (S3, R2, etc.)
    upload_dir = os.path.join(os.getcwd(), "uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename using buyer buyer_id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".jpg" if "jpeg" in payload.mime_type.lower() else ".png"
    filename = f"{buyer.buyer_id}_{timestamp}{ext}"
    filepath = os.path.join(upload_dir, filename)

    # Save file
    with open(filepath, "wb") as f:
        f.write(image_data)

    # Generate URL (replace with CDN URL in production)
    profile_image_url = f"/uploads/avatars/{filename}"

    # Update database
    buyer.profile_image = profile_image_url
    db.add(buyer)
    db.commit()

    return AvatarUploadResponse(profile_image=profile_image_url)
