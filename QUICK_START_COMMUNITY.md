# 🚀 Quick Start: Community Profile Setup

## What You Have:

Your backend already has a **complete Community Profile system**:

### ✅ Main Profile Table: `communities`
Contains: name, city, followers, residents, homes, description, video, awards, etc.

### ✅ Related Tables (Auto-loaded):
- `community_amenities` - Pool, gym, trails, etc.
- `community_events` - Upcoming events
- `community_builders` - Builders in the community
- `community_admins` - Admin contact info
- `community_awards` - Recognition and awards
- `community_topics` - Discussion threads
- `community_phases` - Development phases with lots

### ✅ User Link Table: `community_admin_profiles`
Links users to communities they manage

---

## 🎯 Setup in 3 Steps:

### Step 1: Create Community Admin Profile Table

```bash
cd "Artitec Backend Development"
mysql -u your_user -p your_database < migrations/create_community_admin_profiles_table.sql
```

### Step 2: Create a Full Community Profile with ALL Data

```bash
python scripts/create_full_community_profile.py
```

This creates:
- ✅ Main community (Oak Meadows)
- ✅ 7 amenities with photo galleries
- ✅ 5 upcoming events
- ✅ 3 builder cards
- ✅ 3 community administrators
- ✅ 3 awards
- ✅ 6 discussion threads
- ✅ 3 development phases with lots data

**Output will show you the Community ID** (e.g., `Community ID: 1`)

### Step 3: Link Your User to the Community

```bash
# Replace USER_ID and COMMUNITY_ID with your actual IDs
python scripts/create_community_admin_sample.py --user-id 1 --community-id 1
```

---

## 📱 Test in iOS App:

1. Update `CommunityDashboard.swift`:
   ```swift
   private var userCommunityId: Int {
       return 1  // Use the Community ID from step 2
   }
   ```

2. Sign in as the user you linked (from step 3)

3. Navigate to the Community profile tab

4. Watch the console logs to see data loading! 🎉

---

## 🧪 Test the API:

```bash
# Get community with all nested data
curl "http://127.0.0.1:8000/v1/profiles/communities/1?include=amenities,events,builder_cards,admins,awards,threads,phases" | json_pp

# Get community admin profile
curl "http://127.0.0.1:8000/v1/profiles/community-admins/user/1"
```

---

## 📊 Database Tables Overview:

```
MAIN COMMUNITY PROFILE:
├── communities (the profile)
│   ├── name, city, postal_code
│   ├── followers, residents, homes
│   ├── about (description)
│   ├── intro_video_url
│   ├── community_dues, tax_rate
│   └── is_verified, founded_year

NESTED DATA (1-to-many):
├── community_amenities
├── community_events
├── community_builders (builder cards)
├── community_admins (contact info)
├── community_awards
├── community_topics (discussion threads)
└── community_phases (with lots as JSON)

USER LINK:
└── community_admin_profiles
    ├── user_id → users
    └── community_id → communities
```

---

## 🎨 What the iOS App Will Show:

### Info Tab:
- Video intro
- Description/About
- Facts (city, dues, tax rate)
- Amenities with galleries
- Schools (future)
- Shopping (future)
- Builders
- Administrators

### Threads Tab:
- Discussion topics
- Replies count
- Pinned posts

### Updates & Awards Tab:
- Upcoming events
- Awards and recognition

### Phases Tab:
- Development phases
- Lots (available/sold/reserved)
- Phase maps

---

## ✅ Checklist:

- [ ] Run migration to create `community_admin_profiles` table
- [ ] Run script to create full community profile
- [ ] Note the Community ID from the output
- [ ] Link your user to the community
- [ ] Update `userCommunityId` in iOS app
- [ ] Launch app and test!

---

## 🆘 Need Help?

**Check if tables exist:**
```sql
SHOW TABLES LIKE 'communit%';
```

**View created data:**
```sql
SELECT * FROM communities;
SELECT * FROM community_amenities;
SELECT * FROM community_admin_profiles;
```

**Delete and start over:**
```sql
DELETE FROM communities WHERE id = 1;
-- This will cascade delete all related data
```

---

Happy coding! 🎉
