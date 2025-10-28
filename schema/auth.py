# schema/auth.py
from __future__ import annotations
from typing import List, Optional, Literal, Union, Annotated, Dict
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, AliasChoices
from pydantic.config import ConfigDict

from src.schemas import UserOut, OrgParseOut

PlanLiteral = Literal[
    "userFree",
    "builderFree",
    "builderPro",
    "builderEnterprise",
    "communityFree",
    "communityEnterprise",
    "existingActive",
    "salesRep",
    "communityAdminVerify",
]

class RoleSelectionIn(BaseModel):
    # accept any of these keys: user_public_id, public_id, userPublicId
    user_public_id: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("user_public_id", "public_id", "userPublicId"),
    )
    # allow only supported roles (relax to `str` if needed)
    role: Literal["buyer", "builder", "community", "community_admin", "salesrep"]
    # org_id can be null or absent; accept org_id / orgId
    org_id: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("org_id", "orgId"),
    )
    # plan can arrive as selected_plan / plan_tier / planTier / selectedPlan
    selected_plan: Optional[PlanLiteral] = Field(
        None,
        validation_alias=AliasChoices("selected_plan", "plan_tier", "planTier", "selectedPlan"),
    )

    # ignore unexpected extra keys instead of failing, and allow populate_by_name
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

class RoleSelectionOut(BaseModel):
    user: UserOut
    role: str                      # ← was RoleOut; now just the role key e.g. "buyer"
    plan_label: str
    requires_payment: bool
    next_step: Literal["finish", "payment", "org_info"]
    messages: list[str] = []
    parsed_org: OrgParseOut

class OrgLookupOut(BaseModel):
    is_existing: bool
    existing_active: bool
    tier: Optional[str] = None
    org_type: Optional[str] = None
    no_pay: bool


class UserOutLite(BaseModel):
    public_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    is_email_verified: bool
    created_at: datetime

# --- Role-scoped form payloads ---
class BuilderForm(BaseModel):
    role: Literal["builder"] = "builder"
    public_id: str
    company_name: str
    enterprise_number: Optional[str] = None
    company_address: Optional[str] = None
    staff_size: Optional[str] = None
    years_in_business: Optional[int] = None
    website_url: Optional[str] = None

class CommunityForm(BaseModel):
    role: Literal["community"] = "community"
    public_id: str
    community_name: str
    community_address: Optional[str] = None
    city: str
    state: str
    stage: Optional[str] = None
    enterprise_number: Optional[str] = None

class CommunityAdminForm(BaseModel):
    role: Literal["community_admin"] = "community_admin"
    public_id: str
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    sex: Optional[str] = None
    community_link: str
    community_address: Optional[str] = None

class SalesRepForm(BaseModel):
    role: Literal["salesrep"] = "salesrep"
    public_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    sex: Optional[str] = None
    dob: Optional[datetime] = None
    company_account_number: Optional[str] = None
    office_location: Optional[str] = None
    community_id: Optional[str] = None
    brokerage: Optional[str] = None
    license_id: Optional[str] = None
    years_at_company: Optional[int] = None

class BuyerForm(BaseModel):
    role: Literal["buyer"] = "buyer"
    public_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    state: str
    zip: Optional[str] = None
    sex: Optional[str] = None
    income_range: Optional[str] = None
    first_time: Optional[str] = None
    home_type: Optional[str] = None
    budget_min: Optional[str] = None
    budget_max: Optional[str] = None
    location_interest: Optional[str] = None
    builder_interest: Optional[str] = None

RoleForm = Annotated[
    Union[BuilderForm, CommunityForm, CommunityAdminForm, SalesRepForm, BuyerForm],
    Field(discriminator="role"),
]

class FormPreviewOut(BaseModel):
    role: str
    valid: bool
    missing: Dict[str, str] = Field(default_factory=dict)
    suggestions: List[str] = Field(default_factory=list)
    next_step: Literal["finish", "await_verification", "review"]

class FormCommitOut(BaseModel):
    role: str
    saved: bool
    messages: List[str]
    next_step: Literal["finish", "await_verification"]

__all__ = [
    "PlanLiteral",
    "OrgLookupOut",
    "RoleSelectionIn",
    "RoleSelectionOut",
    "UserOutLite",
    "BuilderForm",
    "CommunityForm",
    "CommunityAdminForm",
    "SalesRepForm",
    "BuyerForm",
    "RoleForm",
    "FormPreviewOut",
    "FormCommitOut",
]