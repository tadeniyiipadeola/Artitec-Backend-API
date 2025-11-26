# Field Coverage Analysis: Database vs Collectors

## 🔍 Comprehensive Review of All Tables vs Collector Search Fields

---

## 1️⃣ BUILDER_PROFILES Table

### Database Columns (from `model/profiles/builder.py`)

| Column | Type | Collector Searches? | Status |
|--------|------|-------------------|--------|
| `id` | BIGINT | N/A (auto-generated) | ✅ N/A |
| `builder_id` | String(50) | N/A (auto-generated) | ✅ N/A |
| `user_id` | String(50) | N/A (assigned) | ✅ N/A |
| `name` | String(255) | ✅ YES | ✅ COVERED |
| `website` | String(1024) | ✅ YES | ✅ COVERED |
| `specialties` | JSON | ✅ YES | ✅ COVERED |
| `rating` | Float | ✅ YES | ✅ COVERED |
| `communities_served` | JSON | ❌ NO | ⚠️ **MISSING** |
| `about` | Text | ❌ NO (has `description`) | ⚠️ **MISMATCH** |
| `phone` | String(64) | ✅ YES | ✅ COVERED |
| `email` | String(255) | ✅ YES | ✅ COVERED |
| `address` | String(255) | ❌ NO (has `headquarters_address`) | ⚠️ **MISMATCH** |
| `city` | String(255) | ❌ NO | ⚠️ **MISSING** |
| `state` | String(64) | ❌ NO | ⚠️ **MISSING** |
| `postal_code` | String(20) | ❌ NO | ⚠️ **MISSING** |
| `verified` | Integer | N/A (admin sets) | ✅ N/A |
| `title` | String(128) | ❌ NO | ⚠️ **MISSING** |
| `bio` | Text | ❌ NO | ⚠️ **MISSING** |
| `socials` | JSON | ❌ NO | ⚠️ **MISSING** |

### Collector Searches (from `prompts.py:246-346`)

| Field in Prompt | Maps to DB Column | Status |
|----------------|-------------------|--------|
| `name` | `name` | ✅ MATCHES |
| `description` | ? `about` or `bio` | ⚠️ UNCLEAR |
| `website` | `website` | ✅ MATCHES |
| `phone` | `phone` | ✅ MATCHES |
| `email` | `email` | ✅ MATCHES |
| `headquarters_address` | ? `address` | ⚠️ MISMATCH |
| `founded_year` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `employee_count` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `service_areas` | ? `communities_served` | ⚠️ **UNCLEAR** |
| `price_range_min` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `price_range_max` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `rating` | `rating` | ✅ MATCHES |
| `review_count` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `awards` | → BuilderAward table | ✅ MATCHES |
| `certifications` | → BuilderCredential table | ✅ MATCHES |
| `communities` | ? `communities_served` | ⚠️ **UNCLEAR** |
| `home_plans` | → BuilderHomePlan table | ✅ MATCHES |

### ⚠️ CRITICAL ISSUES - Builder

1. **Missing DB Columns** being searched:
   - `founded_year` - Collector searches but NO DB column
   - `employee_count` - Collector searches but NO DB column
   - `price_range_min` - Collector searches but NO DB column
   - `price_range_max` - Collector searches but NO DB column
   - `review_count` - Collector searches but NO DB column

2. **Missing Searches** for existing DB columns:
   - `communities_served` (JSON) - DB has it, collector doesn't search
   - `city` - DB has it, collector doesn't search
   - `state` - DB has it, collector doesn't search
   - `postal_code` - DB has it, collector doesn't search
   - `title` - DB has it, collector doesn't search
   - `bio` - DB has it, collector doesn't search
   - `socials` (JSON) - DB has it, collector doesn't search

3. **Field Name Mismatches**:
   - Collector: `headquarters_address` vs DB: `address`
   - Collector: `description` vs DB: `about` or `bio`?

---

## 2️⃣ PROPERTIES Table

### Database Columns (from `model/property/property.py`)

