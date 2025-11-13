# Fred Caldwell Community Profile - Seed Data

This directory contains seed data scripts to create a complete community profile for **Fred Caldwell**, HOA President of **Oak Meadows** in Austin, TX.

## 📋 What Gets Created

### 1. User Account
- **Name**: Fred Caldwell
- **Email**: fred.caldwell@oakmeadows.org
- **Phone**: +1 (512) 555-0199
- **Role**: Community Admin
- **Status**: Active, Verified, Onboarding Complete
- **Plan**: Pro

### 2. Community Profile (Oak Meadows)
- **Name**: Oak Meadows
- **Location**: Austin, TX 78704
- **Type**: Master-Planned Community
- **Stats**:
  - 524 homes
  - 1,847 residents
  - 1,247 followers
  - Founded: 2018
  - Development Stage: Phase 3
- **Financials**:
  - Community Dues: $500/year
  - Monthly Fee: $125/month
  - Tax Rate: 2.1%

### 3. Amenities (6)
- Resort-Style Pool
- State-of-the-Art Fitness Center
- Walking & Biking Trails
- Dog Park
- Playground & Splash Pad
- Community Clubhouse

### 4. Upcoming Events (4)
- Annual Summer BBQ & Pool Party (15 days from now)
- HOA Board Meeting (7 days from now)
- Kids Movie Night Under the Stars (22 days from now)
- Fitness Bootcamp (3 days from now)

### 5. Builder Cards (3)
- Taylor Morrison (Luxury Custom Homes) - 1,542 followers
- Lennar Homes (Energy-Efficient Living) - 2,341 followers
- David Weekley Homes (Award-Winning Builder) - 987 followers

### 6. Community Admin Contacts (3)
- Fred Caldwell - HOA President
- Sarah Martinez - Vice President
- Michael Chen - Treasurer

### 7. Awards (3)
- Best Master-Planned Community (2023) - Austin Home Builders Association
- Community of the Year (2022) - Texas HOA Management
- Green Community Award (2024) - Austin Environmental Council

### 8. Discussion Topics (3)
- Pool Hours Extension Request (24 replies, pinned)
- New Playground Equipment Ideas (15 replies)
- Landscaping Maintenance Schedule (8 replies, pinned)

### 9. Development Phases (3)
- Phase 1 - Established (3 lots, all sold)
- Phase 2 - Nearly Complete (2 lots, 1 available)
- Phase 3 - Under Development (3 lots, all available)

### 10. Community Admin Profile
Links Fred Caldwell's user account to the Oak Meadows community with full admin permissions.

## 🚀 Usage

### Option 1: Python Script (Recommended)

The Python script uses the existing database session management and models:

```bash
cd "Artitec Backend Development"
source .venv/bin/activate
python seed_fred_caldwell_community.py
```

**Advantages:**
- Uses existing database session management
- Validates data through Pydantic schemas
- Handles errors gracefully
- Provides detailed progress output
- Won't create duplicates if run multiple times

### Option 2: SQL Script (Direct Database)

For direct database execution:

```bash
# Using MySQL CLI
mysql -u root -p artitec < seed_fred_caldwell_community.sql

# Or using a specific database URL
mysql -h localhost -u your_user -p your_database < seed_fred_caldwell_community.sql
```

**Advantages:**
- Fast execution
- No Python dependencies
- Direct SQL control
- Easy to modify

## 📊 Database Tables Modified

The scripts will insert data into the following tables:

