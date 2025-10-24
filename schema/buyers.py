

from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

try:
    # Pydantic v2
    from pydantic import ConfigDict
    _HAS_V2 = True
except Exception:  # pragma: no cover
    _HAS_V2 = False

# ---------------------------------------------------------------------------
# Enums (mirroring SAEnum choices in model/profiles/buyer.py)
# ---------------------------------------------------------------------------
Sex = Literal["female", "male", "non_binary", "other", "prefer_not"]
BuyTimeline = Literal[
    "immediately", "one_to_three_months", "three_to_six_months", "six_plus_months", "exploring"
]
FinancingStatus = Literal[
    "cash", "pre_approved", "pre_qualified", "needs_pre_approval", "unknown"
]
LoanProgram = Literal["conventional", "fha", "va", "usda", "jumbo", "other"]
PreferredChannel = Literal["email", "phone", "sms", "in_app"]
TourStatus = Literal["requested", "confirmed", "completed", "cancelled", "no_show", "rescheduled"]

# ---------------------------------------------------------------------------
# BuyerProfile
# ---------------------------------------------------------------------------
class BuyerProfileIn(BaseModel):
    # Identity / display
    display_name: Optional[str] = None
    avatar_symbol: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website_url: Optional[str] = None

    # Contact
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    contact_preferred: Optional[PreferredChannel] = "email"

    # Core attributes
    sex: Optional[Sex] = None
    timeline: Optional[BuyTimeline] = "exploring"

    # Financing snapshot
    financing_status: Optional[FinancingStatus] = "unknown"
    loan_program: Optional[LoanProgram] = None
    budget_max_usd: Optional[int] = None
    down_payment_percent: Optional[int] = Field(None, ge=0, le=100)
    lender_name: Optional[str] = None
    agent_name: Optional[str] = None

    # Flexible metadata
    extra: Optional[Dict[str, Any]] = None


class BuyerProfileOut(BuyerProfileIn):
    id: int                      # buyer_profiles.id
    user_id: str                 # FK to users.public_id (string in the provided model)
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True

# ---------------------------------------------------------------------------
# BuyerPreference (one-to-one with BuyerProfile via buyer_id)
# ---------------------------------------------------------------------------
class BuyerPreferenceIn(BaseModel):
    # Basic search ranges
    min_beds: Optional[int] = None
    min_baths: Optional[float] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None

    # Property attributes
    has_pool: Optional[bool] = None
    new_construction_ok: Optional[bool] = None
    hoa_ok: Optional[bool] = None
    lot_min_sqft: Optional[int] = None

    # Geography / areas of interest
    cities: Optional[List[str]] = None
    zips: Optional[List[str]] = None
    states: Optional[List[str]] = None

    # Additional features/tags
    features: Optional[List[str]] = None


class BuyerPreferenceOut(BuyerPreferenceIn):
    buyer_id: int                # FK to buyer_profiles.id
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True

# ---------------------------------------------------------------------------
# BuyerTour
# ---------------------------------------------------------------------------
class BuyerTourIn(BaseModel):
    # target property: allow either id or public_id to be supplied by client
    property_id: Optional[int] = None
    property_public_id: Optional[str] = None

    scheduled_at: Optional[datetime] = None
    status: Optional[TourStatus] = "requested"

    # optional details
    note: Optional[str] = None
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None


class BuyerTourOut(BuyerTourIn):
    id: int
    buyer_id: int
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True

# ---------------------------------------------------------------------------
# BuyerDocument
# ---------------------------------------------------------------------------
class BuyerDocumentIn(BaseModel):
    # optional linkage to a property (either id or public_id)
    property_id: Optional[int] = None
    property_public_id: Optional[str] = None

    filename: str
    file_url: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    note: Optional[str] = None


class BuyerDocumentOut(BuyerDocumentIn):
    id: int
    buyer_id: int
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True

# ---------------------------------------------------------------------------
# Reference tables (simple Out models for list endpoints / pickers)
# ---------------------------------------------------------------------------
class RefCodeOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    color_hex: Optional[str] = None

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

# Aliases for clarity in route signatures
TourStatusOut = RefCodeOut
FinancingStatusOut = RefCodeOut
LoanProgramOut = RefCodeOut
BuyingTimelineOut = RefCodeOut
PreferredChannelOut = RefCodeOut


__all__ = [
    # Profile
    "BuyerProfileIn", "BuyerProfileOut",
    # Preferences
    "BuyerPreferenceIn", "BuyerPreferenceOut",
    # Tours
    "BuyerTourIn", "BuyerTourOut",
    # Documents
    "BuyerDocumentIn", "BuyerDocumentOut",
    # Reference tables
    "RefCodeOut", "TourStatusOut", "FinancingStatusOut", "LoanProgramOut", "BuyingTimelineOut", "PreferredChannelOut",
]