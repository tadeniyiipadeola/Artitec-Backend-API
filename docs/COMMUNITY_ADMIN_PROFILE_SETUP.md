# Community Admin Profile Setup Guide

This guide explains how to set up and use the Community Admin Profile system for your Artitec backend.

## Overview

The **Community Admin Profile** system allows users to be linked to communities they administer. This is similar to how `buyer_profiles` and `builder_profiles` work.

### What Was Created

1. **Database Model**: `CommunityAdminProfile` (`model/profiles/community_admin_profile.py`)
2. **Pydantic Schemas**: Request/Response models (`schema/community_admin_profile.py`)
3. **API Routes**: CRUD endpoints (`routes/profiles/community_admin.py`)
4. **SQL Migration**: Table creation script (`migrations/create_community_admin_profiles_table.sql`)
5. **Helper Script**: Sample data creation (`scripts/create_community_admin_sample.py`)

---

## Step 1: Run the Database Migration

Create the `community_admin_profiles` table in your database:

```bash
# Connect to your MySQL database
mysql -u your_username -p your_database_name

# Run the migration
source migrations/create_community_admin_profiles_table.sql

# Or directly:
mysql -u your_username -p your_database_name < migrations/create_community_admin_profiles_table.sql
```

---

## Step 2: Create a Test Community (if needed)

If you don't have a community in your database yet, you'll need to create one. You can do this via SQL or through the API.

### Option A: Create via SQL

```sql
INSERT INTO communities (
    public_id, name, city, postal_code,
    community_dues, tax_rate, monthly_fee,
    followers, about, is_verified,
    homes, residents, founded_year
) VALUES (
    'oak-meadows-001',
    'Oak Meadows',
    'Austin',
    '78704',
    '$500/year',
    '2.1%',
    '$125',
    1250,
    'A vibrant family-friendly community in Austin, Texas',
    1,
    524,
    1847,
    2018
);

-- Get the ID of the created community
SELECT id, name FROM communities WHERE public_id = 'oak-meadows-001';
```

### Option B: Create via API

```bash
curl -X POST http://127.0.0.1:8000/v1/profiles/communities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Oak Meadows",
    "city": "Austin",
    "postal_code": "78704",
    "community_dues": "$500/year",
    "tax_rate": "2.1%",
    "is_verified": true,
    "homes": 524,
    "residents": 1847,
    "founded_year": 2018
  }'
```

---

## Step 3: Create a Community Admin Profile

Link a user to a community using the helper script:

```bash
# Interactive mode (will prompt for IDs)
python scripts/create_community_admin_sample.py --interactive

# Or specify IDs directly
python scripts/create_community_admin_sample.py --user-id 1 --community-id 1
```

The script will:
- ✅ Verify the user exists
- ✅ Verify the community exists
- ✅ Create the admin profile linking them
- ✅ Set default permissions

---

## Step 4: Ensure User Has Correct Role

Make sure the user has a "community" or "community_admin" role:

```sql
-- Check current role
SELECT u.id, u.email, u.first_name, u.last_name, r.name as role
FROM users u
LEFT JOIN user_roles r ON u.role_id = r.id
WHERE u.id = 1;

-- Update role if needed (find the community role_id first)
SELECT id, name FROM user_roles WHERE name LIKE '%community%';

-- Set the role
UPDATE users SET role_id = <community_role_id> WHERE id = 1;
```

---

## Step 5: Update iOS App to Fetch Community ID

Update `CommunityDashboard.swift` to fetch the community ID from the user's profile:

```swift
// In CommunityDashboard.swift
private var userCommunityId: Int {
    // Fetch from community admin profile API
    // GET /v1/profiles/community-admins/me
    // For now, using test ID
    return 1
}
```

---

## API Endpoints

### Get Current User's Community Admin Profile
```http
GET /v1/profiles/community-admins/me
Authorization: Bearer <token>
```

### Get Community Admin Profile by ID
```http
GET /v1/profiles/community-admins/{profile_id}
```

### Get Community Admin Profile by User ID
```http
GET /v1/profiles/community-admins/user/{user_id}
```

### Create Community Admin Profile
```http
POST /v1/profiles/community-admins
Content-Type: application/json

{
  "user_id": 1,
  "community_id": 1,
  "display_name": "John Doe",
  "title": "Community Manager",
  "bio": "Managing Oak Meadows since 2020",
  "contact_email": "john@example.com",
  "can_post_announcements": true,
  "can_manage_events": true,
  "can_moderate_threads": true
}
```

### Update Community Admin Profile
```http
PATCH /v1/profiles/community-admins/{profile_id}
Content-Type: application/json

{
  "display_name": "John Doe Jr.",
  "title": "Senior Community Manager"
}
```

### Update Current User's Profile
```http
PATCH /v1/profiles/community-admins/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "bio": "Updated bio text"
}
```

---

## Database Schema

```sql
community_admin_profiles
├── id (BIGINT, PK)
├── user_id (BIGINT, FK -> users.id, UNIQUE)
├── community_id (BIGINT, FK -> communities.id)
├── display_name (VARCHAR)
├── profile_image (VARCHAR)
├── bio (TEXT)
├── title (VARCHAR)
├── contact_email (VARCHAR)
├── contact_phone (VARCHAR)
├── contact_preferred (VARCHAR)
├── can_post_announcements (BOOLEAN)
├── can_manage_events (BOOLEAN)
├── can_moderate_threads (BOOLEAN)
├── extra (TEXT)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

---

## Testing

### 1. Create Test Data
```bash
python scripts/create_community_admin_sample.py --user-id 1 --community-id 1
```

### 2. Test API Endpoint
```bash
# Get the profile
curl http://127.0.0.1:8000/v1/profiles/community-admins/user/1
```

### 3. Test in iOS App
1. Sign in as the user you linked to the community
2. Navigate to the Community profile tab
3. You should see the community data load from the API

---

## Next Steps

1. ✅ **Run migration** to create the table
2. ✅ **Create test community** (if needed)
3. ✅ **Link user to community** using the script
4. ✅ **Test API endpoints** to verify data
5. ✅ **Update iOS app** to fetch community ID from `/me` endpoint
6. ✅ **Populate community with data** (amenities, events, awards, etc.)

---

## Troubleshooting

### "Community admin profile not found"
- Make sure you ran the script to create the profile
- Check: `SELECT * FROM community_admin_profiles;`

### "Community not found"
- Create a community first (see Step 2)
- Check: `SELECT * FROM communities;`

### iOS app not loading community
- Check console logs for API errors
- Verify the community ID in CommunityDashboard
- Ensure backend is running and accessible

---

## Files Modified/Created

### Backend Files
- ✅ `model/profiles/community_admin_profile.py` - Database model
- ✅ `schema/community_admin_profile.py` - Pydantic schemas
- ✅ `routes/profiles/community_admin.py` - API endpoints
- ✅ `src/app.py` - Registered routes
- ✅ `migrations/create_community_admin_profiles_table.sql` - Migration
- ✅ `scripts/create_community_admin_sample.py` - Helper script

### iOS Files (already done)
- ✅ `CommunityDashboard.swift` - Uses `userCommunityId`
- ✅ `CommunityViewLoader.swift` - Fetches community data
- ✅ `CommunityRemoteRepository.swift` - API integration

---

## Support

If you encounter any issues:
1. Check the console logs (both backend and iOS)
2. Verify database tables exist
3. Ensure foreign key relationships are correct
4. Test API endpoints with curl/Postman first

Happy coding! 🎉
