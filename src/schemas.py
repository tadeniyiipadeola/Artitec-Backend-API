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
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    sex: Optional[str] = None
    # preferences
    income_range: Optional[str] = None
    # Accept either legacy string or new boolean for first-time buyer
    first_time: Optional[str] = None                 # "Yes"/"No"/"Prefer not to say" (legacy)
    first_time_home_buyer: Optional[bool] = None     # new (preferred)
    home_type: Optional[str] = None   # "Single home"/"Multiple homes"
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    location_interest: Optional[str] = None
    builder_interest: Optional[str] = None
    buying_timeline: Optional[str] = None            # "0–3 months","3–6 months","6–12 months","12+ months"
    financing_status: Optional[str] = None           # "Pre-approved","Pre-qualified","Researching","Cash buyer"
    loan_program: Optional[str] = None               # "FHA","Conventional","VA","USDA","Other"
    preferred_channel: Optional[str] = None          # "Email","Phone","Text","In-app"
    household_income: Optional[int] = None           # plain USD integer

    @model_validator(mode="before")
    @classmethod
    def _coerce_numeric_fields(cls, values):
        """
        Coerce string currency inputs like '250,000' -> Decimal('250000')
        and 'household_income' -> int when provided as a string.
        """
        def _to_decimal(x):
            if x is None or isinstance(x, Decimal):
                return x
            s = str(x).replace(",", "").strip()
            if s == "":
                return None
            try:
                return Decimal(s)
            except Exception:
                return None
        def _to_int(x):
            if x is None or isinstance(x, int):
                return x
            s = str(x).replace(",", "").strip()
            if s == "":
                return None
            try:
                return int(float(s))
            except Exception:
                return None
        vals = dict(values or {})
        vals["budget_min"] = _to_decimal(vals.get("budget_min"))
        vals["budget_max"] = _to_decimal(vals.get("budget_max"))
        vals["household_income"] = _to_int(vals.get("household_income"))
        return vals

    @model_validator(mode="after")
    def check_budget_range(self):
        if self.budget_min is not None and self.budget_max is not None:
            if self.budget_min > self.budget_max:
                raise ValueError("budget_min cannot be greater than budget_max")
        return self

    def as_formatted_dict(self) -> dict:
        """
        Return a dictionary representation with currency fields formatted as strings with dollar signs.
        Example: 250000 -> "$250,000"
        """
        data = self.dict()
        def _fmt_money(val):
            if val is None:
                return None
            try:
                return f"${val:,.0f}"
            except Exception:
                return str(val)
        for key in ["budget_min", "budget_max", "household_income"]:
            data[key] = _fmt_money(data.get(key))
        return data

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


# =============================
# Enterprise Builder Provisioning
# =============================

class EnterpriseBuilderProvisionIn(BaseModel):
    """
    Admin-initiated enterprise builder account creation.
    Creates builder profile, primary user account, and invitation code.
    """
    # Builder profile information
    company_name: str
    website_url: Optional[str] = None
    enterprise_number: Optional[str] = None
    company_address: Optional[str] = None
    staff_size: Optional[str] = None
    years_in_business: Optional[int] = None

    # Primary contact/user information
    primary_contact_email: EmailStr
    primary_contact_first_name: str
    primary_contact_last_name: str
    primary_contact_phone: Optional[str] = None

    # Invitation settings
    invitation_expires_days: Optional[int] = 7  # Default: 7 days
    custom_message: Optional[str] = None

    # Account settings
    plan_tier: Literal["pro", "enterprise"] = "enterprise"

    # Community assignments (optional)
    # List of community IDs where the builder operates
    # If provided, these communities will be associated with the builder in builder_communities table
    community_ids: Optional[List[str]] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "company_name": "Perry Homes",
            "website_url": "https://www.perryhomes.com",
            "enterprise_number": "ENT-12345",
            "company_address": "123 Builder Lane, Houston, TX 77002",
            "staff_size": "500+",
            "years_in_business": 65,
            "primary_contact_email": "john.smith@perryhomes.com",
            "primary_contact_first_name": "John",
            "primary_contact_last_name": "Smith",
            "primary_contact_phone": "+18325551234",
            "invitation_expires_days": 7,
            "custom_message": "Welcome to Artitec! Please complete your account setup.",
            "plan_tier": "enterprise",
            "community_ids": ["COM-123", "COM-456"]
        }
    })


