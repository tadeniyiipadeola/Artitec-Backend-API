# Builder Profile Route Fix Required

## Problem

The builder profile routes in `routes/profiles/builder.py` are using `org_id` as the path parameter and model field, but:
- The BuilderProfile **model** (`model/profiles/builder.py`) has `user_id` (FK to users.id), NOT `org_id`
- All routes trying to filter by `BuilderModel.org_id` will fail because that column doesn't exist

## Solution

Update `routes/profiles/builder.py` to follow the **buyer profile pattern** from `routes/profiles/buyers.py`:

###  1. Helper Function Pattern

```python
def _ensure_user(db: Session, user_id: str):
    """Resolve public_id (string) to Users model instance"""
    user = db.query(Users).filter(Users.public_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 2. Create Route Pattern

```python
@router.post("/{user_id}", response_model=BuilderProfileOut, status_code=status.HTTP_201_CREATED)
def create_builder_profile(user_id: str, payload: BuilderProfileCreate, db: Session = Depends(get_db)):
    # user_id parameter is actually public_id (string UUID)
    user = _ensure_user(db, user_id)
    uid = int(user.id)  # Get numeric ID

    # Check if builder profile already exists
    existing = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Builder profile already exists")

    # Create builder profile
    data = payload.model_dump(exclude_none=True)
    obj = BuilderModel(**data, user_id=uid)  # Set user_id from resolved user
    db.add(obj)

    # Mark onboarding complete
    user.onboarding_completed = True

    db.commit()
    db.refresh(obj)
    return BuilderProfileOut.model_validate(obj)
```

### 3. Get Route Pattern

```python
@router.get("/{user_id}", response_model=BuilderProfileOut)
def get_builder_profile(user_id: str, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    obj = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Builder profile not found")

    return BuilderProfileOut.model_validate(obj)
```

### 4. Update Route Pattern

```python
@router.patch("/{user_id}", response_model=BuilderProfileOut)
def update_builder_profile(user_id: str, payload: BuilderProfileUpdate, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    obj = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Builder profile not found")

    data = payload.model_dump(exclude_none=True)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)

    db.commit()
    db.refresh(obj)
    return BuilderProfileOut.model_validate(obj)
```

### 5. Delete Route Pattern

```python
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_builder_profile(user_id: str, db: Session = Depends(get_db)):
    user = _ensure_user(db, user_id)
    uid = int(user.id)

    obj = db.query(BuilderModel).filter(BuilderModel.user_id == uid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Builder profile not found")

    db.delete(obj)
    db.commit()
    return None
```

## Summary of Changes

| Current (Broken) | Fixed |
|-----------------|-------|
| `/{org_id}` path parameter | `/{user_id}` path parameter (actually public_id string) |
| `BuilderModel.org_id` filter | `BuilderModel.user_id` filter |
| `payload.org_id` | Route resolves user_id from path parameter |
| Direct org_id usage | Use `_ensure_user()` helper to resolve public_id → user.id |

## iOS Integration

The iOS app now:
- POSTs to `/v1/profiles/builders/{public_id}` with BuilderProfileCreate payload
- BuilderProfileCreate does NOT include user_id (route provides it)
- Follows same pattern as buyer profile creation

## Schema Updates

The builder_profiles table now includes broken down address fields:
- `address` - Street address (VARCHAR 255)
- `city` - City name (VARCHAR 255)
- `state` - State code (VARCHAR 64)
- `postal_code` - ZIP/postal code (VARCHAR 20)

Migration: `922b25005b74_add_location_fields_to_builder_profiles.py`

## Testing

```bash
# Create builder profile
curl -X POST http://localhost:8000/v1/profiles/builders/USER_PUBLIC_ID_HERE \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_HERE" \
  -d '{
    "name": "Test Builder Co",
    "website": "https://example.com",
    "phone": "555-1234",
    "email": "info@testbuilder.com",
    "address": "123 Main St",
    "city": "Houston",
    "state": "TX",
    "postal_code": "77339",
    "about": "We build custom homes in the Houston area"
  }'
```

Expected: 201 Created with BuilderProfileOut response
