# Implementation Steps: Public ID Migration
## Backend & SwiftUI Complete Guide

This guide walks you through implementing the public ID system for both backend and iOS app.

---

## 🎯 Overview

**What's Changing:**
- User IDs: Already `USR-xxx`, now standardized format
- Buyer IDs: **NEW** `BYR-xxx` added
- Builder IDs: Renamed from `build_id` to `public_id`, format `BLD-xxx`
- Community IDs: Already exists, format standardized to `CMY-xxx`
- Community Admin IDs: **NEW** `ADM-xxx` added
- Sales Rep IDs: **NEW** `SLS-xxx` added

**Format:** `PREFIX-TIMESTAMP-RANDOM`
**Example:** `BYR-1699564234-A7K9M2`

---

## 📋 PART 1: Backend Implementation

### Step 1: Review What's Already Done ✅

The following files have been created/updated:
- ✅ `src/id_generator.py` - ID generation utilities
- ✅ `src/route_helpers.py` - Route lookup helpers
- ✅ `routes/profiles/buyers_updated.py` - Updated buyer routes
- ✅ `alembic/versions/e1f2g3h4i5j6_add_public_ids_to_all_profiles.py` - Migration
- ✅ `model/profiles/buyer.py` - Added `public_id` column
- ✅ `model/profiles/builder.py` - Renamed `build_id` to `public_id`
- ✅ `model/profiles/community_admin_profile.py` - Added `public_id`
- ✅ `model/profiles/sales_rep.py` - Added `public_id`
- ✅ `model/followers.py` - Fixed type mismatches
- ✅ `schema/buyers.py` - Updated to return `public_id` as `id`

### Step 2: Test ID Generator

```bash
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"

# Test the ID generator
python3 << 'EOF'
from src.id_generator import *

print("Testing ID Generation:")
print("=" * 50)
print(f"User ID:            {generate_user_id()}")
print(f"Buyer ID:           {generate_buyer_id()}")
print(f"Builder ID:         {generate_builder_id()}")
print(f"Community ID:       {generate_community_id()}")
print(f"Community Admin ID: {generate_community_admin_id()}")
print(f"Sales Rep ID:       {generate_sales_rep_id()}")

# Test parsing
buyer_id = generate_buyer_id()
parsed = parse_public_id(buyer_id)
print(f"\nParsed {buyer_id}:")
print(f"  Prefix:     {parsed['prefix']}")
print(f"  Timestamp:  {parsed['timestamp']}")
print(f"  Random:     {parsed['random']}")
print(f"  Type:       {parsed['resource_type']}")

# Test validation
print(f"\nValidation:")
print(f"  Valid BYR: {validate_public_id(buyer_id, 'BYR')}")
print(f"  Invalid (wrong prefix): {validate_public_id(buyer_id, 'USR')}")
EOF
```

**Expected output:**
```
Testing ID Generation:
==================================================
User ID:            USR-1731432567-A7K9M2
Buyer ID:           BYR-1731432567-X3P8Q1
Builder ID:         BLD-1731432567-Z5R7N4
Community ID:       CMY-1731432567-M2K9L3
Community Admin ID: ADM-1731432567-P7Q8R9
Sales Rep ID:       SLS-1731432567-S1T2U3

Parsed BYR-1731432567-X3P8Q1:
  Prefix:     BYR
  Timestamp:  1731432567
  Random:     X3P8Q1
  Type:       buyer

Validation:
  Valid BYR: True
  Invalid (wrong prefix): False
```

### Step 3: Review Migration (Don't Run Yet!)

```bash
# See what the migration will do (SQL preview)
alembic upgrade e1f2g3h4i5j6 --sql

# Check current migration status
alembic current

# See migration history
alembic history
```

### Step 4: Update Your Main Router

**File:** `src/app.py` (or wherever you register routes)

```python
from fastapi import FastAPI
from routes.profiles.buyers_updated import router as buyers_router
# Import other routers...

app = FastAPI()

# Register updated routes
app.include_router(buyers_router, tags=["Buyers"])
# app.include_router(builders_router, tags=["Builders"])
# app.include_router(communities_router, tags=["Communities"])
```

### Step 5: Replace Old Route File (When Ready)

```bash
# Backup old file
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
cp routes/profiles/buyers.py routes/profiles/buyers_BACKUP.py

# Replace with updated version
cp routes/profiles/buyers_updated.py routes/profiles/buyers.py

# Or keep both and gradually migrate
# Use buyers_updated.py as reference for updating other routes
```

### Step 6: Update Other Routes (Builder, Community, etc.)