| Column | Type | Collector Searches? | Status |
|--------|------|-------------------|--------|
| `id` | BIGINT | N/A (auto-generated) | ✅ N/A |
| `owner_id` | BIGINT | N/A (assigned) | ✅ N/A |
| `title` | String(140) | ✅ YES | ✅ COVERED |
| `description` | Text | ✅ YES | ✅ COVERED |
| `address1` | String(255) | ✅ YES (as `address`) | ✅ COVERED |
| `address2` | String(255) | ❌ NO | ⚠️ **MISSING** |
| `city` | String(120) | ✅ YES | ✅ COVERED |
| `state` | String(120) | ✅ YES | ✅ COVERED |
| `postal_code` | String(20) | ✅ YES (as `zip_code`) | ✅ COVERED |
| `latitude` | Float | ❌ NO | ⚠️ **MISSING** |
| `longitude` | Float | ❌ NO | ⚠️ **MISSING** |
| `price` | Numeric(12,2) | ✅ YES | ✅ COVERED |
| `bedrooms` | Integer | ✅ YES (as `beds`) | ✅ COVERED |
| `bathrooms` | Float | ✅ YES (as `baths`) | ✅ COVERED |
| `sqft` | Integer | ✅ YES | ✅ COVERED |
| `lot_sqft` | Integer | ✅ YES (as `lot_size`) | ✅ COVERED |
| `year_built` | Integer | ❌ NO | ⚠️ **MISSING** |
| `builder_id` | BIGINT | ✅ YES (linked) | ✅ COVERED |
| `community_id` | BIGINT | ✅ YES (linked) | ✅ COVERED |
| `has_pool` | Boolean | ✅ YES (as `pool_type`) | ✅ COVERED |
| `media_urls` | JSON | ✅ YES (as `images`) | ✅ COVERED |
| `listed_at` | TIMESTAMP | ❌ NO | ⚠️ **MISSING** |

### Collector Searches (from `prompts.py:420-563`)

**The property collector searches for 60+ fields, but many DON'T exist in the database!**

| Field in Prompt | DB Column Exists? | Status |
|----------------|-------------------|--------|
| `title` | ✅ YES | ✅ MATCHES |
| `address` | ✅ YES (`address1`) | ✅ MATCHES |
| `city` | ✅ YES | ✅ MATCHES |
| `state` | ✅ YES | ✅ MATCHES |
| `zip_code` | ✅ YES (`postal_code`) | ✅ MATCHES |
| `description` | ✅ YES | ✅ MATCHES |
| `property_type` | ❌ NO | ⚠️ **EXTRA** |
| `status` | ❌ NO | ⚠️ **EXTRA** |
| `price` | ✅ YES | ✅ MATCHES |
| `beds` | ✅ YES (`bedrooms`) | ✅ MATCHES |
| `baths` | ✅ YES (`bathrooms`) | ✅ MATCHES |
| `sqft` | ✅ YES | ✅ MATCHES |
| `lot_size` | ✅ YES (`lot_sqft`) | ✅ MATCHES |
| `stories` | ❌ NO | ⚠️ **EXTRA** |
| `garage_spaces` | ❌ NO | ⚠️ **EXTRA** |
| `corner_lot` | ❌ NO | ⚠️ **EXTRA** |
| `cul_de_sac` | ❌ NO | ⚠️ **EXTRA** |
| `lot_backing` | ❌ NO | ⚠️ **EXTRA** |
| `school_district` | ❌ NO | ⚠️ **EXTRA** |
| `elementary_school` | ❌ NO | ⚠️ **EXTRA** |
| `middle_school` | ❌ NO | ⚠️ **EXTRA** |
| `high_school` | ❌ NO | ⚠️ **EXTRA** |
| `model_home` | ❌ NO | ⚠️ **EXTRA** |
| `quick_move_in` | ❌ NO | ⚠️ **EXTRA** |
| `construction_stage` | ❌ NO | ⚠️ **EXTRA** |
| `estimated_completion` | ❌ NO | ⚠️ **EXTRA** |
| `builder_plan_name` | ❌ NO | ⚠️ **EXTRA** |
| `price_per_sqft` | ❌ NO | ⚠️ **EXTRA** |
| `days_on_market` | ❌ NO | ⚠️ **EXTRA** |
| `builder_incentives` | ❌ NO | ⚠️ **EXTRA** |
| `upgrades_included` | ❌ NO | ⚠️ **EXTRA** |
| `upgrades_value` | ❌ NO | ⚠️ **EXTRA** |
| `hoa_fee` | ❌ NO | ⚠️ **EXTRA** |
| `virtual_tour_url` | ❌ NO | ⚠️ **EXTRA** |
| `floor_plan_url` | ❌ NO | ⚠️ **EXTRA** |
| `images` | ✅ YES (`media_urls`) | ✅ MATCHES |

### ⚠️ CRITICAL ISSUES - Property

**THE PROPERTY TABLE IS SEVERELY INCOMPLETE!**

