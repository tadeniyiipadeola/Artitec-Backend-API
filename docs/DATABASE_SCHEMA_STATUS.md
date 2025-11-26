# Database Schema Status - Collector Alignment

## Current Status

The database schema is **mostly complete** for collector requirements. An existing migration (`3509492dffbd_add_collection_tracking_columns.py`) already added most of the fields that collectors search for.

---

## What's Already in the Database

### Property Table - Already Added (20 fields)

✅ **From migration 3509492dffbd:**
- `property_type` - Type of property
- `stories` - Number of stories
- `garage_spaces` - Number of garage spaces
- `corner_lot` - Boolean: Is corner lot
- `cul_de_sac` - Boolean: On cul-de-sac
- `lot_backing` - What lot backs to
- `school_district` - School district name
- `elementary_school` - Elementary school
- `middle_school` - Middle school
- `high_school` - High school
- `school_ratings` - JSON school ratings
- `price_per_sqft` - Price per sqft
- `days_on_market` - Days listed
- `model_home` - Boolean: Model home
- `quick_move_in` - Boolean: Quick move-in
- `construction_stage` - Construction stage
- `estimated_completion` - Completion date
- `builder_incentives` - Builder incentives
- `upgrades_included` - Included upgrades
- `upgrades_value` - Value of upgrades

### Builder Profile Table - Already Added (4 fields)

✅ **From migration 3509492dffbd:**
- `founded_year` - Year founded
- `employee_count` - Number of employees
- `service_areas` - JSON service areas
- `review_count` - Number of reviews

### Sales Rep Table - Already Added (1 field)

✅ **From migration 3509492dffbd:**
- `is_active` - Boolean: Currently active

---

## What Still Needs to Be Added

### Property Table - Missing Fields (25+ remaining)

❌ **Still need to add:**
- `listing_status` - available, pending, under_contract, sold
- `views` - Views from property
- `builder_plan_name` - Builder floor plan name
- `builder_series` - Builder series/collection name
- `elevation_options` - Available elevation options
- `flooring_types` - Types of flooring
- `countertop_materials` - Countertop materials
- `appliances` - Included appliances
- `game_room` - Boolean: Has game room
- `study_office` - Boolean: Has study/office
- `bonus_rooms` - Additional bonus rooms
- `pool_type` - private, community, none
- `covered_patio` - Boolean: Has covered patio
- `outdoor_kitchen` - Boolean: Has outdoor kitchen
- `landscaping` - Landscaping description
- `hoa_fee_monthly` - Monthly HOA fee
- `pet_restrictions` - Pet restrictions
- `lease_allowed` - Boolean: Leasing allowed
- `energy_rating` - Energy efficiency rating
- `internet_providers` - Available ISPs
- `annual_property_tax` - Annual property tax
- `assumable_loan` - Boolean: Loan assumable
- `virtual_tour_url` - Virtual tour URL
- `floor_plan_url` - Floor plan URL
- `matterport_link` - Matterport 3D tour
- `move_in_date` - Available move-in date
- `showing_instructions` - Showing instructions
- `source_url` - Data source URL
- `data_confidence` - Data confidence score

### Builder Profile Table - Missing Fields (3 remaining)

❌ **Still need to add:**
- `description` - Primary description field (for collector)
- `headquarters_address` - Full HQ address (rename from `address`)
- `price_range_min` - Minimum price range
- `price_range_max` - Maximum price range

Note: `address` field exists but needs to be renamed to `headquarters_address` to match collector expectations.

### Sales Rep Table - Missing Fields (2 remaining)

❌ **Still need to add:**
- `office_phone` - Office phone number
- `bio` - Sales rep biography

---

## Model Status

### Models Updated ✅

All three models have been updated to include the new fields:
- ✅ `model/property/property.py` - Updated with all fields
- ✅ `model/profiles/builder.py` - Updated with all fields
- ✅ `model/profiles/sales_rep.py` - Updated with all fields

**Important:** The models now have fields that don't exist in the database yet. Migrations need to be created to add the missing fields.

---

## Next Steps

### 1. Create Minimal Migrations (Only Missing Fields)

Need to create 3 new migrations that add ONLY the fields not already in the database:

**Property Migration:**
- Add ~25 remaining fields (listing_status, views, builder_plan_name, etc.)
- Add indexes for commonly searched fields

**Builder Migration:**
- Add `description`, `price_range_min`, `price_range_max`
- Rename `address` → `headquarters_address`
- Add indexes

**Sales Rep Migration:**
- Add `office_phone`, `bio`

### 2. Update Collectors

After migrations are applied, update collectors to map fields correctly:

**Property Collector:**
- Map all 60+ fields to database columns
- Ensure `zip_code` → `postal_code`
- Ensure `beds` → `bedrooms`
- Ensure `baths` → `bathrooms`
- Ensure `lot_size` → `lot_sqft`
- Ensure `images` → `media_urls`

**Builder Collector:**
- Map `description` field properly
- Map `headquarters_address` (not `address`)
- Ensure all new fields are mapped

**Sales Rep Collector:**
- Map `office_phone`, `bio`, `is_active`
- Ensure `photo_url` → `avatar_url`

---

## Migration Sequence

The migration dependency chain should be:

```
931c766ea143 (add_status_history_table) [CURRENT HEAD]
    ↓
[NEW] Property remaining fields
    ↓
[NEW] Builder remaining fields + rename
    ↓
[NEW] Sales rep remaining fields
```

---

## Summary

**Good News:**
- 📊 Property table: 20/45 fields already exist (44%)
- 📊 Builder table: 4/12 fields already exist (33%)
- 📊 Sales Rep table: 1/3 fields already exist (33%)

**Action Required:**
1. Create 3 minimal migrations with only missing fields
2. Run migrations
3. Update collectors to use correct field mappings
4. Test collection to ensure data is saved properly

**Models:**
- ✅ All models already updated and ready
- Models currently have more fields than database (will match after migrations)
