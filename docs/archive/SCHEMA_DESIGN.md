# Artitec Schema Design - User Profile Relationships

## Current State Analysis

### User Table Structure
```sql
users
  ├─ id (BIGINT UNSIGNED) - PRIMARY KEY - Internal database ID
  ├─ public_id (VARCHAR(50)) - UNIQUE - External API identifier
  ├─ email (VARCHAR(255))
  ├─ first_name, last_name
  ├─ role_id (FK → roles.id) - Determines profile type
  ├─ onboarding_completed (BOOLEAN)
  └─ ...
```

### Current Profile Tables

#### 1. BuyerProfile ✅ CORRECT
```sql
buyer_profiles
  ├─ id (BIGINT UNSIGNED) - PRIMARY KEY
  ├─ user_id (BIGINT UNSIGNED) - FK → users.id ✅
  │    UNIQUE, NOT NULL, CASCADE DELETE
  ├─ display_name, location, bio...
  └─ financing info, preferences...
```
**Status:** ✅ Properly structured
- One-to-one with User via users.id
- Correct data type (BIGINT)
- Cascade delete on user deletion

---

#### 2. BuilderProfile ❌ INCORRECT
```sql
builder_profiles
  ├─ id (BIGINT UNSIGNED) - PRIMARY KEY
  ├─ build_id (VARCHAR(64)) - UNIQUE - Builder public ID
  ├─ public_id (BIGINT UNSIGNED) - FK → users.public_id ❌
  │    ^
  │    └─ PROBLEM: Type mismatch!
  │       - Column is BIGINT
  │       - References users.public_id (VARCHAR)
  │       - Should be user_id → users.id
  ├─ name, website, specialties...
  └─ rating, locations...
```
**Status:** ❌ Schema error
- Wrong column name (`public_id` should be `user_id`)
- Wrong foreign key target (`users.public_id` should be `users.id`)
- Type mismatch (BIGINT → VARCHAR)

---

#### 3. Community ℹ️ NOT A USER PROFILE
```sql
communities
  ├─ id (BIGINT UNSIGNED) - PRIMARY KEY
  ├─ public_id (VARCHAR(64)) - UNIQUE - Community UUID
  ├─ name, city, postal_code...
  ├─ NO direct user link (communities are entities)
  └─ Linked to users via community_admin_links
```
**Status:** ℹ️ Correct design
- Communities are NOT user profiles
- Users can admin communities via `community_admin_links`
- Many-to-many relationship

---

#### 4. CommunityAdminLink ✅ CORRECT
```sql
community_admin_links
  ├─ id (BIGINT UNSIGNED) - PRIMARY KEY
  ├─ community_id (BIGINT UNSIGNED) - FK → communities.id ✅
  ├─ user_id (BIGINT UNSIGNED) - FK → users.id ✅
  ├─ role (VARCHAR) - "owner", "moderator", "editor"
  └─ UNIQUE(community_id, user_id)
```
**Status:** ✅ Properly structured
- Links User to Community with role
- Many-to-many relationship

---

#### 5. SalesRep ℹ️ EMPLOYEE MODEL (NOT USER PROFILE)
```sql
sales_reps
  ├─ id (BIGINT UNSIGNED) - PRIMARY KEY
  ├─ builder_id (BIGINT UNSIGNED) - FK → builder_profiles.id
  ├─ community_id (BIGINT UNSIGNED) - FK → communities.id
  ├─ full_name, email, phone...
  ├─ NO user_id (sales reps are builder employees)
  └─ ...
```
**Status:** ℹ️ Different model
- Sales reps are employees of builders
- NOT linked to User table
- May need revision if sales reps should be users

---

## Problems Identified

### 🚨 Critical Issues

1. **BuilderProfile Foreign Key Error**
   - Column: `public_id BIGINT`
   - References: `users.public_id VARCHAR(50)`
   - **Type mismatch** - Will cause FK constraint failure
   - Should reference `users.id` instead

2. **Inconsistent Naming**
   - BuyerProfile uses `user_id` ✅
   - BuilderProfile uses `public_id` ❌
   - Should be consistent across all profile tables

3. **Missing User Relationships**
   - User model only has `buyer_profile` relationship
   - Missing: `builder_profile`, etc.

---

## Recommended Schema Design

### Option 1: Separate Profile Tables (Current Approach) ✅ RECOMMENDED

**Pros:**
- Different profiles have different fields
- Flexible schema per role
- Good for role-specific queries
- Better performance (no unused columns)

**Cons:**
- Need multiple tables
- Slightly more complex joins

