# src/schemas.py
from datetime import datetime
from typing import Optional, Literal, Union, Annotated, List, Dict
from pydantic import BaseModel, EmailStr, model_validator, ConfigDict
from pydantic import Field as PydField
from decimal import Decimal

# Role payload model returned with the user
class RoleOut(BaseModel):
    key: Literal["buyer", "builder", "community", "community_admin", "salesrep", "admin"]
    name: str

# Request model for updating a user's role

class UserRoleUpdate(BaseModel):
    role: Literal["buyer", "builder", "community", "community_admin", "salesrep", "admin"]
    model_config = ConfigDict(json_schema_extra={
        "example": {"role": "buyer"}
    })

# Request model for updating a user's tier
class TierUpdate(BaseModel):
    tier: Literal["free", "pro", "enterprise"]
    model_config = ConfigDict(json_schema_extra={
        "example": {"tier": "pro"}
    })

class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_e164: Optional[str] = None
    password: str
    confirm_password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "user@example.com",
                "phone_e164": "+18325550123",
                "password": "ExamplePass123!",
                "confirm_password": "ExamplePass123!"
            }
        }
    )

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class UserOut(BaseModel):
    public_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_e164: Optional[str] = None
    role: Optional[RoleOut] = None
    is_email_verified: bool
    onboarding_completed: bool = False
    plan_tier: Optional[Literal["free", "pro", "enterprise"]] = "free"
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str
    requires_email_verification: bool = True

class LoginIn(BaseModel):
    email: EmailStr
    password: str

# =============================
# Step 2: Role Selection & Org Lookup
# =============================

class OrgLookupOut(BaseModel):
    is_existing: bool
    existing_active: bool
    tier: Optional[Literal["free", "pro", "enterprise"]] = None  # constrained to known tiers
    org_type: Optional[Literal["builder", "community"]] = None  # one of: builder, community
    no_pay: bool


# Parsed organization info used in role selection responses
class OrgParseOut(BaseModel):
    is_existing: bool
    existing_active: bool
    tier: Optional[Literal["free", "pro", "enterprise"]] = None
    org_type: Optional[Literal["builder", "community"]] = None
    no_pay: bool

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "is_existing": False,
            "existing_active": False,
            "tier": "free",
            "org_type": "builder",
            "no_pay": True
        }
    })

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
    user_public_id: str
    role: Literal["buyer", "builder", "community", "community_admin", "salesrep", "admin"]
    org_id: Optional[str] = None
    selected_plan: Optional[PlanLiteral] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_public_id": "f1b5e2f0-1234-4c9c-9a88-0b2e4dbbe123",
            "role": "buyer",
            "org_id": None,
            "selected_plan": "userFree"
        }
    })

class RoleSelectionOut(BaseModel):
    user: UserOut
    role: Literal["buyer", "builder", "community", "community_admin", "salesrep", "admin"]
    plan_label: Optional[str] = None
    requires_payment: bool
    next_step: Literal["finish", "checkout", "await_verification"]
    messages: List[str]
    parsed_org: Optional[OrgParseOut] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user": {
                "public_id": "f1b5e2f0-1234-4c9c-9a88-0b2e4dbbe123",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "user@example.com",
                "role": {"key": "buyer", "name": "Buyer"},
                "is_email_verified": True,
                "onboarding_completed": False,
                "plan_tier": "free",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-02T12:00:00Z"
            },
            "role": "buyer",
            "plan_label": "Free Plan",
            "requires_payment": False,
            "next_step": "finish",
            "messages": [],
            "parsed_org": None
        }
    })

# =============================
# Step 3: Role-Based Forms (Preview & Commit)
# =============================
class BuilderForm(BaseModel):
    role: Literal["builder"] = "builder"
    user_public_id: str
    company_name: str
    enterprise_number: Optional[str] = None
    company_address: Optional[str] = None
    staff_size: Optional[str] = None  # "1–5", "6–10", etc.
    years_in_business: Optional[int] = None
    website_url: Optional[str] = None

class CommunityForm(BaseModel):
    role: Literal["community"] = "community"
    user_public_id: str
    community_name: str
    community_address: Optional[str] = None
    city: str
    state: str
    stage: Optional[str] = None  # "Pre-development", "First phase", etc.
    enterprise_number: Optional[str] = None

class CommunityAdminForm(BaseModel):
    role: Literal["community_admin"] = "community_admin"
    user_public_id: str
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    sex: Optional[str] = None
    community_link: str  # existing community lookup text/ID
    community_address: Optional[str] = None

class SalesRepForm(BaseModel):
    role: Literal["salesrep"] = "salesrep"
    user_public_id: str
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
    user_public_id: str
    # personal
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    sex: Optional[str] = None
    # preferences
    income_range: Optional[str] = None
    first_time: Optional[str] = None  # "Yes"/"No"/"Prefer not to say"
    home_type: Optional[str] = None   # "Single home"/"Multiple homes"
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    location_interest: Optional[str] = None
    builder_interest: Optional[str] = None

    @model_validator(mode="after")
    def check_budget_range(self):
        if self.budget_min is not None and self.budget_max is not None:
            if self.budget_min > self.budget_max:
                raise ValueError("budget_min cannot be greater than budget_max")
        return self

# Tagged union keyed by `role`
RoleForm = Annotated[
    Union[BuilderForm, CommunityForm, CommunityAdminForm, SalesRepForm, BuyerForm],
    PydField(discriminator="role")
]

class FormPreviewOut(BaseModel):
    role: Literal["buyer", "builder", "community", "community_admin", "salesrep", "admin"]
    valid: bool
    missing: Dict[str, str] = PydField(default_factory=dict)
    suggestions: List[str] = PydField(default_factory=list)
    next_step: Literal["finish", "await_verification", "review"]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "role": "buyer",
            "valid": True,
            "missing": {},
            "suggestions": [],
            "next_step": "finish"
        }
    })

class FormCommitOut(BaseModel):
    role: Literal["buyer", "builder", "community", "community_admin", "salesrep", "admin"]
    saved: bool
    messages: List[str]
    next_step: Literal["finish", "await_verification"]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "role": "buyer",
            "saved": True,
            "messages": ["Saved"],
            "next_step": "finish"
        }
    })