Use `routes/profiles/buyers_updated.py` as a template:

**Pattern for Builder Routes:**
```python
from src.route_helpers import get_builder_by_public_id
from src.id_generator import generate_builder_id

# NEW: Direct resource access
@router.get("/builders/{builder_id}", response_model=BuilderProfileOut)
def get_builder(builder_id: str, db: Session = Depends(get_db)):
    builder = get_builder_by_public_id(db, builder_id)
    user = db.query(Users).filter(Users.id == builder.user_id).first()
    # Return response with public_id as id
    return {...}

# When creating:
builder = BuilderProfile(
    public_id=generate_builder_id(),  # NEW
    user_id=user.id,
    ...
)
```

### Step 7: Run Migration

**⚠️ IMPORTANT: Backup your database first!**

```bash
# Backup database
mysqldump -u user -p artitec > artitec_backup_$(date +%Y%m%d).sql

# Run migration
alembic upgrade e1f2g3h4i5j6

# Verify
alembic current
# Should show: e1f2g3h4i5j6 (head)
```

**Expected migration output:**
```
🔧 Starting public_id migration...

1️⃣  Updating users.public_id to new format (USR-TIMESTAMP-RANDOM)...
   ✅ Updated 10 user public_ids

2️⃣  Adding public_id to buyer_profiles...
   ✅ Added public_id to 5 buyer profiles

3️⃣  Updating builder_profiles.build_id to public_id with new format...
   ✅ Migrated 3 builder profiles from build_id to public_id

4️⃣  Adding public_id to community_admin_profiles...
   ✅ Added public_id to 2 community admin profiles

5️⃣  Adding public_id to sales_reps...
   ✅ Added public_id to 8 sales reps

6️⃣  Updating communities.public_id to new format (CMY-TIMESTAMP-RANDOM)...
   ✅ Updated 4 community public_ids

✨ Migration complete! All profiles now have typed public_ids
```

### Step 8: Test Backend Endpoints

```bash
# Assuming you have a buyer with new ID
BUYER_ID="BYR-1699564234-A7K9M2"

# Test GET buyer profile
curl -X GET "http://localhost:8000/api/v1/buyers/${BUYER_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test PATCH buyer profile
curl -X PATCH "http://localhost:8000/api/v1/buyers/${BUYER_ID}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "John Updated", "budget_max_usd": 600000}'

# Test GET tours
curl -X GET "http://localhost:8000/api/v1/buyers/${BUYER_ID}/tours" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📱 PART 2: SwiftUI/iOS Implementation

### Step 1: Update Models

**Location:** `YourApp/Models/`

Copy the model code from `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md`:

1. **BuyerProfile.swift** - Update `id` from `UUID` to `String`
2. **BuilderProfile.swift** - Update `id` from `UUID` to `String`
3. **Community.swift** - Update `id` from `UUID` to `String`

**Key Change:**
```swift
// Before
struct BuyerProfile: Codable, Identifiable {
    let id: UUID
    // ...
}

// After
struct BuyerProfile: Codable, Identifiable {
    let id: String  // "BYR-1699564234-A7K9M2"
    // ...
}
```

### Step 2: Update API Client

**Location:** `YourApp/Services/APIClient.swift`

Copy the API client code from the guide, or update your existing one:

```swift
class APIClient {
    // Change methods to use String IDs
    func getBuyer(buyerId: String) async throws -> BuyerProfile {
        // Uses new endpoint: /buyers/{buyerId}
    }

    func updateBuyer(buyerId: String, updates: BuyerProfileUpdate) async throws -> BuyerProfile {
        // Uses: PATCH /buyers/{buyerId}
    }
}
```

### Step 3: Update Views

**Find and replace across your project:**

```swift
// OLD: UUID parameter
struct BuyerProfileView: View {
    let buyerId: UUID
    // ...
}

// NEW: String parameter
struct BuyerProfileView: View {
    let buyerId: String  // e.g., "BYR-1699564234-A7K9M2"
    // ...
}
```

**Navigation updates:**
```swift
// Before
NavigationLink(destination: BuyerProfileView(buyerId: UUID(uuidString: id)!)) {
    Text("View Profile")
}

// After
NavigationLink(destination: BuyerProfileView(buyerId: buyer.id)) {
    Text("View Profile")
}
```

### Step 4: Update Persistence (if using)

**If using Core Data:**
```swift
// Update entity attribute type
// id: UUID -> id: String
```

**If using SwiftData:**
```swift
@Model
class CachedBuyer {
    @Attribute(.unique) var id: String  // Changed from UUID
    var displayName: String
    // ...
}
```

**If using UserDefaults:**
```swift
// Before
UserDefaults.standard.set(buyerId.uuidString, forKey: "current_buyer_id")