1. `users` - Fred Caldwell's user account
2. `roles` - Community admin role (if doesn't exist)
3. `communities` - Oak Meadows community
4. `community_amenities` - 6 amenity records
5. `community_events` - 4 event records
6. `community_builders` - 3 builder card records
7. `community_admins` - 3 admin contact records
8. `community_awards` - 3 award records
9. `community_topics` - 3 discussion topic records
10. `community_phases` - 3 development phase records
11. `community_admin_profiles` - Fred's admin profile

## 🔍 Verification

After running the seed script, verify the data was created:

### Check User
```sql
SELECT id, public_id, email, first_name, last_name, role_id
FROM users
WHERE email = 'fred.caldwell@oakmeadows.org';
```

### Check Community
```sql
SELECT id, public_id, name, city, state, followers, homes, residents
FROM communities
WHERE name = 'Oak Meadows';
```

### Check Admin Profile
```sql
SELECT
    u.email,
    CONCAT(u.first_name, ' ', u.last_name) as user_name,
    c.name as community_name,
    cap.title,
    cap.bio
FROM users u
JOIN community_admin_profiles cap ON u.id = cap.user_id
JOIN communities c ON cap.community_id = c.id
WHERE u.email = 'fred.caldwell@oakmeadows.org';
```

### Check Related Data
```sql
-- Amenities
SELECT COUNT(*) as amenity_count FROM community_amenities
WHERE community_id = (SELECT id FROM communities WHERE name = 'Oak Meadows');

-- Events
SELECT COUNT(*) as event_count FROM community_events
WHERE community_id = (SELECT id FROM communities WHERE name = 'Oak Meadows');

-- Builder Cards
SELECT COUNT(*) as builder_count FROM community_builders
WHERE community_id = (SELECT id FROM communities WHERE name = 'Oak Meadows');

-- Awards
SELECT COUNT(*) as award_count FROM community_awards
WHERE community_id = (SELECT id FROM communities WHERE name = 'Oak Meadows');

-- Discussion Topics
SELECT COUNT(*) as topic_count FROM community_topics
WHERE community_id = (SELECT id FROM communities WHERE name = 'Oak Meadows');

-- Development Phases
SELECT COUNT(*) as phase_count FROM community_phases
WHERE community_id = (SELECT id FROM communities WHERE name = 'Oak Meadows');
```

Expected counts:
- Amenities: 6
- Events: 4
- Builder Cards: 3
- Admin Contacts: 3
- Awards: 3
- Topics: 3
- Phases: 3

## 📱 iOS App Integration

Once the seed data is loaded, you can view Fred Caldwell's community profile in the iOS app:

1. **Login/Register** as Fred Caldwell:
   - Email: `fred.caldwell@oakmeadows.org`
   - Password: (you'll need to set this via user credentials table)

2. **View Community Profile**:
   - Navigate to Communities section
   - Search for "Oak Meadows" or use the community public_id

3. **Profile Features Visible**:
   - Community header with name, location, followers
   - About section with full description
   - 6 amenities with gallery images
   - 4 upcoming events
   - 3 builder cards
   - 3 admin contacts
   - 3 awards with recognition details
   - 3 discussion topics with replies
   - 3 development phases with lot information

## 🔐 User Credentials

**Important**: The seed scripts create the user account but **do not set a password**. You need to add credentials separately:

```sql
-- Set password for Fred Caldwell (use bcrypt hash)
INSERT INTO user_credentials (user_id, password_hash, password_algo)
VALUES (
    (SELECT id FROM users WHERE email = 'fred.caldwell@oakmeadows.org'),
    '$2b$12$YOUR_BCRYPT_HASH_HERE',  -- Replace with actual bcrypt hash
    'bcrypt'
);
```

Or use the registration API endpoint to create credentials.

## 🎨 Customization

Both scripts are easy to customize:

### Python Script
Edit `seed_fred_caldwell_community.py` and modify the data dictionaries:
- `amenities_data` - Add/remove amenities
- `events_data` - Modify events
- `builders_data` - Change builders
- `awards_data` - Update awards
- etc.

### SQL Script
Edit `seed_fred_caldwell_community.sql` and modify the INSERT statements directly.

## ⚠️ Important Notes

1. **Duplicate Prevention**: The Python script checks for existing data and won't create duplicates. The SQL script uses `INSERT ... ON DUPLICATE KEY UPDATE` for users/roles but will create duplicate communities if run multiple times.

2. **Foreign Key Dependencies**: The scripts create data in the correct order to satisfy foreign key constraints:
   - Role → User → Community → Related Tables → Admin Profile

3. **Image URLs**: The scripts use Unsplash placeholder images. Replace with actual community images in production.

4. **Timestamps**: Events are scheduled relative to the current time when the script runs.

5. **Public IDs**: UUID/unique identifiers are generated automatically.

## 🧪 Testing

To test the complete workflow:

1. Run the seed script
2. Start the backend server
3. Query the community profile API:
```bash
# Get community by ID
curl http://localhost:8000/v1/communities/{community_id}

# Get community by public_id
curl http://localhost:8000/v1/communities/by-public-id/{public_id}
```

4. Test in iOS app by navigating to the community profile

## 📝 API Endpoints

After seeding, these endpoints should work:

- `GET /v1/communities/{id}` - Get full community profile
- `GET /v1/communities/{id}/amenities` - Get amenities
- `GET /v1/communities/{id}/events` - Get upcoming events
- `GET /v1/communities/{id}/awards` - Get awards
- `GET /v1/communities/{id}/topics` - Get discussion topics
- `GET /v1/communities/{id}/phases` - Get development phases

## 🆘 Troubleshooting

### Script Fails with "Connection Refused"
- Ensure MySQL/database server is running
- Check database credentials in `.env` file
- Verify `DATABASE_URL` environment variable

### Duplicate Key Error
- The community or user already exists
- Either delete existing data or modify the script to use different email/name

### Foreign Key Constraint Error
- Ensure all referenced tables exist (users, roles, communities)
- Check that migrations have been run: `alembic upgrade head`

### User Already Has Admin Profile
- The user is already linked to a community
- Either use a different user or delete the existing admin profile

## 📚 Related Documentation

- [Community Models](model/profiles/community.py)
- [Community Schemas](schema/community.py)
- [Community Admin Profile Model](model/profiles/community_admin_profile.py)
- [User Model](model/user.py)

---

**Created**: November 12, 2025
**Version**: 1.0
**Status**: Ready for use
