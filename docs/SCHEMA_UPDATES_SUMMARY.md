# Database Schema Updates for Collector Alignment

## Overview

This document summarizes the database schema updates made to align the database tables with the fields that the collectors search for. Three migrations were created to expand the Property, Builder, and SalesRep tables.

---

## 1. Property Table Updates

**Migration:** `alembic/versions/i5j6k7l8m9n0_expand_property_table_for_collector.py`
**Model:** `model/property/property.py`

### Fields Added (40+ new columns):

#### Property Classification
- `property_type` - single_family, townhome, condo, etc.
- `listing_status` - available, pending, under_contract, sold

#### Structural Details
- `stories` - Number of stories/floors
- `garage_spaces` - Number of garage parking spaces

#### Lot Characteristics
- `corner_lot` - Boolean: Is this a corner lot?
- `cul_de_sac` - Boolean: Is lot on a cul-de-sac?
- `lot_backing` - What lot backs to (greenbelt, pond, street, etc.)
- `views` - Views from property

#### School Information
- `school_district` - School district name
- `elementary_school` - Zoned elementary school
- `middle_school` - Zoned middle school
- `high_school` - Zoned high school
- `school_ratings` - JSON: School ratings data

#### Builder-Specific Information
- `model_home` - Boolean: Is this a model home?
- `quick_move_in` - Boolean: Quick move-in/inventory home?
- `construction_stage` - pre_construction, under_construction, completed
- `estimated_completion` - Expected completion date (string)
- `builder_plan_name` - Builder floor plan name
- `builder_series` - Builder series/collection name
- `elevation_options` - Available elevation options

#### Interior Features
- `flooring_types` - Types of flooring (hardwood, tile, carpet)
- `countertop_materials` - Countertop materials (granite, quartz, etc.)
- `appliances` - Included appliances
- `game_room` - Boolean: Has game room?
- `study_office` - Boolean: Has study/office?
- `bonus_rooms` - Additional bonus rooms

#### Outdoor Amenities
- `pool_type` - private, community, none
- `covered_patio` - Boolean: Has covered patio?
- `outdoor_kitchen` - Boolean: Has outdoor kitchen?
- `landscaping` - Landscaping description

#### Pricing & Market Information
- `price_per_sqft` - Price per square foot
- `days_on_market` - Number of days listed
- `builder_incentives` - Current builder incentives
- `upgrades_included` - Upgrades included in price
- `upgrades_value` - Estimated value of upgrades

#### HOA & Restrictions
- `hoa_fee_monthly` - Monthly HOA fee
- `pet_restrictions` - Pet policy and restrictions
- `lease_allowed` - Boolean: Is leasing allowed?

#### Energy & Utilities
- `energy_rating` - Energy efficiency rating
- `internet_providers` - Available internet providers

#### Tax & Financial
- `annual_property_tax` - Estimated annual property tax
- `assumable_loan` - Boolean: Is loan assumable?

#### Media & Virtual Tours
- `virtual_tour_url` - Virtual tour URL
- `floor_plan_url` - Floor plan image/PDF URL
- `matterport_link` - Matterport 3D tour link

#### Availability & Showing
- `move_in_date` - Available move-in date (string)
- `showing_instructions` - Instructions for showing the property

#### Collection Metadata
- `source_url` - URL where property data was collected
- `data_confidence` - Confidence score of collected data (0.0-1.0)

### Indexes Added:
- `ix_properties_property_type`
- `ix_properties_listing_status`
- `ix_properties_construction_stage`
- `ix_properties_school_district`

---

## 2. Builder Profile Table Updates

**Migration:** `alembic/versions/j6k7l8m9n0o1_expand_builder_table_for_collector.py`
**Model:** `model/profiles/builder.py`

### Fields Added:

#### Primary Description
- `description` - Primary builder description (for collector)

#### Address Update
- **RENAMED:** `address` → `headquarters_address` (to match collector expectations)

#### Company Information
- `founded_year` - Year the builder was founded
- `employee_count` - Number of employees
- `service_areas` - JSON: Geographic areas served

#### Pricing Information
- `price_range_min` - Minimum home price range
- `price_range_max` - Maximum home price range

#### Review Metrics
- `review_count` - Number of reviews

### Indexes Added:
- `ix_builder_profiles_founded_year`
- `ix_builder_profiles_price_range_min`
- `ix_builder_profiles_price_range_max`

