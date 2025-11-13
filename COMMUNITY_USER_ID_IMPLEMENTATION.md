# Community user_id Implementation Summary

## Overview
Added `user_id` foreign key to the `communities` table to track community ownership/creator.

---

## ✅ Completed Changes

### 1. Database Schema (Migration)
**File:** `alembic/versions/g3h4i5j6k7l8_add_user_id_to_communities.py`

- Added `user_id` INTEGER column to `communities` table
- Created foreign key constraint: `fk_communities_user_id` → `users.id`
- Added index: `ix_communities_user_id` for performance
- Column is nullable to avoid breaking existing communities
- FK uses `ON DELETE SET NULL` to preserve communities when user is deleted

**Migration Status:** ✅ Successfully executed

```bash
# Run migration
alembic upgrade head
```

---

### 2. SQLAlchemy Model
**File:** `model/profiles/community.py:27`

```python
class Community(Base):
    __tablename__ = "communities"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    public_id = Column(String(64), unique=True, nullable=False)

    # Owner/Creator of community
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # ... other fields

    # Relationships
    owner = relationship("Users", foreign_keys=[user_id], lazy="joined")
```

**Changes:**
- Added `user_id` column (INTEGER, nullable, indexed)
- Added `owner` relationship to Users model with eager loading

---

### 3. Pydantic Schema
**File:** `schema/community.py:309`

```python
class CommunityOut(CommunityBase):
    id: int
    public_id: str
    user_id: Optional[int] = None  # FK to users.id (owner/creator)

    created_at: datetime
    updated_at: datetime

    # ... nested relationships
```

**Changes:**
- Added `user_id: Optional[int]` field to response schema
- Field is optional to handle existing communities without owners

---

### 4. API Response
**Affected Endpoints:**

All community endpoints automatically return `user_id` field:

- `GET /v1/profiles/communities/` - List all communities
- `GET /v1/profiles/communities/{community_id}` - Get specific community
- `GET /v1/profiles/communities/for-user/{user_id}` - Get community for user
- `POST /v1/profiles/communities/` - Create community
- `PUT /v1/profiles/communities/{community_id}` - Update community (full)
- `PATCH /v1/profiles/communities/{community_id}` - Update community (partial)

**Example Response:**
```json
{
  "id": 1,
  "public_id": "CMY-1763002155-ABC123",
  "user_id": 42,
  "name": "The Highlands",
  "city": "Houston",
  "state": "TX",
  "followers": 150,
  "is_verified": true,
  "homes": 500,
  "residents": 1200,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-03-20T14:45:00Z"
}
```

---

### 5. iOS/SwiftUI Model
**File:** `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md` (Section 3)

```swift
struct Community: Codable, Identifiable {
    // NEW: String ID
    let id: String  // e.g., "CMY-1699564234-Z5R7N4"

    // Owner/Creator reference
    var userId: Int?  // FK to users.id (owner of the community)

    var name: String
    var city: String?
    // ... other fields

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"  // Maps to backend's user_id field
        case name
        case city
        // ... other keys
    }
}
```

**Changes:**
- Added `userId: Int?` property to Community struct
- Added `userId = "user_id"` to CodingKeys enum
- Field is optional to handle communities without assigned owners

---

## 🔧 Database Type Resolution

### Issue Encountered
Initial migration used `BIGINT(unsigned=True)` for `user_id`, but `users.id` is `INTEGER`.
MySQL FK constraint requires matching types.

### Resolution
- Updated migration to use `sa.Integer()` to match `users.id` type
- Added type-checking logic to migration to convert existing BIGINT columns to INT
- Migration now safely handles both fresh installs and failed previous attempts

---

## 📋 Pending Tasks

### 1. Update The Highlands Community Record
Once MySQL is running, set the `user_id` for The Highlands community:

**Option A: Via Admin API Endpoint**
```bash
POST http://localhost:8000/admin/connect-user-to-community
  ?user_public_id=USR-1763002155-GRZVLL
  &community_name=The Highlands
```

**Option B: Direct SQL**
```sql
-- Find user's integer ID
SELECT id, public_id, email, first_name, last_name
FROM users
WHERE public_id = 'USR-1763002155-GRZVLL';

-- Update The Highlands (replace 42 with actual user.id from above)
UPDATE communities
SET user_id = 42
WHERE name LIKE '%Highlands%';
```

### 2. iOS/SwiftUI Implementation
Developer needs to update their iOS project:

1. Copy Community model from `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md`
2. Replace existing `Models/Community.swift` with updated version
3. Update any views that display community owner information
4. Test API integration

---

## 🔄 Data Relationships

```
User (users table)
  ├─ id: INTEGER (primary key)
  ├─ public_id: STRING ("USR-xxx")
  └─ owned_communities: [Community] (via Community.user_id FK)

Community (communities table)
  ├─ id: BIGINT UNSIGNED (primary key)
  ├─ public_id: STRING ("CMY-xxx")
  ├─ user_id: INTEGER (FK → users.id, nullable)
  └─ owner: User (relationship, lazy="joined")
```

---

## 🧪 Testing

### Backend Tests
```bash
# Test API response includes user_id
curl http://localhost:8000/api/v1/profiles/communities/1

# Test community for user endpoint
curl http://localhost:8000/api/v1/profiles/communities/for-user/USR-1763002155-GRZVLL
```

### Expected Behavior
- ✅ All community API responses include `user_id` field
- ✅ `user_id` is `null` for existing communities without owners
- ✅ `user_id` is populated for new communities created with owner
- ✅ Deleting a user sets community's `user_id` to NULL (doesn't delete community)
- ✅ Can query communities by owner using `user_id` filter

---

## 📝 Notes

### Design Decisions

1. **Nullable user_id**: Allows existing communities without owners, avoiding breaking changes
2. **ON DELETE SET NULL**: Preserves community data if owner account is deleted
3. **INTEGER vs BIGINT**: Follows existing `users.id` type for FK compatibility
4. **Lazy="joined"**: Eager loads owner relationship for better performance
5. **Index on user_id**: Optimizes queries filtering by owner

### Future Enhancements

- Add endpoint to transfer community ownership
- Add permission checks based on community ownership
- Add owner information to community detail views
- Track ownership history (audit table)

---

## 🎯 Key Files Modified

1. ✅ `alembic/versions/g3h4i5j6k7l8_add_user_id_to_communities.py` - Migration
2. ✅ `model/profiles/community.py` - SQLAlchemy model
3. ✅ `schema/community.py` - Pydantic schema
4. ✅ `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md` - iOS model documentation

---

## 🔗 Related Documentation

- [Public ID Implementation](./PUBLIC_ID_IMPLEMENTATION_SUMMARY.md)
- [Community Admin Profile Setup](./docs/COMMUNITY_ADMIN_PROFILE_SETUP.md)
- [SwiftUI Implementation Guide](./docs/SWIFTUI_IMPLEMENTATION_GUIDE.md)
- [The Highlands Community Setup](./COMPLETED_THE_HIGHLANDS_SETUP.md)

---

**Status:** ✅ Backend Complete, ⏳ Pending The Highlands Update + iOS Implementation

**Date:** 2024-11-12
