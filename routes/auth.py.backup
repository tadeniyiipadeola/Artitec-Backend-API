from typing import Optional, Literal, List, Dict
# routes/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.orm import Session
import logging

from pydantic import ValidationError

from config.db import get_db
from config.settings import REFRESH_TTL_DAYS
from model.user import Users, UserCredential, EmailVerification, SessionToken, Role, validate_role, get_role_display_name
from model.profiles.buyer import BuyerProfile
from schema.auth import (
    OrgLookupOut, RoleSelectionIn,
    RoleForm, FormPreviewOut, FormCommitOut, PlanLiteral,
    BuilderForm, CommunityForm, CommunityAdminForm, SalesRepForm, BuyerForm,
)
from src.schemas import RegisterIn, LoginIn, AuthOut, UserOut, RoleSelectionOut, OrgParseOut

from src.utils import gen_public_id, gen_token_hex, hash_password, verify_password, make_access_token
from config.dependencies import require_user


logger = logging.getLogger(__name__)


def _redact(s: Optional[str], keep: int = 3) -> str:
    if not s:
        return ""
    s = str(s)
    return s[:keep] + "…" if len(s) > keep else s

router = APIRouter()

@router.post(
    "/register",
    response_model=AuthOut,
    responses={
        200: {"description": "Registration successful"},
        400: {"description": "Bad Request - Passwords do not match"},
        401: {"description": "Unauthorized"},
        409: {"description": "Conflict - Email already in use"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error - Default user type not seeded or unexpected error"}
    },
    openapi_extra={"security": []}
)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    logger.info("Register endpoint called with email=%s", body.email)
    logger.debug("Handling /register request body: %s", body.dict(exclude={'password','confirm_password'}))
    # Pick a temporary default role so we can create the record now; update on next step
    role_row = db.query(Role).filter(Role.key == "buyer").one_or_none()
    if not role_row:
        # Fallback to any available role
        role_row = db.query(Role).first()
    if not role_row:
        logger.error("Default role not found")
        raise HTTPException(
            status_code=500,
            detail="Default roles not seeded. Seed roles with at least one entry (e.g., 'buyer')."
        )

    logger.debug("Checking if email already exists: %s", body.email)
    if db.query(Users).filter(Users.email == body.email).first():
        logger.warning("Email already in use: %s", body.email)
        raise HTTPException(status_code=409, detail="Email already in use")

    logger.debug("Validating password confirmation")
    # Ensure password and confirmation match (defensive, even though schema validates it)
    if body.password != body.confirm_password:
        logger.warning("Passwords do not match for email=%s", body.email)
        raise HTTPException(status_code=400, detail="Passwords do not match")

    u = Users(
        user_id=gen_public_id(),
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        phone_e164=body.phone_e164,
        role=role_row.key  # Direct role string instead of FK
    )
    db.add(u)
    db.flush()
    logger.info("User created with id=%s, user_id=%s", u.id, u.user_id)

    creds = UserCredential(
        user_id=u.id,
        password_hash=hash_password(body.password),
        last_password_change=datetime.utcnow()
    )
    db.add(creds)

    ver = EmailVerification(
        user_id=u.id,
        token=gen_token_hex(32),
        expires_at=datetime.utcnow() + timedelta(days=2)
    )
    db.add(ver)

    refresh = gen_token_hex(32)
    sess = SessionToken(
        user_id=u.id,
        refresh_token=refresh,
        user_agent=request.headers.get("user-agent"),
        ip_addr=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TTL_DAYS)
    )
    db.add(sess)
    db.commit()

    # Send verification email after commit (so token is saved)
    from src.email_service import get_email_service
    email_service = get_email_service()
    user_name = f"{u.first_name} {u.last_name}"
    email_service.send_email_verification(
        to_email=u.email,
        verification_token=ver.token,
        user_name=user_name
    )
    logger.info("Registration committed for user id=%s", u.id)
    db.refresh(u)

    access = make_access_token(u.user_id, u.id, u.email)
    logger.info("Registration successful for user email=%s", body.email)
    # Build role dict for response
    if u.role:
        role_out = {"key": u.role, "name": get_role_display_name(u.role)}
    else:
        role_out = None

    return AuthOut(
        user=UserOut(
            public_id=u.user_id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            phone_e164=u.phone_e164,
            role=role_out,
            is_email_verified=u.is_email_verified,
            onboarding_completed=u.onboarding_completed,
            plan_tier=u.plan_tier,
            created_at=u.created_at,
            updated_at=u.updated_at
        ),
        access_token=access,
        refresh_token=refresh,
        requires_email_verification=True
    )

