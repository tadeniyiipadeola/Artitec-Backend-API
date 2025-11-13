# Update The Highlands Community Owner

## Quick Start

### 1. Start MySQL
```bash
# Option 1: Using Homebrew services
brew services start mysql

# Option 2: Direct start
mysql.server start

# Verify MySQL is running
mysql -u root -p -e "SELECT 1"
```

### 2. Run the Update Script
```bash
# From the project root directory
python update_highlands_owner.py

# OR using the virtual environment directly
.venv/bin/python update_highlands_owner.py
```

### Expected Output
```
============================================================
Update The Highlands Community Owner
============================================================

🔍 Looking for user USR-1763002155-GRZVLL...
✅ Found user:
   ID: 42
   Public ID: USR-1763002155-GRZVLL
   Email: fred.caldwell@oakmeadows.org
   Name: Fred Caldwell

🔍 Looking for The Highlands community...
✅ Found community:
   ID: 1
   Public ID: CMY-1763002155-ABC123
   Name: The Highlands
   Current user_id: None

💾 Updating community owner...

============================================================
✅ SUCCESS!
============================================================
Community: "The Highlands"
Owner: Fred Caldwell
Email: fred.caldwell@oakmeadows.org
User ID: 42 (public_id: USR-1763002155-GRZVLL)
Verified in database: user_id = 42

You can now fetch this community via:
  GET /api/v1/profiles/communities/1
  GET /api/v1/profiles/communities/for-user/USR-1763002155-GRZVLL
============================================================
```

---

## Alternative: Manual SQL Update

If you prefer to run SQL directly:

```sql
-- 1. Connect to MySQL
mysql -u root -p appdb

-- 2. Find the user's integer ID
SELECT id, public_id, email, first_name, last_name
FROM users
WHERE public_id = 'USR-1763002155-GRZVLL';

-- Expected result:
-- +----+------------------------+-------------------------------+-------+----------+
-- | id | public_id              | email                         | first | last     |
-- +----+------------------------+-------------------------------+-------+----------+
-- | 42 | USR-1763002155-GRZVLL  | fred.caldwell@oakmeadows.org  | Fred  | Caldwell |
-- +----+------------------------+-------------------------------+-------+----------+

-- 3. Update The Highlands community (replace 42 with actual user.id from step 2)
UPDATE communities
SET user_id = 42
WHERE name LIKE '%Highlands%';

-- 4. Verify the update
SELECT id, public_id, name, user_id
FROM communities
WHERE name LIKE '%Highlands%';

-- Expected result:
-- +----+------------------------+--------------+---------+
-- | id | public_id              | name         | user_id |
-- +----+------------------------+--------------+---------+
-- |  1 | CMY-1763002155-ABC123  | The Highlands|      42 |
-- +----+------------------------+--------------+---------+
```

---

## Alternative: Using Admin API Endpoint

If your FastAPI server is running:

```bash
# Using curl
curl -X POST "http://localhost:8000/admin/connect-user-to-community?user_public_id=USR-1763002155-GRZVLL&community_name=The%20Highlands"

# Using httpie
http POST "http://localhost:8000/admin/connect-user-to-community?user_public_id=USR-1763002155-GRZVLL&community_name=The%20Highlands"
```

**Note:** This endpoint updates the CommunityAdminProfile but doesn't currently update the community's user_id field. The Python script or SQL update is recommended.

---

## Verification

After updating, verify the change worked:

### Via API (if server is running)
```bash
# Get community by ID
curl http://localhost:8000/api/v1/profiles/communities/1

# Get community for user
curl http://localhost:8000/api/v1/profiles/communities/for-user/USR-1763002155-GRZVLL

# Expected response should include:
# {
#   "id": 1,
#   "public_id": "CMY-1763002155-ABC123",
#   "user_id": 42,
#   "name": "The Highlands",
#   ...
# }
```

### Via Direct SQL
```sql
SELECT
    c.id,
    c.public_id,
    c.name,
    c.user_id,
    u.public_id as owner_public_id,
    u.email as owner_email,
    u.first_name,
    u.last_name
FROM communities c
LEFT JOIN users u ON c.user_id = u.id
WHERE c.name LIKE '%Highlands%';
```

---

## Troubleshooting

### Error: "Can't connect to MySQL server"
```bash
# Check if MySQL is running
brew services list | grep mysql

# Start MySQL
brew services start mysql

# Check MySQL status
mysql.server status
```

### Error: "User not found"
```bash
# List all users to find the correct public_id
.venv/bin/python -c "
from config.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text('SELECT public_id, email, first_name, last_name FROM users'))
for row in result:
    print(f'{row[0]}: {row[2]} {row[3]} ({row[1]})')
db.close()
"
```

### Error: "Community not found"
```bash
# List all communities
.venv/bin/python -c "
from config.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
result = db.execute(text('SELECT id, public_id, name FROM communities'))
for row in result:
    print(f'{row[0]}: {row[2]} ({row[1]})')
db.close()
"
```

---

## Files Updated

- ✅ `update_highlands_owner.py` - Helper script to update community owner
- ✅ `alembic/versions/g3h4i5j6k7l8_add_user_id_to_communities.py` - Migration executed
- ✅ `model/profiles/community.py` - Model updated with user_id field
- ✅ `schema/community.py` - Schema updated to return user_id
- ✅ `docs/SWIFTUI_IMPLEMENTATION_GUIDE.md` - iOS model documented

---

## Related Documentation

- [Community user_id Implementation](./COMMUNITY_USER_ID_IMPLEMENTATION.md)
- [SwiftUI Implementation Guide](./docs/SWIFTUI_IMPLEMENTATION_GUIDE.md)
- [The Highlands Setup](./COMPLETED_THE_HIGHLANDS_SETUP.md)

---

**Status:** ⏳ Ready to run when MySQL is started

**Last Updated:** 2024-11-12
