
from __future__ import annotations
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
try:
    # Pydantic v2
    from pydantic import ConfigDict
    _HAS_V2 = True
except Exception:  # pragma: no cover
    _HAS_V2 = False

# ---------- Pydantic Schemas ----------


class ContactIn(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    preferred: Optional[Literal["email", "phone", "sms", "in_app"]] = "email"

class FinanceIn(BaseModel):
    financing_status: Optional[Literal["cash", "pre_approved", "pre_qualified", "needs_pre_approval", "unknown"]] = "unknown"
    loan_program: Optional[Literal["conventional", "fha", "va", "usda", "jumbo", "other"]] = None
    budget_max_usd: Optional[int] = None
    down_payment_percent: Optional[int] = Field(None, ge=0, le=100)
    lender_name: Optional[str] = None
    agent_name: Optional[str] = None

class BuyerProfileIn(BaseModel):
    display_name: str
    avatar_symbol: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    sex: Optional[Literal["female", "male", "non_binary", "other", "prefer_not"]] = None
    contact: Optional[ContactIn] = ContactIn()
    timeline: Optional[Literal["immediately", "one_to_three_months", "three_to_six_months", "six_plus_months", "exploring"]] = "exploring"
    finance: Optional[FinanceIn] = FinanceIn()

class BuyerProfileOut(BuyerProfileIn):
    user_id: int
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True

class TourSlot(BaseModel):
    start: datetime
    end: datetime

class TourIn(BaseModel):
    property_public_id: str
    status: Optional[Literal["requested", "confirmed", "completed", "canceled"]] = "requested"
    notes: Optional[str] = None
    preferred_slots: Optional[List[TourSlot]] = None

class TourOut(TourIn):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True

class DocumentIn(BaseModel):
    kind: Literal[
        "id", "pre_approval_letter", "proof_of_funds",
        "employment_letter", "tax_return", "bank_statement", "other"
    ]
    name: str
    file_url: Optional[str] = None

class DocumentOut(DocumentIn):
    id: int
    user_id: int
    uploaded_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:  # Pydantic v1 fallback
        class Config:
            orm_mode = True


__all__ = [
    "ContactIn", "FinanceIn", "BuyerProfileIn", "BuyerProfileOut",
    "TourSlot", "TourIn", "TourOut",
    "DocumentIn", "DocumentOut",
]