@router.post(
    "/login",
    response_model=AuthOut,
    responses={
        200: {"description": "Login successful"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized - Invalid email or password"},
        422: {"description": "Unprocessable Entity - Validation error"},
        500: {"description": "Internal Server Error"}
    },
    openapi_extra={"security": []}
)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    logger.info("Login attempt for email=%s", body.email)
    logger.debug("Handling /login request body: %s", body.dict(exclude={'password'}))
    u = db.query(Users).filter(Users.email == body.email, Users.status == "active").one_or_none()
    if not u or not u.creds or not verify_password(body.password, u.creds.password_hash):
        logger.warning("Invalid login attempt for email=%s", body.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    refresh = gen_token_hex(32)
    sess = SessionToken(
        user_id=u.id,
        refresh_token=refresh,
        user_agent=request.headers.get("user-agent"),
        ip_addr=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TTL_DAYS)
    )
    db.add(sess)
    db.commit()
    logger.info("Login successful for user id=%s", u.id)

    logger.info("Login completed successfully for email=%s", body.email)
    # Build role dict for response
    if u.role:
        role_out = {"key": u.role, "name": get_role_display_name(u.role)}
    else:
        role_out = None

    return AuthOut(
        user=UserOut(
            public_id=u.user_id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            phone_e164=u.phone_e164,
            role=role_out,
            is_email_verified=u.is_email_verified,
            onboarding_completed=u.onboarding_completed,
            plan_tier=u.plan_tier,
            created_at=u.created_at,
            updated_at=u.updated_at
        ),
        access_token=make_access_token(u.user_id, u.id, u.email),
        refresh_token=refresh,
        requires_email_verification=not u.is_email_verified
    )


def _parse_org_id(input_id: Optional[str]) -> OrgLookupOut:
    if not input_id:
        return OrgLookupOut(is_existing=False, existing_active=False, tier=None, org_type=None, no_pay=False)
    v = input_id.strip().upper()
    logger.debug("[_parse_org_id] raw=%s parsed=%s", _redact(input_id, keep=6), v)
    is_existing = v.startswith("B-") or v.startswith("C-")
    org_type = "builder" if v.startswith("B-") else ("community" if v.startswith("C-") else None)
    existing_active = ("ACTIVE" in v) and ("NOPAY" not in v)
    no_pay = ("NOPAY" in v)
    tier: Optional[str] = None
    if existing_active:
        if "PRO" in v:
            tier = "pro"
        elif "ENT" in v or "ENTERPRISE" in v:
            tier = "enterprise"
        else:
            tier = "free"
    return OrgLookupOut(
        is_existing=is_existing,
        existing_active=existing_active,
        tier=tier,
        org_type=org_type,
        no_pay=no_pay,
    )

def _plan_label(plan: Optional[str]) -> Optional[str]:
    mapping = {
        "userFree": "User • Free",
        "builderFree": "Builder • Free",
        "builderPro": "Builder • Pro $159.99/mo",
        "builderEnterprise": "Builder • Enterprise",
        "communityFree": "Community • Free",
        "communityEnterprise": "Community • Enterprise",
        "existingActive": "Existing organization • Active tier",
        "salesRep": "Sales Rep • Verify Builder ID",
        "communityAdminVerify": "Community Admin • Verify Community ID",
    }
    return mapping.get(plan) if plan else None

def _resolve_role(db: Session, role_key: str) -> Role:
    preferred_keys = {
        "buyer": ["buyer"],
        "builder": ["builder"],
        "community": ["community"],
        "community_admin": ["community_admin"],
        "salesrep": ["salesrep"],
        "admin": ["admin"],
    }
    for key in preferred_keys.get(role_key, [role_key]):
        r = db.query(Role).filter(Role.key == key).one_or_none()
        if r:
            return r
    r_any = db.query(Role).first()
    if not r_any:
        raise HTTPException(status_code=500, detail="No roles are seeded.")
    return r_any

@router.get("/role/org-lookup", response_model=OrgLookupOut, openapi_extra={"security": []})
def org_lookup(id: str):
    """Parse an org ID from the client (e.g., B-ACTIVE-PRO-4123) and return status."""
    try:
        logger.debug("[org_lookup] query id=%s", _redact(id, keep=6))
        result = _parse_org_id(id)
        logger.info("[org_lookup] parsed: existing=%s active=%s tier=%s type=%s no_pay=%s",
                    result.is_existing, result.existing_active, result.tier, result.org_type, result.no_pay)
        return result
    except Exception as exc:
        logger.exception("[org_lookup] unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/role/selection/preview", response_model=RoleSelectionOut, openapi_extra={"security": []})
def role_selection_preview(body: RoleSelectionIn, db: Session = Depends(get_db)):
    """
    Validates the user's selection from the Role/Tier UI and tells the app the next step.
    It does not persist anything—use /role/selection/commit to save.
    """
    try:
        logger.debug("[role_selection_preview] in: user=%s role=%s plan=%s org_id=%s",
                     getattr(body, 'user_public_id', None), getattr(body, 'role', None),
                     getattr(body, 'selected_plan', None), _redact(body.org_id, keep=6))
        parsed = _parse_org_id(body.org_id)
        messages: List[str] = []

        if body.role == "buyer":
            plan = "userFree"
            next_step = "finish"
            requires_payment = False
            messages.append("Buyer accounts are free. You can finish onboarding.")
        elif body.role == "builder":
            plan = body.selected_plan
            if plan in (None, "existingActive") and parsed.existing_active:
                plan = "existingActive"
                next_step = "finish"
                requires_payment = False
                messages.append("Builder organization already active. No payment required.")
            elif plan == "salesRep":
                next_step = "await_verification"
                requires_payment = False
                if not body.org_id:
                    messages.append("Enter a Builder ID so our team can verify.")
                else:
                    messages.append("Sales will verify the Builder ID you provided.")
            elif plan in ("builderFree",):
                next_step = "finish"
                requires_payment = False
            elif plan in ("builderPro", "builderEnterprise"):
                next_step = "checkout"
                requires_payment = True
            else:
                raise HTTPException(status_code=422, detail="Invalid builder plan selection.")
        elif body.role == "community":
            plan = body.selected_plan
            if plan in (None, "existingActive") and parsed.existing_active:
                plan = "existingActive"
                next_step = "finish"
                requires_payment = False
                messages.append("Community organization already active. No payment required.")
            elif plan == "communityAdminVerify":
                next_step = "await_verification"
                requires_payment = False
                if not body.org_id:
                    messages.append("Enter a Community ID so our team can verify.")
                else:
                    messages.append("Our team will verify the Community ID you provided.")
            elif plan in ("communityFree",):
                next_step = "finish"
                requires_payment = False
            elif plan in ("communityEnterprise",):
                next_step = "checkout"
                requires_payment = True
            else:
                raise HTTPException(status_code=422, detail="Invalid community plan selection.")
        elif body.role == "community_admin":
            # Admins must be tied to an existing community; treat as verification flow
            plan = "communityAdminVerify"
            next_step = "await_verification"
            requires_payment = False
            if not body.org_id:
                messages.append("Enter a Community ID so our team can verify.")
            else:
                messages.append("We will verify the Community ID you provided.")
        elif body.role == "salesrep":
            plan = "salesRep"
            next_step = "await_verification"
            requires_payment = False
            if not body.org_id:
                messages.append("Enter a Builder ID so our team can verify.")
            else:
                messages.append("Sales will verify the Builder ID you provided.")
        else:
            raise HTTPException(status_code=422, detail="Unknown role.")

        # Load the user for the response
        u = db.query(Users).filter(Users.user_id == body.user_public_id).one_or_none()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info("[role_selection_preview] out: user=%s role=%s next_step=%s requires_payment=%s",
                    u.user_id, body.role, next_step, requires_payment)
        return RoleSelectionOut(
            user=UserOut(
                public_id=u.user_id,
                first_name=u.first_name,
                last_name=u.last_name,
                email=u.email,
                is_email_verified=u.is_email_verified,
                created_at=u.created_at,
            ),
            role=body.role,
            plan_label=_plan_label(plan),
            requires_payment=requires_payment,
            next_step=next_step,  # finish | checkout | await_verification
            messages=messages,
            parsed_org=OrgParseOut(**parsed.model_dump()) if parsed is not None else None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[role_selection_preview] unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/role/selection/commit", response_model=RoleSelectionOut)
def role_selection_commit(
    body: RoleSelectionIn,
    db: Session = Depends(get_db),
    current_user: Users = Depends(require_user),
):
    """
    Persist the chosen role (maps to Role) and then return the same structure as
    the preview endpoint. We allow an optional public_id in the body; if present
    it must match the authenticated user to prevent spoofing. When omitted, we
    fall back to the JWT user.
    """
    logger.debug(
        "[role_selection_commit] in: user=%s role=%s org_id=%s plan=%s",
        getattr(body, "user_public_id", None),
        getattr(body, "role", None),
        _redact(body.org_id, keep=6),
        getattr(body, "selected_plan", None),
    )

    # Determine target user via public_id (if provided) or authenticated user
    requested_pub = body.user_public_id or current_user.user_id

    # Security: if client supplied a public_id, it must match the authenticated user
    if body.user_public_id is not None and requested_pub != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: user mismatch")

    # Load active user
    u = (
        db.query(Users)
        .filter(Users.user_id == requested_pub, Users.status == "active")
        .one_or_none()
    )
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # Resolve role by key and persist
    r = _resolve_role(db, body.role)
    u.role = r.key  # Direct role string instead of FK

    # Optional: persist selected plan tier if present (map UI keys to DB tiers)
    if getattr(body, "selected_plan", None):
        plan_map = {
            "userFree": "free",
            "builderFree": "free",
            "builderPro": "pro",
            "builderEnterprise": "enterprise",
            "communityFree": "free",
            "communityEnterprise": "enterprise",
            "existingActive": "free",
            "salesRep": "free",
            "communityAdminVerify": "free",
        }
        mapped = plan_map.get(body.selected_plan, body.selected_plan)
        # Only set if we resolved something sensible
        if mapped:
            u.plan_tier = mapped

    db.add(u)
    db.commit()
    db.refresh(u)

    logger.info("[role_selection_commit] persisted role=%s for user=%s", r.key, u.user_id)

    # Call preview with a fresh payload (avoid mutating the incoming model)
    preview_body = RoleSelectionIn(
        user_public_id=u.user_id,
        role=body.role,
        org_id=body.org_id,
        selected_plan=body.selected_plan,
    )
    preview = role_selection_preview(preview_body, db)
    logger.info("[role_selection_commit] next_step=%s", preview.next_step)
    return preview



# Generalized role form builder for all roles
def _build_role_form(data: dict) -> RoleForm:
    role = data.get("role")
    if role == "buyer":
        return BuyerForm(**data)
    elif role == "builder":
        return BuilderForm(**data)
    elif role == "community":
        return CommunityForm(**data)
    elif role == "community_admin":
        return CommunityAdminForm(**data)
    elif role == "salesrep":
        return SalesRepForm(**data)
    # Fallback to the base union if needed
    return RoleForm(**data)

def _normalize_role_form_payload(raw: dict) -> RoleForm:
    """
    Accept either shape:
      A) Flat payload:
         { "role": "buyer", "user_public_id": "...", ...role fields... }
      B) Nested payload:
         { "role": "buyer", "user_public_id": "...", "buyer": { ...role fields... } }
    We flatten (B) into (A) by merging the nested block whose key matches the role.
    """
    role = raw.get("role")
    if not role:
        raise HTTPException(status_code=422, detail="Missing 'role' discriminator")
    if role not in {"buyer", "builder", "community", "community_admin", "salesrep"}:
        raise HTTPException(status_code=422, detail=f"Unsupported role: {role}")
    if role and isinstance(raw.get(role), dict):
        nested = raw[role]
        merged = {**raw, **nested}
        merged.pop(role, None)
        # Backfill from nested.public_id -> user_public_id / public_id
        if not merged.get("user_public_id") and nested.get("public_id"):
            merged["user_public_id"] = nested["public_id"]
        if not merged.get("public_id") and nested.get("public_id"):
            merged["public_id"] = nested["public_id"]
        # Backfill from top-level user_public_id -> public_id (BuyerForm expects public_id)
        if not merged.get("public_id") and merged.get("user_public_id"):
            merged["public_id"] = merged["user_public_id"]
        return _build_role_form(merged)
    # Already flat: ensure Buyer-compatible IDs if client sent user_public_id only
    flat = dict(raw)
    if role == "buyer":
        if not flat.get("public_id") and flat.get("user_public_id"):
            flat["public_id"] = flat["user_public_id"]
    return _build_role_form(flat)

# =============================
# Step 3: Role-Based Form (Preview & Commit)
# =============================


def _validate_role_form(form: RoleForm) -> FormPreviewOut:
    missing: Dict[str, str] = {}
    suggestions: List[str] = []

    if isinstance(form, BuilderForm):
        if not form.company_name.strip():
            missing["company_name"] = "Company name is required"
        suggestions.append("Company name appears on your public Builder profile.")
        next_step: Literal["finish", "await_verification", "review"] = "finish"
        return FormPreviewOut(role=form.role, valid=(len(missing) == 0), missing=missing, suggestions=suggestions, next_step=next_step)

    if isinstance(form, CommunityForm):
        if not form.community_name.strip():
            missing["community_name"] = "Community name is required"
        if not form.city.strip():
            missing["city"] = "City is required"
        if not form.state.strip():
            missing["state"] = "State is required"
        suggestions.append("We verify new Communities before publishing.")
        next_step = "review" if missing else "finish"
        return FormPreviewOut(role=form.role, valid=(len(missing) == 0), missing=missing, suggestions=suggestions, next_step=next_step)

    if isinstance(form, CommunityAdminForm):
        if not form.first_name.strip():
            missing["first_name"] = "First name is required"
        if not form.last_name.strip():
            missing["last_name"] = "Last name is required"
        if not form.community_link.strip():
            missing["community_link"] = "Link to an existing Community is required"
        suggestions.append("Admin accounts must be tied to an existing Community.")
        next_step = "await_verification" if not missing else "review"
        return FormPreviewOut(role=form.role, valid=(len(missing) == 0), missing=missing, suggestions=suggestions, next_step=next_step)

    if isinstance(form, SalesRepForm):
        # License is optional but if provided should be at least 4 chars (matches UI)
        if form.license_id and len(form.license_id) < 4:
            missing["license_id"] = "License ID must be at least 4 characters if provided"
        suggestions.append("Provide license/brokerage to boost trust on your profile (optional).")
        next_step = "finish" if not missing else "review"
        return FormPreviewOut(role=form.role, valid=(len(missing) == 0), missing=missing, suggestions=suggestions, next_step=next_step)

    if isinstance(form, BuyerForm):
        required = [
            (form.first_name, "first_name"),
            (form.last_name, "last_name"),
            (form.email, "email"),
            (form.phone, "phone"),
            (form.address, "address"),
            (form.city, "city"),
            (form.state, "state"),
        ]
        for value, fieldname in required:
            if not str(value).strip():
                missing[fieldname] = f"{fieldname.replace('_',' ').title()} is required"
        suggestions.append("Preferences help personalize recommendations and can be added later.")
        next_step = "finish" if not missing else "review"
        return FormPreviewOut(role=form.role, valid=(len(missing) == 0), missing=missing, suggestions=suggestions, next_step=next_step)

    # Fallback (should never hit with a correct discriminator)
    return FormPreviewOut(role="unknown", valid=False, missing={"role": "Unsupported role"}, suggestions=[], next_step="review")


@router.post("/role/form/preview", response_model=FormPreviewOut, openapi_extra={"security": []})
def role_form_preview(body: dict = Body(...)):
    """Validate role-based form fields from step 3 and advise next action."""
    try:
        # Normalize incoming body (supports nested 'buyer' or top-level fields)
        form = _normalize_role_form_payload(body)
        logger.debug("[role_form_preview] in: user=%s role=%s",
                     getattr(form, 'user_public_id', None), getattr(form, 'role', None))
        out = _validate_role_form(form)
        logger.info("[role_form_preview] out: role=%s valid=%s next_step=%s missing=%d",
                    out.role, out.valid, out.next_step, len(out.missing))
        return out
    except HTTPException:
        raise
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception:
        logger.exception("[role_form_preview] unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/role/form/commit", response_model=FormCommitOut)
def role_form_commit(body: dict = Body(...), db: Session = Depends(get_db)):
    """
    Persist role-based form fields. For now we stage data for later processors:
    - If tables like builder_profiles/community_profiles exist, this can be extended to insert rows.
    - Current implementation is non-destructive and only ensures the user exists.
    """
    try:
        # Normalize incoming body (supports nested 'buyer' or top-level fields)
        form = _normalize_role_form_payload(body)
        # Prefer user_public_id, but fall back to public_id for legacy schemas
        uid = getattr(form, "user_public_id", None) or getattr(form, "public_id", None)
        logger.debug("[role_form_commit] in: user=%s role=%s", uid, getattr(form, 'role', None))
        if not uid:
            raise HTTPException(status_code=422, detail={"missing": {"user_public_id": "User public_id is required"}})
        u = db.query(Users).filter(Users.user_id == uid).one_or_none()
        if not u:
            logger.warning("[role_form_commit] user not found: %s", form.user_public_id)
            raise HTTPException(status_code=404, detail="User not found")
        preview = _validate_role_form(form)
        if not preview.valid:
            logger.warning("[role_form_commit] validation failed: missing=%s", list(preview.missing.keys()))
            raise HTTPException(status_code=422, detail={"missing": preview.missing})
        messages: List[str] = []
        if isinstance(form, BuilderForm):
            messages.append("Builder details received. Pending profile creation (builder_profiles).")
        elif isinstance(form, CommunityForm):
            messages.append("Community details received. Pending verification & profile creation (community_profiles).")
        elif isinstance(form, CommunityAdminForm):
            messages.append("Admin details received. Verification will be required before admin privileges are active.")
        elif isinstance(form, SalesRepForm):
            messages.append("Sales Rep details received. Optional license/brokerage stored.")
        elif isinstance(form, BuyerForm):
            messages.append("Buyer details received. Preferences will power recommendations.")
            # Persist/Upsert BuyerProfile from submitted form
            # 1) Update core user fields (keep existing if client sent blanks)
            if getattr(form, "first_name", None) and str(form.first_name).strip():
                u.first_name = str(form.first_name).strip()
            if getattr(form, "last_name", None) and str(form.last_name).strip():
                u.last_name = str(form.last_name).strip()
            if getattr(form, "email", None) and str(form.email).strip():
                u.email = str(form.email).strip()
            if getattr(form, "phone", None) and str(form.phone).strip():
                # Store raw in users.phone_e164 for now; upstream can normalize
                u.phone_e164 = str(form.phone).strip()
            db.add(u)

            # 2) Find or create BuyerProfile keyed by user's user_id string
            prof = (
                db.query(BuyerProfile)
                .filter(BuyerProfile.user_id == u.user_id)
                .one_or_none()
            )
            display_name = f"{u.first_name or ''} {u.last_name or ''}".strip()

            if prof is None:
                prof = BuyerProfile(
                    user_id=u.user_id,  # STRING FK to users.user_id
                    display_name=display_name or None,
                )

            # 3) Push contact + basic presentation fields
            prof.display_name = display_name or prof.display_name

            # Populate BOTH legacy and canonical fields
            email_val = (str(form.email).strip() or None) if getattr(form, "email", None) else None
            phone_val = (str(form.phone).strip() or None) if getattr(form, "phone", None) else None

            if email_val:
                prof.email = email_val
                prof.contact_email = email_val
            if phone_val:
                prof.phone = phone_val
                prof.contact_phone = phone_val

            # Copy name fields to BuyerProfile
            if u.first_name:
                prof.first_name = u.first_name
            if u.last_name:
                prof.last_name = u.last_name

            # Populate address fields from form into dedicated columns
            if getattr(form, "address", None) and str(form.address).strip():
                prof.address = str(form.address).strip()
            if getattr(form, "zip_code", None) and str(form.zip_code).strip():
                prof.zip_code = str(form.zip_code).strip()

            # location: "City, State" when available (also store in dedicated columns)
            city_val = str(form.city).strip() if getattr(form, "city", None) else ""
            state_val = str(form.state).strip() if getattr(form, "state", None) else ""

            # Store in dedicated columns
            if city_val:
                prof.city = city_val
            if state_val:
                prof.state = state_val

            # Also create combined location string for display
            loc = ", ".join([s for s in (city_val, state_val) if s])
            prof.location = loc or prof.location

            # 3b) Optional enum-backed fields with safe normalization
            # timeline (e.g., "3-6 months") -> BuyTimelineEnum
            if getattr(form, "buying_timeline", None):
                val = str(form.buying_timeline).strip().lower()
                # Simple normalization; adjust these to match your Enum values
                TMAP = {
                    "asap": "asap",
                    "0-3 months": "soon",
                    "3-6 months": "three_to_six",
                    "6-12 months": "six_to_twelve",
                    "12+ months": "later",
                    "exploring": "exploring",
                }
                mapped = TMAP.get(val, None)
                if mapped:
                    try:
                        prof.timeline = mapped  # assumes DB Enum names match strings above
                    except Exception:
                        pass  # ignore invalid enum assignment

            # financing_status (e.g., "Pre-approved", "Prequalified", "Unknown")
            if getattr(form, "financing_status", None):
                val = str(form.financing_status).strip().lower().replace(" ", "_")
                FMAP = {
                    "unknown": "unknown",
                    "pre_approved": "pre_approved",
                    "preapproved": "pre_approved",
                    "prequalified": "prequalified",
                    "no_financing": "no_financing",
                }
                mapped = FMAP.get(val, None)
                if mapped:
                    try:
                        prof.financing_status = mapped
                    except Exception:
                        pass

            # loan_program (free text or known set)
            if getattr(form, "loan_program", None):
                lp = str(form.loan_program).strip()
                if lp:
                    prof.loan_program = lp

            # preferred contact channel (e.g., "Email", "Phone", "SMS")
            if getattr(form, "preferred_channel", None):
                val = str(form.preferred_channel).strip().lower()
                CMAP = {
                    "email": "email",
                    "phone": "phone",
                    "sms": "sms",
                    "text": "sms",
                }
                mapped = CMAP.get(val, None)
                if mapped:
                    try:
                        prof.contact_preferred = mapped
                    except Exception:
                        pass

            # 4) Preserve additional submitted fields in `extra` for future structured mapping
            # Note: address, city, state, zip_code now use dedicated columns
            extra = dict(prof.extra or {})
            for key in [
                "income_range", "household_income",
                "first_time", "first_time_home_buyer", "home_type",
                "budget_min", "budget_max",
                "location_interest", "builder_interest", "sex",
                "buying_timeline", "preferred_channel"
            ]:
                if hasattr(form, key):
                    val = getattr(form, key)
                    if val is not None and str(val).strip() != "":
                        extra[key] = val
            prof.extra = extra

            db.add(prof)
        next_step: Literal["finish", "await_verification"] = "finish"
        if isinstance(form, CommunityAdminForm):
            next_step = "await_verification"
        db.commit()
        logger.info("[role_form_commit] out: user=%s role=%s next_step=%s messages=%d",
                    u.user_id, preview.role, next_step, len(messages))
        return FormCommitOut(role=preview.role, saved=True, messages=messages, next_step=next_step)
    except HTTPException:
        raise
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception:
        logger.exception("[role_form_commit] unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")