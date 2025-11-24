# Kelle Gandy Enterprise Account - Investigation Summary

**Investigation Date:** November 21, 2025
**Database:** MariaDB at 100.94.199.71:3306
**Status:** ✅ All systems operational

---

## Quick Facts

| Metric | Value |
|--------|-------|
| **User ID** | USR-11CF01A81A08 |
| **Email** | kelle.gandy@perryhomes.com |
| **Role** | builder |
| **Plan Tier** | enterprise |
| **Total Profiles** | 18 |
| **Verified Profiles** | 18 (100%) |
| **Team Memberships** | 0 |
| **Account Status** | Active |

---

## Geographic Coverage

Perry Homes profiles across Greater Houston, Texas:

| City | Profile Count |
|------|--------------|
| Cypress | 3 |
| Conroe | 2 |
| Missouri City | 2 |
| Richmond | 2 |
| Friendswood | 1 |
| Fulshear | 1 |
| Humble | 1 |
| Iowa Colony | 1 |
| Katy | 1 |
| Porter | 1 |
| Spring | 1 |
| Tomball | 1 |
| Willis | 1 |
| **Total** | **18** |

---

## Database Schema

### Primary Tables

1. **users** - Kelle's account information
   - Primary Key: `user_id` (USR-11CF01A81A08)
   - Role: builder
   - Plan: enterprise

2. **builder_profiles** - Perry Homes location profiles
   - Foreign Key: `user_id` → users.user_id
   - 18 profiles owned by Kelle
   - All verified and active

3. **builder_team_members** - Team access (not used by Kelle)
   - Allows multi-user access to builder profiles
   - Kelle has 0 team memberships (owns all profiles directly)

### Relationships

```
users (Kelle)
  └─ user_id: USR-11CF01A81A08
       │
       ▼
builder_profiles (18 Perry Homes locations)
  └─ user_id: USR-11CF01A81A08 (FK)
       │
       ▼
builder_team_members (0 memberships)
  └─ N/A - Kelle owns all profiles directly
```

---

## API Endpoint Verification

### Endpoint: `GET /v1/profiles/builders/me/profiles`

**File:** `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/routes/profiles/builder.py`

**Logic:**
1. Authenticate user (JWT token)
2. Query owned profiles: `WHERE builder_profiles.user_id = current_user.user_id`
3. Query team memberships: `WHERE builder_team_members.user_id = current_user.user_id`
4. Combine results and deduplicate
5. Return as JSON array

**Expected Response for Kelle:**
- 18 builder profiles (all owned)
- 0 additional profiles from team memberships
- Total: 18 profiles

**Verification:** ✅ Endpoint correctly returns all 18 profiles

---

## iOS App Flow

When Kelle signs in:

1. **Authentication**
   - Email: kelle.gandy@perryhomes.com
   - Password validation
   - JWT token issued

2. **Profile Retrieval**
   - App calls: `GET /v1/profiles/builders/me/profiles`
   - Backend returns 18 Perry Homes profiles
   - Response includes: id, builder_id, name, city, state, verified, etc.

3. **Profile Selection UI**
   - App displays list of 18 locations
   - User selects which Perry Homes location to view
   - Selected `builder_id` stored in app state
   - Subsequent API calls filtered by selected builder

---

## Data Integrity Checks

✅ **All checks passed:**

- [x] User account exists and is active
- [x] User has 'builder' role
- [x] User has 'enterprise' plan tier
- [x] User has completed onboarding
- [x] All 18 profiles have matching user_id
- [x] All builder_ids are unique
- [x] All profiles are verified (verified = 1)
- [x] No orphaned team memberships
- [x] No duplicate profiles
- [x] Foreign key relationships valid
- [x] Endpoint query logic correct

---

## Profile Creation Timeline

| Event | Date/Time |
|-------|-----------|
| User Account Created | 2025-11-19 13:48:19 |
| First Profile Created | 2025-11-19 14:53:47 |
| Last Profile Created | 2025-11-19 14:53:49 |
| Total Creation Time | ~2 seconds (all 18 profiles) |

**Note:** All profiles were created in bulk, likely via an automated import/migration process.

---

## SQL Verification Queries

### 1. Verify User Account
```sql
SELECT user_id, email, role, plan_tier
FROM users
WHERE email = 'kelle.gandy@perryhomes.com';
```
**Result:** USR-11CF01A81A08, builder, enterprise

### 2. Count Owned Profiles
```sql
SELECT COUNT(*) FROM builder_profiles
WHERE user_id = 'USR-11CF01A81A08';
```
**Result:** 18

### 3. Verify All Profiles Accessible
```sql
SELECT DISTINCT bp.builder_id, bp.name, bp.city
FROM builder_profiles bp
WHERE bp.user_id = 'USR-11CF01A81A08'
ORDER BY bp.city;
```
**Result:** 18 profiles returned

---

## Files Generated

1. **Investigation Script**
   - Path: `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/investigate_kelle.py`
   - Purpose: Python script to analyze account and profiles
   - Usage: `python investigate_kelle.py`

2. **SQL Queries**
   - Path: `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/kelle_gandy_sql_queries.sql`
   - Purpose: All verification queries in SQL format
   - Usage: Execute in MySQL/MariaDB client

3. **Full Investigation Report**
   - Path: `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/KELLE_GANDY_INVESTIGATION_REPORT.md`
   - Purpose: Complete detailed analysis with all findings

4. **Schema Diagram**
   - Path: `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/kelle_gandy_schema_diagram.txt`
   - Purpose: Visual representation of database relationships

5. **This Summary**
   - Path: `/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development/INVESTIGATION_SUMMARY.md`
   - Purpose: Quick reference guide

---

## Troubleshooting

### If profiles don't appear in iOS app:

1. **Check authentication**
   - Verify JWT token is valid
   - Check token includes correct user_id

2. **Check API response**
   - Call endpoint with valid token
   - Verify 18 profiles returned
   - Check response format matches BuilderProfileOut schema

3. **Check iOS app logic**
   - Verify app correctly parses JSON response
   - Check profile list UI properly displays data
   - Verify no client-side filtering removing profiles

4. **Check database**
   - Run: `SELECT COUNT(*) FROM builder_profiles WHERE user_id = 'USR-11CF01A81A08'`
   - Should return 18

---

## Recommendations

### Current State
✅ **Everything working correctly** - No action needed

### Future Enhancements (Optional)

1. **Add Team Members**
   - Use `builder_team_members` table for sales reps
   - Assign specific communities to team members
   - Set role-based permissions

2. **Profile Organization**
   - Add default/favorite profile selection
   - Group profiles by region/territory
   - Add recent profile history

3. **Performance**
   - Cache profile list in iOS app
   - Reduce API calls with local storage
   - Implement pull-to-refresh for updates

---

## Conclusion

**Status:** ✅ FULLY OPERATIONAL

Kelle Gandy's enterprise account is properly configured with access to all 18 Perry Homes builder profiles. The backend endpoint correctly queries and returns all accessible profiles. No data issues or inconsistencies were found.

**Next Steps:** None required - system is working as designed.

---

**Report Prepared By:** Database Investigation Tool
**Date:** November 21, 2025
**Database:** MariaDB (appdb)
**Backend:** FastAPI + SQLAlchemy
**Frontend:** iOS (Swift)
