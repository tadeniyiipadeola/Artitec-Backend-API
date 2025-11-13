# Community Admin Architecture

## 📊 Three Tables, Three Purposes

Your community admin system uses **three different tables**, each serving a specific purpose:

### 1. `community_admins` (Contact Metadata)
**File**: `model/profiles/community.py` (line 129-137)

**Purpose**: Simple contact information for displaying on community profiles

**Structure**:
```python
class CommunityAdmin(Base):
    __tablename__ = "community_admins"

    id = Column(...)
    community_id = Column(...)  # FK to communities
    name = Column(String(255))  # Just a text name
    role = Column(String(128))  # e.g., "HOA President"
    email = Column(String(255))
    phone = Column(String(64))
```

**Use Case**:
- Display contact info on community profile pages
- List multiple admins/board members
- **Does NOT require them to be registered users**
- Example: "Contact: Fred Caldwell (HOA President) - fred@example.com"

**Relationship**: One community → Many contact records

---

### 2. `community_admin_links` (Role-Based Access)
**File**: `model/profiles/community.py` (line 175-204)

**Purpose**: Flexible role-based permission management

**Structure**:
```python
class CommunityAdminLink(Base):
    __tablename__ = "community_admin_links"

    id = Column(...)
    community_id = Column(...)   # FK to communities
    user_id = Column(...)        # FK to users (must be registered)
    role = Column(String(64))    # "owner", "moderator", "editor"
    is_active = Column(Boolean)
```

**Use Case**:
- **One user can manage MULTIPLE communities**
- Role-based permissions (owner, moderator, editor)
- Lightweight permission mapping
- Management companies managing many communities
- Example: Sarah manages 5 different communities as "moderator"

**Relationship**: Many-to-many (users ↔ communities)

---

### 3. `community_admin_profiles` (Full User Profile)
**File**: `model/profiles/community_admin_profile.py`

**Purpose**: Complete user profile (like `buyer_profiles` or `builder_profiles`)

**Structure**:
```python
class CommunityAdminProfile(Base):
    __tablename__ = "community_admin_profiles"

    id = Column(...)
    user_id = Column(..., unique=True)    # One-to-one with users
    community_id = Column(...)             # ONE community only

    first_name = Column(String(128))
    last_name = Column(String(128))
    profile_image = Column(String(500))
    bio = Column(Text)
    title = Column(String(128))

    contact_email = Column(String(255))
    contact_phone = Column(String(64))
    contact_preferred = Column(String(32))

    can_post_announcements = Column(Boolean)
    can_manage_events = Column(Boolean)
    can_moderate_threads = Column(Boolean)
```

**Use Case**:
- **One user = ONE community admin profile**
- Dedicated community managers/HOA presidents
- Full profile with bio, image, permissions
- Consistent with buyer/builder profile pattern
- Example: Fred Caldwell is THE HOA President of Oak Meadows (only)

**Relationship**: One-to-one (user ↔ profile), One-to-many (community ↔ profiles)

---

## 🏗️ Architecture Pattern

### Consistent with Other Profiles

```
users table
  ├── buyer_profile (one-to-one) → ONE buyer profile
  ├── builder_profile (one-to-one) → ONE builder profile
  └── community_admin_profile (one-to-one) → ONE community admin profile
```

Each user can have **ONE profile per role type**:
- One buyer profile
- One builder profile
- One community admin profile

---

## 🤔 Which Should You Use?

### Use All Three Together:

**Scenario**: Fred Caldwell (Oak Meadows HOA President)

1. **`community_admin_profiles`** ✅
   - Fred's full profile with bio, image, title
   - Links Fred to Oak Meadows as his primary community
   - Displays on his user profile page

2. **`community_admins`** ✅
   - Lists Fred as "HOA President" contact on Oak Meadows page
   - Also lists Sarah Martinez (Vice President), Michael Chen (Treasurer)
   - These are just display contacts

3. **`community_admin_links`** (optional) ✅
   - Gives Fred "owner" role for Oak Meadows
   - Can also give Sarah "moderator" role
   - Flexible for future multi-community access

### When to Use Only `community_admin_links`:

**Scenario**: Management company managing 20 communities

