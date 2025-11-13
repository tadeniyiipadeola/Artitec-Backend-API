# Quick Start: Fred Caldwell - The Highlands Community

## ⚡ 5-Minute Setup

### Step 1: Start Your Database
```bash
# Make sure MySQL is running
mysql.server start  # or your system's MySQL start command
```

### Step 2: Run the Seed Script

**SQL (Recommended - No Dependencies)**
```bash
mysql -u root -p appdb < seed_fred_caldwell_community.sql
```

### Step 3: Verify the Data
```bash
# Check that Fred Caldwell was created
mysql -u root -p appdb -e "
SELECT u.email, CONCAT(u.first_name, ' ', u.last_name) as name, c.name as community
FROM users u
JOIN community_admin_profiles cap ON u.id = cap.user_id
JOIN communities c ON cap.community_id = c.id
WHERE u.email = 'fred.caldwell@thehighlands.com';
"
```

Expected output:
```
+----------------------------------+---------------+---------------+
| email                            | name          | community     |
+----------------------------------+---------------+---------------+
| fred.caldwell@thehighlands.com   | Fred Caldwell | The Highlands |
+----------------------------------+---------------+---------------+
```

### Step 4: Get the Community ID
```bash
mysql -u root -p appdb -e "
SELECT id, public_id, name, city, state FROM communities WHERE name = 'The Highlands';
"
```

Save the `id` and `public_id` for API calls.

### Step 5: Test the API

**Start your backend server:**
```bash
cd "Artitec Backend Development"
source .venv/bin/activate
uvicorn main:app --reload
```

**Test the API endpoints:**
```bash
# Get community profile (replace {community_id} with actual ID)
curl http://localhost:8000/v1/communities/{community_id}

# Get community with all related data
curl "http://localhost:8000/v1/communities/{community_id}?include=amenities,events,builder_cards,admins,awards,threads,phases"

# Search for Oak Meadows
curl "http://localhost:8000/v1/communities/?q=Oak%20Meadows"

# Get specific amenities
curl http://localhost:8000/v1/communities/{community_id}/amenities

# Get upcoming events
curl http://localhost:8000/v1/communities/{community_id}/events

# Get awards
curl http://localhost:8000/v1/communities/{community_id}/awards

# Get discussion topics
curl http://localhost:8000/v1/communities/{community_id}/topics

# Get development phases
curl http://localhost:8000/v1/communities/{community_id}/phases
```

## 📱 View in iOS App

### If Backend is Local:
1. Update iOS app to point to your local backend: `http://localhost:8000`
2. Launch the iOS app
3. Navigate to Communities
4. Search for "The Highlands" or browse communities
5. View Fred Caldwell's complete community profile

### If Backend is Deployed:
1. Ensure the backend URL is configured in iOS app
2. Launch the app
3. Navigate to Communities → The Highlands

## 📊 What You'll See

### Community Header
- **The Highlands**
- Porter, TX 77365
- 2,847 followers
- President & CEO: Fred Caldwell

### Statistics
- 2,300 acres of natural beauty
- 1,200 homes (4,000 planned)
- 3,600 residents
- Founded 2021
- Active Development - Phase 2

### Amenities (12)
- The Highlands Pines Golf Course (18-hole, semi-private)
- Water Park & Lazy River
- State-of-the-Art Fitness Center
- 30+ Miles of Trails
- 200-Acre Nature Preserve with 100-year-old cypress trees
- Event Lawn & Pavilion
- Tennis & Pickleball Courts
- Recreational Lakes (fishing, kayaking, paddle boarding)
- Lakeside Patio & Firepit
- Fishing Docks & Picnic Pavilions
- Amenity Center
- Highlands Elementary School (on-site)

### Upcoming Events (6)
- Party in the Preserve (GHBA Event of the Year)
- All Trails Lead Home Community Walk
- Golf Tournament & Social
- Lakeside Movie Night
- Community Fitness Bootcamp
- Kayaking & Paddle Board Social

### Builders (13)
- Taylor Morrison, Lennar, Perry Homes
- Chesmar Homes, Highland Homes, David Weekley Homes
- Coventry Homes, Beazer Homes, Empire Homes
- Partners in Building, Caldwell Homes
- Drees Custom Homes, Newmark Homes

### Awards (6)
- Master Planned Community of the Year (2024 - GHBA)
- Event of the Year - Party in the Preserve (2024 - GHBA)
- Developer of the Year (2024, 2023 - GHBA)
- Billboard Campaign Recognition (2024 - GHBA)
- Community Impact Award (2024 - Montgomery County)

### Discussion Topics (6)
- New Middle School Opening Fall 2027 (34 replies, pinned)
- Golf Course Membership Options (28 replies, pinned)
- Trail Maintenance and New Routes (42 replies)
- Party in the Preserve - Volunteers (19 replies, pinned)
- Water Park Hours Extension (31 replies)
- Fishing Tournament Sign-Ups (15 replies)

### Development Phases (4)
- Phase 1 - The Pines: Complete (all lots sold)
- Phase 2 - The Preserve: Active (lots $165K-$185K)
- Phase 3 - Lakeside Village: Coming Soon
- Fairway Pines: 55+ Active Adult (lots $145K-$160K)

## 🔑 User Login (Optional)

To login as Fred Caldwell, you need to set a password:

```python
# In Python shell
from werkzeug.security import generate_password_hash
import bcrypt

password = "YourPassword123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
print(hashed)
```

