# iOS Backend Alignment Verification

**Date:** 2025-11-11
**Status:** ✅ FULLY ALIGNED

---

## Summary

All three profile types (Builder, Community, Sales Rep) are now fully aligned between iOS SwiftUI models, backend Pydantic schemas, SQLAlchemy models, and database tables.

---

## ✅ Builder Profiles - FULLY ALIGNED

### API Endpoint
- **iOS sends to:** `POST /v1/profiles/builders/{user_id}`
- **Backend route:** `routes/profiles/builder.py`
- **Method:** `create_builder_profile()`

### Schema Alignment

| Field | iOS Model | Backend Schema | Database Column | Data Type | Match |
|-------|-----------|----------------|-----------------|-----------|-------|
| name | ✅ | ✅ | ✅ name | VARCHAR(255) | ✅ |
| website | ✅ | ✅ | ✅ website | VARCHAR(1024) | ✅ |
| specialties | ✅ | ✅ | ✅ specialties | JSON | ✅ |
| rating | ✅ | ✅ | ✅ rating | FLOAT | ✅ |
| communities_served | ✅ | ✅ | ✅ communities_served | JSON | ✅ |
| about | ✅ | ✅ | ✅ about | TEXT | ✅ |
| phone | ✅ | ✅ | ✅ phone | VARCHAR(64) | ✅ |
| email | ✅ | ✅ | ✅ email | VARCHAR(255) | ✅ |
| address | ✅ | ✅ | ✅ address | VARCHAR(255) | ✅ |
| city | ✅ | ✅ | ✅ city | VARCHAR(255) | ✅ |
| state | ✅ | ✅ | ✅ state | VARCHAR(64) | ✅ |
| postal_code | ✅ | ✅ | ✅ postal_code | VARCHAR(20) | ✅ |
| verified | ✅ | ✅ | ✅ verified | INT | ✅ |
| title | ✅ | ✅ | ✅ title | VARCHAR(128) | ✅ |
| bio | ✅ | ✅ | ✅ bio | TEXT | ✅ |
| socials | ✅ | ✅ | ✅ socials | JSON | ✅ |

### Additional Database Fields (auto-generated)
- `id` - Primary key (INT AUTO_INCREMENT)
- `build_id` - Unique builder identifier (VARCHAR(64), format: B_329_XXX_XXX_XXX_XXX)
- `user_id` - Foreign key to users.id (INT, UNIQUE)
- `created_at` - Timestamp (DATETIME)
- `updated_at` - Timestamp (DATETIME)

### Foreign Key Constraints
- ✅ `builder_profiles.user_id` → `users.id` ON DELETE CASCADE

### Unique Indexes
- ✅ `build_id` (UNIQUE)
- ✅ `user_id` (UNIQUE)

### iOS Form Fields Mapped
```swift
BuilderProfileCreate(
    name: companyName,                    // ✅ Maps to builder_profiles.name
    website: websiteUrl,                  // ✅ Maps to builder_profiles.website
    about: aboutCompany,                  // ✅ Maps to builder_profiles.about
    phone: companyPhone,                  // ✅ Maps to builder_profiles.phone
    email: companyEmail,                  // ✅ Maps to builder_profiles.email
    address: companyAddress,              // ✅ Maps to builder_profiles.address
    city: companyCity,                    // ✅ Maps to builder_profiles.city
    state: companyState,                  // ✅ Maps to builder_profiles.state
    postalCode: companyPostalCode         // ✅ Maps to builder_profiles.postal_code
)
```

---

## ✅ Community Profiles - FULLY ALIGNED

### API Endpoint
- **iOS sends to:** `POST /v1/profiles/communities`
- **Backend route:** `routes/profiles/community.py`
- **Method:** `create_community()`

### Schema Alignment

