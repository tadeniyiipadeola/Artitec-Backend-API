# Followers Feature Setup Guide

This guide walks you through implementing the followers feature for the Artitec backend.

## 📋 Overview

The followers feature enables users to follow other users (buyers, builders, sales reps, etc.) and see social engagement metrics. The iOS app currently displays a placeholder "24 followers" count that will be replaced with real data once this backend is deployed.

## 🗂️ Files Created/Modified

### Database Migrations
1. **`alembic/versions/a1b2c3d4e5f6_add_followers_count_to_buyer_profiles.py`**
   - Adds `followers_count` column to `buyer_profiles` table
   - Creates index for efficient queries

2. **`alembic/versions/b2c3d4e5f6g7_create_followers_table.py`**
   - Creates `followers` table to track follow relationships
   - Includes constraints and indexes

### Models
3. **`model/profiles/buyer.py`** (Modified)
   - Added `followers_count` column (line 58)

4. **`model/followers.py`** (New)
   - Follower model for tracking relationships

### Schemas
5. **`schema/buyers.py`** (Modified)
   - Added `followers_count` field to `BuyerProfileOut` (line 247)

### API Routes
6. **`routes/followers.py`** (New)
   - Complete follow/unfollow API endpoints
   - Endpoints for listing followers/following
   - Stats endpoint

## 🚀 Deployment Steps

### Step 1: Run Database Migrations

```bash
cd "Artitec Backend Development"

# Review the migrations first
alembic history

# Apply the migrations
alembic upgrade head
```

This will:
- Add `followers_count` column to `buyer_profiles` table with default value 0
- Create the `followers` table with all constraints and indexes

### Step 2: Register the Followers Router

Add the followers router to your main application file (usually `main.py` or `app.py`):

```python
from routes import followers

# Add to your app
app.include_router(followers.router)
```

### Step 3: Verify Database Schema

Connect to your MySQL database and verify:

```sql
-- Check buyer_profiles table
DESCRIBE buyer_profiles;
-- Should show followers_count column

-- Check followers table
DESCRIBE followers;
-- Should show all columns and constraints

-- Verify indexes
SHOW INDEX FROM buyer_profiles WHERE Key_name = 'ix_buyer_profiles_followers_count';
SHOW INDEX FROM followers;
```

### Step 4: Test the Endpoints

```bash
# Get follow stats for a user
curl -X GET "http://localhost:8000/v1/followers/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Follow a user
curl -X POST "http://localhost:8000/v1/followers/2/follow" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get user's followers
curl -X GET "http://localhost:8000/v1/followers/2/followers"

# Unfollow a user
curl -X DELETE "http://localhost:8000/v1/followers/2/follow" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📱 iOS App Integration

Once deployed, the iOS app will automatically:
1. Display real follower counts instead of the placeholder "24"
2. Fetch `followers_count` from the API response (already implemented in `BuyerProfileOut.swift`)

### iOS Update Location
The placeholder is set in:
```swift
// Features/Profiles/BuyerView.swift:1937
followersCount: 24,  // TODO: Replace with actual followers count from backend once implemented
```

After backend deployment, update this line to:
```swift
followersCount: dto.followersCount ?? 0,  // Now using real backend data
```

## 🔧 API Endpoints Reference

### Follow/Unfollow
- `POST /v1/followers/{user_id}/follow` - Follow a user
- `DELETE /v1/followers/{user_id}/follow` - Unfollow a user

### Query Endpoints
- `GET /v1/followers/{user_id}/followers` - List followers (paginated)
- `GET /v1/followers/{user_id}/following` - List following (paginated)
- `GET /v1/followers/{user_id}/stats` - Get follower/following counts

### Response Schemas

**FollowResponse:**
```json
{
  "success": true,
  "message": "Successfully followed user",
  "followers_count": 42
}
```

**FollowStatsOut:**
```json
{
  "user_id": 123,
  "followers_count": 42,
  "following_count": 15,
  "is_following": true
}
```

**FollowerOut:**
```json
{
  "user_id": 456,
  "public_id": "abc123",
  "display_name": "John Doe",
  "profile_image": "https://...",
  "followed_at": "2025-11-12T12:00:00Z"
}
```

## ⚠️ Important Notes

### Database Triggers (Optional Enhancement)
For better performance, consider adding database triggers to automatically update `followers_count`:

```sql
DELIMITER $$

CREATE TRIGGER followers_count_increment
AFTER INSERT ON followers
FOR EACH ROW
BEGIN
    UPDATE buyer_profiles
    SET followers_count = followers_count + 1
    WHERE user_id = NEW.following_user_id;
END$$

CREATE TRIGGER followers_count_decrement
AFTER DELETE ON followers
FOR EACH ROW
BEGIN
    UPDATE buyer_profiles
    SET followers_count = followers_count - 1
    WHERE user_id = OLD.following_user_id;
END$$

DELIMITER ;
```

### Extending to Other Profiles
Currently only `buyer_profiles` has `followers_count`. To add for builders/sales reps:

1. Add migration to add column to those tables
2. Update the `update_followers_count()` function in `routes/followers.py`
3. Update respective schema files

## 🧪 Testing Checklist

- [ ] Migrations run successfully
- [ ] Can follow a user
- [ ] Cannot follow yourself
- [ ] Cannot follow same user twice
- [ ] Can unfollow a user
- [ ] Follower count updates correctly
- [ ] Can list followers (paginated)
- [ ] Can list following (paginated)
- [ ] Stats endpoint returns correct counts
- [ ] iOS app displays real follower counts

## 📚 Further Enhancements

Consider implementing:
- Push notifications when someone follows you
- Activity feed showing follows
- Suggested users to follow
- Mutual followers
- Follow requests (for private profiles)
- Blocking users

## 🆘 Troubleshooting

**Migration fails:**
- Check that the previous migration (9c7d0e1f3a4b) is applied
- Verify database connection
- Check for existing column/table conflicts

**Follower count not updating:**
- Check that `update_followers_count()` is being called
- Verify buyer_profile exists for the user
- Consider adding database triggers (see above)

**iOS still shows "24 followers":**
- Ensure backend is deployed and accessible
- Check that `followers_count` is in API response
- Update iOS code to use `dto.followersCount` instead of hardcoded value

---

**Created:** November 12, 2025
**Version:** 1.0
**Status:** Ready for deployment