- Skip `community_admin_profiles` (one-to-one constraint won't work)
- Use `community_admin_links` for flexible multi-community access
- Use `community_admins` for displaying contact info per community

---

## 📝 Migration Status

### Current State:

| Migration | Status | Description |
|-----------|--------|-------------|
| `c0d1e2f3g4h5` | **NEW** ✅ | Creates `community_admin_profiles` table |
| `5c8d3a4b9e1f` | Existing | Splits `display_name` → `first_name` + `last_name` |
| `0d8e1f2a3b4c` | Existing | Reorders columns |

### Action Required:

```bash
cd "Artitec Backend Development"
source .venv/bin/activate

# Run the new migration
alembic upgrade head
```

This will:
1. Create `community_admin_profiles` table (if not exists)
2. Apply subsequent migrations that modify it
3. Ensure your database matches your models

---

## 🎯 Recommended Approach for Fred Caldwell

Based on your use case (Fred Caldwell = dedicated HOA President), use:

### ✅ `community_admin_profiles`
- Creates Fred's full profile
- Links him to Oak Meadows
- Stores bio, image, title, permissions

### ✅ `community_admins`
- Lists Fred + other board members as contacts
- Displays on Oak Meadows community page

### ⚠️ `community_admin_links` (Optional)
- Use if you want fine-grained role management
- Use if Fred might manage other communities later
- Otherwise, skip for simplicity

---

## 💻 Code Example

### Creating Fred's Profile

```python
from model.user import Users, Role
from model.profiles.community import Community, CommunityAdmin
from model.profiles.community_admin_profile import CommunityAdminProfile

# 1. Create user
fred = Users(
    public_id=str(uuid.uuid4()),
    email="fred.caldwell@oakmeadows.org",
    first_name="Fred",
    last_name="Caldwell",
    role_id=community_admin_role_id
)
db.add(fred)
db.commit()

# 2. Create community
oak_meadows = Community(
    public_id="oak-meadows-001",
    name="Oak Meadows",
    city="Austin",
    state="TX"
)
db.add(oak_meadows)
db.commit()

# 3. Create admin profile (one-to-one)
admin_profile = CommunityAdminProfile(
    user_id=fred.id,
    community_id=oak_meadows.id,
    first_name="Fred",
    last_name="Caldwell",
    bio="Fred Caldwell has served as HOA President since 2020...",
    title="HOA President",
    profile_image="https://...",
    can_post_announcements=True,
    can_manage_events=True,
    can_moderate_threads=True
)
db.add(admin_profile)

# 4. Add contact info (display on community page)
admin_contact = CommunityAdmin(
    community_id=oak_meadows.id,
    name="Fred Caldwell",
    role="HOA President",
    email="fred.caldwell@oakmeadows.org",
    phone="(512) 555-0199"
)
db.add(admin_contact)

db.commit()
```

### Querying Fred's Profile

```python
# Get user with admin profile
user = db.query(Users).filter(Users.id == fred_id).first()
admin_profile = user.community_admin_profile  # One-to-one relationship

# Get community managed by Fred
community = admin_profile.community

# Get all admins listed on the community page
contact_admins = community.admins  # List of CommunityAdmin records
```

---

## 🔍 API Integration

### Profile Endpoint
```
GET /v1/profiles/community-admin/{user_id}
```

Returns:
```json
{
  "user_id": 123,
  "community_id": 456,
  "community_name": "Oak Meadows",
  "first_name": "Fred",
  "last_name": "Caldwell",
  "title": "HOA President",
  "bio": "Fred Caldwell has served as HOA President...",
  "profile_image": "https://...",
  "permissions": {
    "can_post_announcements": true,
    "can_manage_events": true,
    "can_moderate_threads": true
  }
}
```

### Community Contacts
```
GET /v1/communities/{community_id}
```

Returns community with admins:
```json
{
  "id": 456,
  "name": "Oak Meadows",
  "admins": [
    {
      "name": "Fred Caldwell",
      "role": "HOA President",
      "email": "fred.caldwell@oakmeadows.org",
      "phone": "(512) 555-0199"
    },
    {
      "name": "Sarah Martinez",
      "role": "Vice President",
      "email": "sarah.martinez@oakmeadows.org"
    }
  ]
}
```

---

## ✅ Final Answer

**YES, you should have the `community_admin_profiles` table** because:

1. ✅ It follows your existing pattern (buyer_profiles, builder_profiles)
2. ✅ It stores full user profile data (bio, image, permissions)
3. ✅ Your models reference it
4. ✅ Your migrations modify it
5. ✅ Your seed scripts use it
6. ✅ It's perfect for Fred Caldwell's use case

**Action**: Run `alembic upgrade head` to create the table!