| Field | iOS Model | Backend Schema | Database Column | Data Type | Match |
|-------|-----------|----------------|-----------------|-----------|-------|
| name | ✅ | ✅ | ✅ name | VARCHAR(255) | ✅ |
| city | ✅ | ✅ | ✅ city | VARCHAR(255) | ✅ |
| state | ✅ | ✅ | ✅ state | VARCHAR(64) | ✅ |
| postal_code | ✅ | ✅ | ✅ postal_code | VARCHAR(20) | ✅ |
| community_dues | ✅ | ✅ | ✅ community_dues | VARCHAR(64) | ✅ |
| tax_rate | ✅ | ✅ | ✅ tax_rate | VARCHAR(32) | ✅ |
| monthly_fee | ✅ | ✅ | ✅ monthly_fee | VARCHAR(64) | ✅ |
| about | ✅ | ✅ | ✅ about | TEXT | ✅ |
| homes | ✅ | ✅ | ✅ homes | INT | ✅ |
| residents | ✅ | ✅ | ✅ residents | INT | ✅ |
| founded_year | ✅ | ✅ | ✅ founded_year | INT | ✅ |
| member_count | ✅ | ✅ | ✅ member_count | INT | ✅ |
| development_stage | ✅ | ✅ | ✅ development_stage | VARCHAR(64) | ✅ |
| enterprise_number_hoa | ✅ | ✅ | ✅ enterprise_number_hoa | VARCHAR(255) | ✅ |
| intro_video_url | ✅ | ✅ | ✅ intro_video_url | VARCHAR(1024) | ✅ |
| community_website_url | ✅ | ✅ | ✅ community_website_url | VARCHAR(1024) | ✅ |
| amenity_names | ✅ | ✅ | (creates amenities) | Array→Relations | ✅ |

### iOS Form Fields Mapped
```swift
CommunityCreate(
    name: hoaName,                            // ✅ Maps to communities.name
    city: hoaCity,                            // ✅ Maps to communities.city
    state: hoaState,                          // ✅ Maps to communities.state
    postalCode: postalCode,                   // ✅ Maps to communities.postal_code
    communityDues: communityDues,             // ✅ Maps to communities.community_dues
    taxRate: taxRate,                         // ✅ Maps to communities.tax_rate
    monthlyFee: monthlyFee,                   // ✅ Maps to communities.monthly_fee
    about: aboutCommunity,                    // ✅ Maps to communities.about
    homes: toIntOrNil(totalHomes),            // ✅ Maps to communities.homes
    residents: toIntOrNil(totalResidents),    // ✅ Maps to communities.residents
    foundedYear: toIntOrNil(foundedYear),     // ✅ Maps to communities.founded_year
    memberCount: toIntOrNil(memberCount),     // ✅ Maps to communities.member_count
    developmentStage: developmentStage,       // ✅ Maps to communities.development_stage
    enterpriseNumberHoa: enterpriseNumberHOA, // ✅ Maps to communities.enterprise_number_hoa
    introVideoUrl: introVideoUrl,             // ✅ Maps to communities.intro_video_url
    communityWebsiteUrl: communityWebsiteUrl, // ✅ Maps to communities.community_website_url
    amenityNames: amenityNames                // ✅ Creates community_amenities records
)
```

---

## ✅ Sales Rep Profiles - FULLY ALIGNED

### API Endpoint
- **iOS sends to:** `POST /v1/profiles/sales-reps`
- **Backend route:** `routes/profiles/sales_rep.py`
- **Method:** `create_sales_rep()`

### Schema Alignment

| Field | iOS Model | Backend Schema | Database Column | Data Type | Match |
|-------|-----------|----------------|-----------------|-----------|-------|
| full_name | ✅ | ✅ | ✅ full_name | VARCHAR(255) | ✅ |
| builder_id | ✅ | ✅ | ✅ builder_id | BIGINT UNSIGNED | ✅ |
| community_id | ✅ | ✅ | ✅ community_id | BIGINT UNSIGNED | ✅ |
| title | ✅ | ✅ | ✅ title | VARCHAR(128) | ✅ |
| email | ✅ | ✅ | ✅ email | VARCHAR(255) | ✅ |
| phone | ✅ | ✅ | ✅ phone | VARCHAR(64) | ✅ |
| avatar_url | ✅ | ✅ | ✅ avatar_url | VARCHAR(1024) | ✅ |
| region | ✅ | ✅ | ✅ region | VARCHAR(128) | ✅ |
| office_address | ✅ | ✅ | ✅ office_address | VARCHAR(255) | ✅ |
| verified | ✅ | ✅ | ✅ verified | BOOLEAN | ✅ |