**Implementation:**
```sql
users
  ├─ id (BIGINT) - PK
  ├─ public_id (VARCHAR) - UNIQUE
  ├─ role_id (FK → roles.id) - Determines which profile table to use
  └─ ...

buyer_profiles
  ├─ id (BIGINT) - PK
  ├─ user_id (BIGINT) - FK → users.id UNIQUE
  └─ buyer-specific fields...

builder_profiles
  ├─ id (BIGINT) - PK
  ├─ user_id (BIGINT) - FK → users.id UNIQUE  [FIXED]
  └─ builder-specific fields...

-- Community is NOT a profile (it's an entity)
communities
  ├─ id (BIGINT) - PK
  ├─ public_id (VARCHAR) - UNIQUE
  └─ community fields...

community_admin_links
  ├─ community_id (FK → communities.id)
  ├─ user_id (FK → users.id)
  └─ role (owner/moderator/editor)

-- Sales rep can be either:
-- A) Employee model (current - no user link)
-- B) User profile (add user_id FK)
```

---

### Option 2: Single Profile Table with JSON (Not Recommended)

```sql
user_profiles
  ├─ id (BIGINT) - PK
  ├─ user_id (BIGINT) - FK → users.id UNIQUE
  ├─ profile_type (ENUM: buyer, builder, community_admin, sales_rep)
  └─ profile_data (JSON) - All profile fields
```

**Pros:**
- Single table for all profiles
- Easy to add new profile types

**Cons:**
- No schema validation
- Poor query performance
- Can't use SQL constraints on JSON fields
- Difficult to index

---

## Recommended Solution

### Step 1: Fix BuilderProfile Model

**File:** `model/profiles/builder.py`

**Current (WRONG):**
```python
public_id = Column(
    MyBIGINT(unsigned=True),
    ForeignKey("users.public_id", ondelete="SET NULL"),  # ❌ WRONG
    unique=True,
    nullable=True,
    index=True
)
```

**Fixed (CORRECT):**
```python
user_id = Column(
    MyBIGINT(unsigned=True),
    ForeignKey("users.id", ondelete="CASCADE"),  # ✅ CORRECT
    unique=True,
    nullable=False,  # Should be NOT NULL for required profiles
    index=True
)
```

---

### Step 2: Update User Model Relationships

**File:** `model/user.py`

**Add:**
```python
class Users(Base):
    # ... existing fields ...

    # Profile relationships (one-to-one)
    buyer_profile = relationship("BuyerProfile", back_populates="user", uselist=False)
    builder_profile = relationship("BuilderProfile", back_populates="user", uselist=False)  # ADD THIS

    # Community admin relationships (many-to-many)
    community_admin_links = relationship("CommunityAdminLink", back_populates="user")  # ADD THIS
```

---

### Step 3: Update BuilderProfile Relationship

**File:** `model/profiles/builder.py`

**Add:**
```python
class BuilderProfile(Base):
    # ... existing fields ...

    # Relationship back to user
    user = relationship("Users", back_populates="builder_profile")
```

---

### Step 4: Create Database Migration

```sql
-- Migration: fix_builder_profile_foreign_key

-- Step 1: Drop the incorrect foreign key
ALTER TABLE builder_profiles
  DROP FOREIGN KEY builder_profiles_ibfk_1;  -- Check actual constraint name

-- Step 2: Rename column
ALTER TABLE builder_profiles
  CHANGE COLUMN public_id user_id BIGINT UNSIGNED NOT NULL;

-- Step 3: Ensure user_id values are valid
-- (This may require data migration if public_id contained string UUIDs)

-- Step 4: Add correct foreign key
ALTER TABLE builder_profiles
  ADD CONSTRAINT builder_profiles_ibfk_1
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Step 5: Ensure unique constraint
ALTER TABLE builder_profiles
  ADD UNIQUE INDEX uq_builder_user (user_id);
```

---

## Design Principles

### ✅ Best Practices

1. **Consistent Naming**
   - All profile tables use `user_id` to reference users
   - All FK to users.id (not users.public_id)

2. **One-to-One Relationships**
   - Each User can have ONE profile per type
   - Enforced via UNIQUE constraint on user_id

3. **Cascade Delete**
   - When user deleted → profile deleted
   - Maintains referential integrity

4. **Role Determines Profile**
   - users.role_id indicates which profile type
   - Application logic queries appropriate profile table

### Query Pattern

```python
# Get user with their profile based on role
user = db.query(Users).filter(Users.public_id == public_id).first()

if user.role.key == "buyer":
    profile = user.buyer_profile  # Uses relationship
elif user.role.key == "builder":
    profile = user.builder_profile
elif user.role.key == "community":
    # Community admins don't have a single profile
    # They have links to communities they admin
    admin_links = user.community_admin_links
```

---

## Summary

### Current State
- ✅ BuyerProfile: Correct
- ❌ BuilderProfile: Schema error (wrong FK)
- ℹ️ Community: Not a profile (correct)
- ✅ CommunityAdminLink: Correct
- ℹ️ SalesRep: Employee model (may need user link)

### Required Changes
1. Fix BuilderProfile.user_id foreign key
2. Add builder_profile relationship to Users
3. Create migration script
4. Decide if SalesRep should link to Users

### Files to Modify
- `model/profiles/builder.py` - Fix foreign key
- `model/user.py` - Add relationship
- New migration file