// After
UserDefaults.standard.set(buyerId, forKey: "current_buyer_id")  // Already a string
```

### Step 5: Update Tests

```swift
// Before
let testBuyer = BuyerProfile(
    id: UUID(),
    // ...
)

// After
let testBuyer = BuyerProfile(
    id: "BYR-1699564234-A7K9M2",
    // ...
)
```

### Step 6: Test iOS App

1. **Build and run** - Check for compilation errors
2. **Test profile loading** - Verify data displays correctly
3. **Test profile updates** - Verify PATCH requests work
4. **Test navigation** - Verify deep links work
5. **Test offline mode** - Verify cached data works

---

## 🔄 Rollback Plan

### If Backend Migration Fails:

```bash
# Rollback migration
alembic downgrade -1

# Or rollback to specific version
alembic downgrade d1e2f3g4h5i6

# Restore from backup if needed
mysql -u user -p artitec < artitec_backup_20251112.sql
```

### If iOS App Has Issues:

1. Revert model changes
2. Revert API client changes
3. Test with old endpoints
4. Deploy hotfix to TestFlight

---

## ✅ Verification Checklist

### Backend
- [ ] Migration runs without errors
- [ ] All profiles have `public_id` values
- [ ] GET `/buyers/{buyer_id}` returns correct data
- [ ] PATCH `/buyers/{buyer_id}` updates correctly
- [ ] Old user-based endpoints still work (backward compatibility)
- [ ] All tests pass
- [ ] API documentation updated

### iOS App
- [ ] Models compile without errors
- [ ] API client makes successful requests
- [ ] Profiles load and display correctly
- [ ] Navigation works with new IDs
- [ ] Updates save correctly
- [ ] No crashes in production
- [ ] TestFlight beta testing complete

---

## 📊 Monitoring

### Backend Metrics to Watch:
- Response times for new endpoints
- Error rates on public_id lookups
- Migration completion status
- Database query performance

### iOS Metrics to Watch:
- API call success rate
- Crash rate
- User session length
- Feature adoption

---

## 🆘 Troubleshooting

### Backend Issues

**Problem:** Migration fails with "column already exists"
```sql
-- Check if column exists
DESCRIBE buyer_profiles;

-- If public_id already exists, skip that table in migration
```

**Problem:** "Invalid ID format" errors
```python
# Check ID validation
from src.id_generator import validate_public_id
validate_public_id("BYR-1699564234-A7K9M2", "BYR")  # Should return True
```

**Problem:** 404 errors on new endpoints
```python
# Verify route is registered
from src.app import app
for route in app.routes:
    print(route.path)
# Should see /buyers/{buyer_id}
```

### iOS Issues

**Problem:** JSON decoding fails
```swift
// Check date decoding strategy
decoder.dateDecodingStrategy = .iso8601

// Enable verbose logging
print("Response data: \(String(data: data, encoding: .utf8) ?? "")")
```

**Problem:** IDs not displaying correctly
```swift
// Verify model coding keys
enum CodingKeys: String, CodingKey {
    case id  // Should map to "id" in JSON
    case userId = "user_id"  // Should map to "user_id"
}
```

---

## 📚 Additional Resources

- **Backend Guide:** `PUBLIC_ID_IMPLEMENTATION_SUMMARY.md`
- **SwiftUI Guide:** `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md`
- **Route Examples:** `routes/profiles/buyers_updated.py`
- **Migration File:** `alembic/versions/e1f2g3h4i5j6_add_public_ids_to_all_profiles.py`

---

## 🎉 Success Criteria

You'll know the implementation is successful when:

1. ✅ Backend migration completes without errors
2. ✅ All profiles have unique public_ids
3. ✅ New endpoints return data correctly
4. ✅ iOS app fetches and displays profiles
5. ✅ Updates save successfully
6. ✅ No regression in existing features
7. ✅ Performance is acceptable
8. ✅ Users can navigate between resources

---

## Next Steps After Implementation

1. **Update API documentation** (Swagger/OpenAPI)
2. **Monitor error logs** for first 48 hours
3. **Gather user feedback** from beta testers
4. **Optimize queries** if performance issues arise
5. **Plan deprecation** of legacy endpoints (6-12 months)
6. **Document lessons learned** for future migrations

---

**Questions or issues? Check the troubleshooting section or review the detailed guides.**

Good luck with the implementation! 🚀
