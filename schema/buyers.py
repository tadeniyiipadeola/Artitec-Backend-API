from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

# Pydantic validators (v2 vs v1)
try:
    # v2
    from pydantic import field_validator
except Exception:  # pragma: no cover
    field_validator = None  # type: ignore
try:
    # v1
    from pydantic import validator as _v1_validator  # alias to avoid name clash
except Exception:  # pragma: no cover
    _v1_validator = None  # type: ignore

try:
    # Pydantic v2
    from pydantic import ConfigDict
    _HAS_V2 = True
except Exception:  # pragma: no cover
    _HAS_V2 = False

# ---------------------------------------------------------------------------
# Helpers: normalize human-friendly labels from the iOS app into enum codes
# ---------------------------------------------------------------------------
def _norm_str(x):
    if x is None:
        return None
    if isinstance(x, str):
        return x.strip()
    return str(x).strip()

def normalize_timeline(val: str | None) -> str | None:
    v = _norm_str(val)
    if not v:
        return None
    lo = v.lower().replace('–', '-').replace('—', '-')
    mapping = {
        "immediately": "immediately",
        "0-3 months": "one_to_three_months",
        "0–3 months": "one_to_three_months",
        "0 — 3 months": "one_to_three_months",
        "0 to 3 months": "one_to_three_months",
        "3-6 months": "three_to_six_months",
        "3–6 months": "three_to_six_months",
        "3 to 6 months": "three_to_six_months",
        "6-12 months": "six_plus_months",
        "6–12 months": "six_plus_months",
        "6 to 12 months": "six_plus_months",
        "12+ months": "six_plus_months",
        "12 plus months": "six_plus_months",
        "12 or more months": "six_plus_months",
        "exploring": "exploring",
    }
    return mapping.get(lo, "exploring")

def normalize_financing(val: str | None) -> str | None:
    v = _norm_str(val)
    if not v:
        return None
    lo = v.lower()
    mapping = {
        "cash": "cash",
        "cash buyer": "cash",
        "pre-approved": "pre_approved",
        "pre approved": "pre_approved",
        "prequalified": "pre_qualified",
        "pre-qualified": "pre_qualified",
        "pre qualified": "pre_qualified",
        "researching": "needs_pre_approval",
        "needs pre-approval": "needs_pre_approval",
        "needs pre approval": "needs_pre_approval",
        "unknown": "unknown",
    }
    return mapping.get(lo, "unknown")

def normalize_loan_program(val: str | None) -> str | None:
    v = _norm_str(val)
    if not v:
        return None
    lo = v.lower()
    mapping = {
        "conventional": "conventional",
        "fha": "fha",
        "va": "va",
        "usda": "usda",
        "jumbo": "jumbo",
        "other": "other",
    }
    return mapping.get(lo, "other")

def normalize_channel(val: str | None) -> str | None:
    v = _norm_str(val)
    if not v:
        return None
    lo = v.lower().replace("‑", "-")
    mapping = {
        "email": "email",
        "phone": "phone",
        "text": "sms",
        "sms": "sms",
        "in-app": "in_app",
        "in app": "in_app",
        "in_app": "in_app",
    }
    return mapping.get(lo, "email")

def to_int_or_none(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    s = str(val).replace(",", "").strip()
    try:
        return int(float(s))
    except Exception:
        return None

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
    user_id: Optional[str] = None  # FK to users.public_id
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
    household_income_usd: Optional[int] = None
    budget_min_usd: Optional[int] = None
    budget_max_usd: Optional[int] = None
    down_payment_percent: Optional[int] = Field(None, ge=0, le=100)
    lender_name: Optional[str] = None
    agent_name: Optional[str] = None

    # Flexible metadata
    extra: Optional[Dict[str, Any]] = None

    if _HAS_V2 and field_validator:
        # Normalize label inputs coming from iOS menus
        @field_validator("timeline", mode="before")
        @classmethod
        def _v2_norm_timeline(cls, v):
            return normalize_timeline(v)

        @field_validator("financing_status", mode="before")
        @classmethod
        def _v2_norm_financing(cls, v):
            return normalize_financing(v)

        @field_validator("loan_program", mode="before")
        @classmethod
        def _v2_norm_loan(cls, v):
            return normalize_loan_program(v)

        @field_validator("contact_preferred", mode="before")
        @classmethod
        def _v2_norm_channel(cls, v):
            return normalize_channel(v)

        @field_validator("household_income_usd", "budget_min_usd", "budget_max_usd", mode="before")
        @classmethod
        def _v2_ints(cls, v):
            return to_int_or_none(v)

    if not _HAS_V2 and _v1_validator:
        _v = _v1_validator

        @_v("timeline", pre=True, always=True)
        def _v1_norm_timeline(cls, v):
            return normalize_timeline(v)

        @_v("financing_status", pre=True, always=True)
        def _v1_norm_financing(cls, v):
            return normalize_financing(v)

        @_v("loan_program", pre=True, always=True)
        def _v1_norm_loan(cls, v):
            return normalize_loan_program(v)

        @_v("contact_preferred", pre=True, always=True)
        def _v1_norm_channel(cls, v):
            return normalize_channel(v)

        @_v("household_income_usd", "budget_min_usd", "budget_max_usd", pre=True, always=True)
        def _v1_ints(cls, v):
            return to_int_or_none(v)


class BuyerProfileOut(BuyerProfileIn):
    id: int                      # buyer_profiles.id
    user_id: str                 # FK to users.public_id (string in the provided model)
    created_at: datetime
    updated_at: datetime

    def as_formatted_dict(self) -> Dict[str, Any]:
        data = self.dict()
        def _fmt_money(val):
            if val is None:
                return None
            try:
                return f"${val:,.0f}"
            except Exception:
                return str(val)
        for k in ["household_income_usd", "budget_min_usd", "budget_max_usd"]:
            data[k] = _fmt_money(data.get(k))
        return data

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

    if _HAS_V2 and field_validator:
        @field_validator("price_min", "price_max", "lot_min_sqft", mode="before")
        @classmethod
        def _v2_ints(cls, v):
            return to_int_or_none(v)

    if not _HAS_V2 and _v1_validator:
        _v = _v1_validator
        @_v("price_min", "price_max", "lot_min_sqft", pre=True, always=True)
        def _v1_ints(cls, v):
            return to_int_or_none(v)


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