Then insert into database:
```sql
INSERT INTO user_credentials (user_id, password_hash, password_algo)
SELECT id, 'HASHED_PASSWORD_HERE', 'bcrypt'
FROM users
WHERE email = 'fred.caldwell@thehighlands.com';
```

Or use the registration API endpoint.

## 📝 API Response Example

**GET** `/v1/communities/{id}?include=amenities,events,awards`

```json
{
  "id": 1,
  "public_id": "the-highlands-abc12345",
  "name": "The Highlands",
  "city": "Porter",
  "state": "TX",
  "postal_code": "77365",
  "community_dues": "$1,420/year",
  "tax_rate": "2.1%",
  "monthly_fee": "$118/month",
  "followers": 2847,
  "about": "The Highlands is a 2,300-acre exploration of natural beauty in a densely treed, park-like setting...",
  "is_verified": true,
  "homes": 1200,
  "residents": 3600,
  "founded_year": 2021,
  "member_count": 2847,
  "development_stage": "Active Development - Phase 2",
  "enterprise_number_hoa": "HOA-TX-2021-TH01",
  "intro_video_url": "https://thehighlands.com",
  "community_website_url": "https://thehighlands.com",
  "amenities": [
    {
      "id": 1,
      "community_id": 1,
      "name": "The Highlands Pines Golf Course",
      "gallery": [
        "https://thehighlands.com/wp-content/uploads/2023/04/Golf-Course-Hero.jpg",
        "https://thehighlands.com/wp-content/uploads/2023/04/Golf-Clubhouse.jpg"
      ]
    },
    {
      "id": 2,
      "community_id": 1,
      "name": "200-Acre Nature Preserve",
      "gallery": [
        "https://thehighlands.com/wp-content/uploads/2023/04/Nature-Preserve.jpg"
      ]
    }
    // ... 10 more amenities (12 total)
  ],
  "events": [
    {
      "id": 1,
      "community_id": 1,
      "title": "Party in the Preserve",
      "description": "GHBA Event of the Year - annual celebration in our stunning 200-acre nature preserve!",
      "location": "200-Acre Nature Preserve",
      "start_at": "2025-12-03T12:00:00Z",
      "end_at": "2025-12-03T17:00:00Z",
      "is_public": true
    }
    // ... 5 more events (6 total)
  ],
  "awards": [
    {
      "id": 1,
      "community_id": 1,
      "title": "Master Planned Community of the Year",
      "year": 2024,
      "issuer": "Greater Houston Builders Association",
      "icon": "trophy.fill",
      "note": "Recognized as the top master-planned community in the Greater Houston area"
    }
    // ... 5 more awards (6 total)
  ],
  "builder_cards": [],
  "admins": [],
  "threads": [],
  "phases": [],
  "builder_ids": [],
  "created_at": "2025-11-12T12:00:00Z",
  "updated_at": "2025-11-12T12:00:00Z"
}
```

## 🎯 Available API Endpoints

All endpoints are under `/v1/communities/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all communities (with search/filter) |
| GET | `/{id}` | Get specific community |
| POST | `/` | Create new community |
| PUT/PATCH | `/{id}` | Update community |
| DELETE | `/{id}` | Delete community |
| GET | `/{id}/amenities` | List amenities |
| POST | `/{id}/amenities` | Add amenity |
| PATCH | `/{id}/amenities/{amenity_id}` | Update amenity |
| DELETE | `/{id}/amenities/{amenity_id}` | Delete amenity |
| GET | `/{id}/events` | List events |
| POST | `/{id}/events` | Create event |
| PATCH | `/{id}/events/{event_id}` | Update event |
| DELETE | `/{id}/events/{event_id}` | Delete event |
| GET | `/{id}/awards` | List awards |
| POST | `/{id}/awards` | Create award |
| PATCH | `/{id}/awards/{award_id}` | Update award |
| DELETE | `/{id}/awards/{award_id}` | Delete award |
| GET | `/{id}/topics` | List discussion topics |
| POST | `/{id}/topics` | Create topic |
| PATCH | `/{id}/topics/{topic_id}` | Update topic |
| DELETE | `/{id}/topics/{topic_id}` | Delete topic |
| GET | `/{id}/phases` | List development phases |
| POST | `/{id}/phases` | Create phase |
| PATCH | `/{id}/phases/{phase_id}` | Update phase |
| DELETE | `/{id}/phases/{phase_id}` | Delete phase |

## 🔍 Query Parameters

**List communities:**
- `q` - Search across name/about/city
- `city` - Filter by city
- `postal_code` - Filter by postal code
- `include` - Comma-separated: `amenities,events,builder_cards,admins,awards,threads,phases,builders`
- `limit` - Results per page (1-200, default 50)
- `offset` - Pagination offset

**Get community:**
- `include` - Same as list communities

## 📚 Next Steps

1. **Add More Communities**: Modify the seed script to add more communities
2. **Add Builder Profiles**: Link actual builder profiles to the community
3. **Add User Credentials**: Set passwords for Fred Caldwell to enable login
4. **Upload Real Images**: Replace Unsplash placeholders with actual community photos
5. **Test iOS Integration**: Verify all features work in the mobile app

## 🆘 Need Help?

- **Full Documentation**: See `FRED_CALDWELL_SEED_README.md`
- **Database Schema**: See `model/profiles/community.py`
- **API Routes**: See `routes/profiles/community.py`
- **Pydantic Schemas**: See `schema/community.py`

---

**Ready to go!** Run the seed script and start exploring Fred Caldwell's community profile in your app!