The collector searches for 60+ fields but the database only has ~20 columns!

**Missing DB Columns** (searched but don't exist):
- `property_type`
- `status`
- `stories`
- `garage_spaces`
- `corner_lot`
- `cul_de_sac`
- `lot_backing`
- `school_district`
- `elementary_school`, `middle_school`, `high_school`
- `model_home`
- `quick_move_in`
- `construction_stage`
- `estimated_completion`
- `builder_plan_name`
- `price_per_sqft`
- `days_on_market`
- `builder_incentives`
- `upgrades_included`, `upgrades_value`
- `hoa_fee`
- `virtual_tour_url`, `floor_plan_url`

**Missing Searches** for existing columns:
- `address2` - DB has it, not searched
- `latitude`, `longitude` - DB has it, not searched
- `year_built` - DB has it, not searched
- `listed_at` - DB has it, not searched

---

## 3️⃣ SALES_REPS Table

### Database Columns (from `model/profiles/sales_rep.py`)

| Column | Type | Collector Searches? | Status |
|--------|------|-------------------|--------|
| `id` | BIGINT | N/A (auto-generated) | ✅ N/A |
| `sales_rep_id` | String(50) | N/A (auto-generated) | ✅ N/A |
| `user_id` | String(50) | N/A (linked) | ✅ N/A |
| `builder_id` | BIGINT | ✅ YES (linked) | ✅ COVERED |
| `community_id` | BIGINT | ✅ YES (linked) | ✅ COVERED |
| `first_name` | String(128) | ✅ YES (as `name`) | ✅ COVERED |
| `last_name` | String(128) | ✅ YES (as `name`) | ✅ COVERED |
| `title` | String(128) | ✅ YES | ✅ COVERED |
| `email` | String(255) | ✅ YES | ✅ COVERED |
| `phone` | String(64) | ✅ YES | ✅ COVERED |
| `avatar_url` | String(1024) | ✅ YES (as `photo_url`) | ✅ COVERED |
| `region` | String(128) | ❌ NO | ⚠️ **MISSING** |
| `office_address` | String(255) | ✅ YES | ✅ COVERED |
| `verified` | Boolean | N/A (admin sets) | ✅ N/A |

### Collector Searches (from `prompts.py:360-408`)

| Field in Prompt | Maps to DB Column | Status |
|----------------|-------------------|--------|
| `name` | `first_name` + `last_name` | ✅ MATCHES |
| `title` | `title` | ✅ MATCHES |
| `phone` | `phone` | ✅ MATCHES |
| `email` | `email` | ✅ MATCHES |
| `photo_url` | `avatar_url` | ✅ MATCHES |
| `office_address` | `office_address` | ✅ MATCHES |
| `office_phone` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `bio` | ❌ NOT IN DB | ⚠️ **EXTRA** |
| `is_active` | ❌ NOT IN DB | ⚠️ **EXTRA** |

### ⚠️ ISSUES - Sales Rep

1. **Missing DB Columns** being searched:
   - `office_phone` - Searched but no DB column
   - `bio` - Searched but no DB column
   - `is_active` - Searched but no DB column

2. **Missing Searches**:
   - `region` - DB has it, collector doesn't search

---

## 📊 SUMMARY OF ISSUES

### Builder Profile
- ❌ **5 fields searched** that don't exist in DB
- ❌ **7 DB columns** not being searched
- ❌ **Field name mismatches** need resolution

### Property
- ❌ **40+ fields searched** that don't exist in DB!
- ❌ **4 DB columns** not being searched
- 🚨 **CRITICAL: Property table needs major expansion**

### Sales Rep
- ❌ **3 fields searched** that don't exist in DB
- ❌ **1 DB column** not being searched
- ✅ Mostly aligned, minor issues

---

## 🔧 RECOMMENDATIONS

### Immediate Actions Required:

1. **Expand Property Table** - Add all missing columns that collector searches for
2. **Expand Builder Table** - Add missing columns (founded_year, employee_count, etc.)
3. **Update Collector Prompts** - Add searches for existing but unused DB columns
4. **Fix Field Name Mismatches** - Standardize naming between collector and DB
5. **Add Missing Sales Rep Fields** - Add office_phone, bio, is_active columns

### Priority:

1. **CRITICAL**: Property table expansion (40+ missing fields)
2. **HIGH**: Builder table updates (field mismatches and missing columns)
3. **MEDIUM**: Sales rep minor additions
4. **LOW**: Update collectors to search for latitude/longitude, etc.