### Migration Notes:
- The migration automatically copies existing `address` data to the new `headquarters_address` column before dropping the old column
- Downgrade reverses this process safely

---

## 3. Sales Rep Table Updates

**Migration:** `alembic/versions/k7l8m9n0o1p2_expand_sales_rep_table_for_collector.py`
**Model:** `model/profiles/sales_rep.py`

### Fields Added:

#### Contact Information
- `office_phone` - Office phone number (separate from personal phone)

#### Profile Information
- `bio` - Sales rep biography

#### Status Tracking
- `is_active` - Boolean: Whether sales rep is currently active

### Indexes Added:
- `ix_sales_reps_is_active`

---

## Field Mapping Reference

### Property Collector → Database

| Collector Field | Database Column | Status |
|----------------|-----------------|--------|
| `title` | `title` | ✅ Matches |
| `address` | `address1` | ✅ Matches |
| `zip_code` | `postal_code` | ✅ Matches |
| `beds` | `bedrooms` | ✅ Matches |
| `baths` | `bathrooms` | ✅ Matches |
| `lot_size` | `lot_sqft` | ✅ Matches |
| `images` | `media_urls` | ✅ Matches |
| All 40+ new fields | New columns | ✅ Now matches |

### Builder Collector → Database

| Collector Field | Database Column | Status |
|----------------|-----------------|--------|
| `name` | `name` | ✅ Matches |
| `description` | `description` | ✅ Now matches |
| `headquarters_address` | `headquarters_address` | ✅ Now matches |
| `founded_year` | `founded_year` | ✅ Now matches |
| `employee_count` | `employee_count` | ✅ Now matches |
| `service_areas` | `service_areas` | ✅ Now matches |
| `price_range_min` | `price_range_min` | ✅ Now matches |
| `price_range_max` | `price_range_max` | ✅ Now matches |
| `review_count` | `review_count` | ✅ Now matches |

### Sales Rep Collector → Database

| Collector Field | Database Column | Status |
|----------------|-----------------|--------|
| `name` | `first_name` + `last_name` | ✅ Matches |
| `photo_url` | `avatar_url` | ✅ Matches |
| `office_phone` | `office_phone` | ✅ Now matches |
| `bio` | `bio` | ✅ Now matches |
| `is_active` | `is_active` | ✅ Now matches |

---

## Migration Execution Order

To apply these changes to your database, run migrations in order:

```bash
# 1. Property table expansion
alembic upgrade i5j6k7l8m9n0

# 2. Builder table expansion
alembic upgrade j6k7l8m9n0o1

# 3. Sales rep table expansion
alembic upgrade k7l8m9n0o1p2
```

Or simply upgrade to the latest:

```bash
alembic upgrade head
```

---

## Remaining Work

### Collector Field Mapping Updates Required:

1. **Property Collector** (`src/collection/property_collector.py`)
   - Update field mappings to use new column names
   - Ensure all 60+ fields are properly mapped

2. **Builder Collector** (`src/collection/builder_collector.py`)
   - Update `address` → `headquarters_address` mapping
   - Add mappings for new fields (founded_year, employee_count, etc.)
   - Map `description` field properly

3. **Sales Rep Collector** (`src/collection/sales_rep_collector.py`)
   - Add mappings for `office_phone`, `bio`, `is_active`
   - Ensure `photo_url` → `avatar_url` mapping is correct

---

## Benefits

After these updates:

1. ✅ **Property collector** can now store all 60+ fields it searches for
2. ✅ **Builder collector** has all company information fields
3. ✅ **Sales rep collector** has complete profile data
4. ✅ **Database schema** now fully aligned with collector capabilities
5. ✅ **No data loss** - all existing data preserved in migrations
6. ✅ **Indexed fields** for better query performance

---

## Testing Checklist

After running migrations:

- [ ] Run `alembic current` to verify migration version
- [ ] Check that all new columns exist in database
- [ ] Verify indexes were created
- [ ] Test collector runs to ensure data is saved properly
- [ ] Verify no existing data was lost
- [ ] Update API schemas if needed to expose new fields
- [ ] Update documentation for new fields

---

## Rollback Instructions

If needed, you can rollback each migration:

```bash
# Rollback sales rep changes
alembic downgrade j6k7l8m9n0o1

# Rollback builder changes
alembic downgrade i5j6k7l8m9n0

# Rollback property changes
alembic downgrade h4i5j6k7l8m9
```

**Note:** The builder migration rollback will restore the old `address` column from `headquarters_address` data.