class InvitationOut(BaseModel):
    """Response model for invitation details"""
    invitation_code: str
    builder_id: str
    invited_email: str
    invited_role: Literal["builder", "salesrep", "manager", "viewer"]
    invited_first_name: Optional[str] = None
    invited_last_name: Optional[str] = None
    expires_at: datetime
    status: Literal["pending", "used", "expired", "revoked"]
    custom_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuilderProfileOut(BaseModel):
    """Response model for builder profile"""
    builder_id: str
    name: str
    website: Optional[str] = None
    verified: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnterpriseBuilderProvisionOut(BaseModel):
    """
    Response after successfully creating enterprise builder account.
    Includes builder profile, user account, and invitation details.
    """
    builder: BuilderProfileOut
    user: UserOut
    invitation: InvitationOut
    message: str
    next_steps: List[str]

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "builder": {
                "builder_id": "B_329_XXX_XXX_XXX_XXX",
                "name": "Perry Homes",
                "website": "https://www.perryhomes.com",
                "verified": 1,
                "created_at": "2025-11-17T12:00:00Z"
            },
            "user": {
                "public_id": "f1b5e2f0-1234-4c9c-9a88-0b2e4dbbe123",
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@perryhomes.com",
                "role": {"key": "builder", "name": "Builder"},
                "is_email_verified": False,
                "onboarding_completed": False,
                "plan_tier": "enterprise",
                "created_at": "2025-11-17T12:00:00Z"
            },
            "invitation": {
                "invitation_code": "X3P8Q1R9T2M4",
                "builder_id": "B_329_XXX_XXX_XXX_XXX",
                "invited_email": "john.smith@perryhomes.com",
                "invited_role": "builder",
                "invited_first_name": "John",
                "invited_last_name": "Smith",
                "expires_at": "2025-11-24T12:00:00Z",
                "status": "pending",
                "custom_message": "Welcome to Artitec!",
                "created_at": "2025-11-17T12:00:00Z"
            },
            "message": "Enterprise builder account created successfully",
            "next_steps": [
                "Send invitation code X3P8Q1R9T2M4 to john.smith@perryhomes.com",
                "User must register/login and accept invitation to activate account",
                "After activation, user can invite additional team members"
            ]
        }
    })


class InvitationValidateOut(BaseModel):
    """
    Response for validating an invitation code.
    Shows invitation details and builder information.
    """
    valid: bool
    invitation_code: str
    builder_name: Optional[str] = None
    invited_email: Optional[str] = None
    invited_role: Optional[Literal["builder", "salesrep", "manager", "viewer"]] = None
    expires_at: Optional[datetime] = None
    custom_message: Optional[str] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "valid": True,
            "invitation_code": "X3P8Q1R9T2M4",
            "builder_name": "Perry Homes",
            "invited_email": "john.smith@perryhomes.com",
            "invited_role": "builder",
            "expires_at": "2025-11-24T12:00:00Z",
            "custom_message": "Welcome to Artitec!",
            "error_message": None
        }
    })


class InvitationAcceptIn(BaseModel):
    """Request to accept an invitation after user registration/login"""
    invitation_code: str
    user_public_id: str  # The logged-in user accepting the invitation

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "invitation_code": "X3P8Q1R9T2M4",
            "user_public_id": "f1b5e2f0-1234-4c9c-9a88-0b2e4dbbe123"
        }
    })


class TeamMemberOut(BaseModel):
    """Response model for builder team member"""
    id: int
    builder_id: str
    user_id: str
    role: Literal["admin", "sales_rep", "manager", "viewer"]
    permissions: Optional[List[str]] = None
    communities_assigned: Optional[List[str]] = None
    is_active: Literal["active", "inactive"]
    created_at: datetime

    # Nested user info
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)


class TeamMemberCreateIn(BaseModel):
    """Create a new team member invitation (for builder admins inviting additional team members)"""
    builder_id: str
    invited_email: EmailStr
    invited_role: Literal["salesrep", "manager", "viewer"] = "salesrep"
    invited_first_name: Optional[str] = None
    invited_last_name: Optional[str] = None
    permissions: Optional[List[str]] = None
    # Community assignments (list of community IDs)
    # Empty/None = access to all communities
    communities_assigned: Optional[List[str]] = None
    custom_message: Optional[str] = None
    invitation_expires_days: Optional[int] = 7

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "builder_id": "BLD-1699564234-X3P8Q1",
            "invited_email": "jane.doe@perryhomes.com",
            "invited_role": "salesrep",
            "invited_first_name": "Jane",
            "invited_last_name": "Doe",
            "permissions": ["manage_properties", "schedule_tours"],
            "communities_assigned": ["CMY-1699564234-Z5R7N4", "CMY-1699564235-M2K9L3"],
            "custom_message": "Welcome to Perry Homes Cinco Ranch team!",
            "invitation_expires_days": 7
        }
    })


class TeamMemberUpdateIn(BaseModel):
    """Update team member role, permissions, or community assignments"""
    role: Optional[Literal["admin", "sales_rep", "manager", "viewer"]] = None
    permissions: Optional[List[str]] = None
    communities_assigned: Optional[List[str]] = None
    is_active: Optional[Literal["active", "inactive"]] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "role": "sales_rep",
            "permissions": ["manage_properties", "schedule_tours", "view_analytics"],
            "communities_assigned": ["CMY-1699564234-Z5R7N4", "CMY-1699564236-P7Q8R9"],
            "is_active": "active"
        }
    })


class CommunityOut(BaseModel):
    """Response model for community details"""
    community_id: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    property_count: Optional[int] = 0
    active_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BuilderCommunityListOut(BaseModel):
    """List of communities where builder is active"""
    builder_id: str
    builder_name: str
    communities: List[CommunityOut]
    total_communities: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "builder_id": "BLD-1699564234-X3P8Q1",
            "builder_name": "Perry Homes",
            "communities": [
                {
                    "community_id": "CMY-1699564234-Z5R7N4",
                    "name": "Cinco Ranch",
                    "city": "Katy",
                    "state": "TX",
                    "property_count": 18,
                    "active_status": "active"
                },
                {
                    "community_id": "CMY-1699564235-M2K9L3",
                    "name": "Bridgeland",
                    "city": "Cypress",
                    "state": "TX",
                    "property_count": 24,
                    "active_status": "active"
                }
            ],
            "total_communities": 2
        }
    })