### Foreign Key Constraints
- ✅ `sales_reps.builder_id` → `builder_profiles.id` ON DELETE CASCADE
- ✅ `sales_reps.community_id` → `communities.id` ON DELETE CASCADE (nullable)

### iOS Form Fields Mapped
```swift
SalesRepProfileCreate(
    fullName: repFirstName + " " + repLastName,  // ✅ Maps to sales_reps.full_name
    builderId: Int(repBuilderId),                // ✅ Maps to sales_reps.builder_id
    title: repTitle,                              // ✅ Maps to sales_reps.title
    email: repEmail,                              // ✅ Maps to sales_reps.email
    phone: repPhone,                              // ✅ Maps to sales_reps.phone
    region: repRegion,                            // ✅ Maps to sales_reps.region
    officeAddress: repOfficeAddress,              // ✅ Maps to sales_reps.office_address
    communityId: Int(repCommunityId)              // ✅ Maps to sales_reps.community_id
)
```

---

## Migrations Applied

1. ✅ `ce3f638a0c53` - Fix builder_profiles foreign key to use user_id
2. ✅ `682d5b1ee23a` - Add state and community_website_url to communities
3. ✅ `44f379a49ddf` - Add development_stage and enterprise_number_hoa to communities
4. ✅ `922b25005b74` - Add city, state, postal_code to builder_profiles
5. ✅ `2ab2d90ffbc5` - Update builder_profiles schema to match model (rename columns, add new fields)

---

## Fixes Applied

### 1. Model Data Type Fix
**File:** `model/profiles/builder.py`

**Before:**
```python
user_id = Column(MyBIGINT(unsigned=True), ForeignKey("users.id", ...))
```

**After:**
```python
user_id = Column(Integer, ForeignKey("users.id", ...))
```

**Reason:** Match database `users.id` data type (INT)

### 2. Database Schema Update
**Migration:** `2ab2d90ffbc5_update_builder_profiles_schema_to_match_.py`

**Changes:**
- Renamed `display_name` → `name`
- Renamed `website_url` → `website`
- Added `build_id` (unique UUID-based identifier)
- Added 13 new fields: `specialties`, `rating`, `communities_served`, `about`, `phone`, `email`, `address`, `verified`, `title`, `socials`
- Dropped deprecated: `logo_url`, `service_area`
- Kept existing: `bio`, `city`, `state`, `postal_code`

---

## Test Checklist

### Builder Profile Creation
- [ ] iOS can submit builder form
- [ ] Backend creates builder_profiles record
- [ ] All fields properly saved
- [ ] Foreign key to users.id works
- [ ] build_id auto-generated
- [ ] onboarding_completed flag set

### Community Profile Creation
- [ ] iOS can submit community form
- [ ] Backend creates communities record
- [ ] Amenities properly created from amenity_names array
- [ ] Development stage dropdown values saved
- [ ] Enterprise number saved

### Sales Rep Profile Creation
- [ ] iOS can submit sales rep form
- [ ] Backend creates sales_reps record
- [ ] builder_id foreign key validated
- [ ] Optional community_id works
- [ ] Full name concatenated correctly

---

## Next Steps

1. **End-to-End Testing:** Test actual form submissions from iOS app
2. **Data Validation:** Verify all fields save correctly
3. **Error Handling:** Test validation errors (missing required fields, invalid builder_id, etc.)
4. **Navigation:** Verify post-submission navigation to correct dashboards

---

## Contact

For questions or issues, refer to:
- `docs/SALES_REP_INTEGRATION.md` - Sales Rep integration details
- `routes/profiles/builder.py` - Builder profile API
- `routes/profiles/community.py` - Community profile API
- `routes/profiles/sales_rep.py` - Sales Rep API
