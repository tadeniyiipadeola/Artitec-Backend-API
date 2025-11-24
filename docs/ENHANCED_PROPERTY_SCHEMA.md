# Enhanced Property Schema - Data Collector Updates

**Date**: November 24, 2025
**Purpose**: Comprehensive property data collection with buyer-focused fields
**Status**: Ready for Implementation

---

## Overview

This document extends the Property model with **45+ additional fields** to capture comprehensive real estate data that buyers actually care about. These fields are prioritized by impact and ease of collection.

---

## Current vs Enhanced Schema

### Current Property Model (Baseline)
```python
class Property(Base):
    # IDs
    id, owner_id

    # Basic
    title, description

    # Location
    address1, address2, city, state, postal_code
    latitude, longitude

    # Specs
    price, bedrooms, bathrooms, sqft, lot_sqft, year_built
    has_pool

    # Relationships
    builder_id, community_id

    # Status
    property_status, move_in_ready

    # Media
    media_urls (JSON)

    # Timestamps
    created_at, updated_at, listed_at
```

### Enhanced Property Model (Complete)
```python
class Property(Base):
    # ... (all existing fields) ...

    # NEW FIELDS BELOW:

    # Property Type & Style (Phase 1)
    property_type           # 'single_family', 'townhome', 'condo'
    architectural_style     # 'modern', 'traditional', 'craftsman'
    stories                 # 1, 2, 3

    # Garage & Parking (Phase 1)
    garage_spaces           # 2, 3, 4
    garage_type             # 'attached', 'detached', 'tandem'

    # Lot Details (Phase 1)
    lot_dimensions          # '75x100 feet'
    corner_lot              # BOOLEAN
    cul_de_sac              # BOOLEAN
    lot_backing             # 'greenbelt', 'pond', 'street'
    lot_premium             # 'standard', 'premium', 'view_lot'

    # School Information (Phase 1)
    elementary_school
    middle_school
    high_school
    school_district
    school_ratings          # JSON: {'elementary': 9, 'middle': 8}

    # Pricing & Market (Phase 1)
    original_price
    price_per_sqft          # Calculated or collected
    days_on_market
    price_reduction_count
    incentives              # JSON: builder promotions

    # Builder-Specific (Phase 2)
    model_home              # BOOLEAN
    quick_move_in           # BOOLEAN (ready within 60 days)
    under_construction      # BOOLEAN
    spec_home               # BOOLEAN
    construction_stage      # 'foundation', 'framing', 'drywall'
    estimated_completion    # DATE
    build_start_date        # DATE
    builder_plan_name       # "The Oakmont"
    builder_series          # "Signature Series"
    builder_warranty_years  # INTEGER

    # Interior Features (Phase 3)
    flooring_types          # JSON: ['hardwood_main', 'carpet_bed']
    countertops             # 'granite', 'quartz', 'marble'
    appliances_included     # BOOLEAN
    smart_home_features     # JSON: ['thermostat', 'doorbell']
    fireplace_count         # INTEGER
    study_office            # BOOLEAN
    game_room               # BOOLEAN
    media_room              # BOOLEAN
    flex_room               # BOOLEAN

    # Outdoor Amenities (Phase 3)
    pool_type               # 'in_ground', 'infinity', 'spa'
    outdoor_kitchen         # BOOLEAN
    covered_patio           # BOOLEAN
    patio_sqft              # INTEGER
    sprinkler_system        # BOOLEAN
    fence_type              # 'wood', 'vinyl', 'iron', 'none'
    landscaping_status      # 'full', 'partial', 'sod_only'

    # HOA & Restrictions (Phase 3)
    hoa_fee_monthly         # Property-specific fee
    hoa_includes            # JSON: ['lawn_care', 'pool_access']
    pet_restrictions        # TEXT
    lease_allowed           # BOOLEAN
    minimum_lease_term      # INTEGER (months)

    # Energy & Utilities (Phase 4)
    energy_rating           # 'energy_star', 'leed_certified'
    water_source            # 'city', 'well'
    sewer_type              # 'city', 'septic'
    gas_type                # 'natural_gas', 'propane'
    internet_providers      # JSON: ['comcast', 'att_fiber']
    internet_speed          # 'fiber_1gbps', 'cable_500mbps'

    # Special Features (Phase 4)
    view_description        # 'golf_course', 'lake', 'preserve'
    elevation               # 'A', 'B', 'C' (design variations)
    upgrades_estimated_value # DECIMAL
    design_center_completed  # BOOLEAN
    structural_options      # JSON: added rooms/features

    # Virtual & Media (Phase 4)
    virtual_tour_url
    video_walkthrough_url
    floor_plan_url
    matterport_url
    drone_video_url

    # Financial (Phase 4)
    annual_property_tax
    tax_year
    homestead_exempt        # BOOLEAN
    assumable_loan          # BOOLEAN
    builder_financing_rate  # DECIMAL(5,3)

    # Availability (Phase 4)
    showing_instructions    # TEXT
    occupancy_status        # 'vacant', 'occupied', 'model_home'
```

---

## Database Migration - Phase 1 (Priority Fields)

### Migration Script: `20251124_enhance_properties_phase1.sql`

```sql
-- ============================================================
-- Phase 1: Core Property Enhancements
-- Priority: HIGH - Most buyer-facing fields
-- ============================================================

USE artitec;

-- Property Type & Style
ALTER TABLE properties
ADD COLUMN property_type VARCHAR(50) AFTER description
    COMMENT 'single_family, townhome, condo, duplex',
ADD COLUMN architectural_style VARCHAR(50) AFTER property_type
    COMMENT 'modern, traditional, craftsman, mediterranean',
ADD COLUMN stories INTEGER AFTER year_built
    COMMENT 'Number of floors (1, 2, 3)';

-- Garage & Parking
ALTER TABLE properties
ADD COLUMN garage_spaces INTEGER AFTER stories
    COMMENT 'Number of garage spaces (0, 1, 2, 3, 4)',
ADD COLUMN garage_type VARCHAR(50) AFTER garage_spaces
    COMMENT 'attached, detached, tandem, carport';

-- Lot Details
ALTER TABLE properties
ADD COLUMN lot_dimensions VARCHAR(100) AFTER lot_sqft
    COMMENT 'e.g., 75x100 feet',
ADD COLUMN corner_lot BOOLEAN DEFAULT FALSE AFTER lot_dimensions
    COMMENT 'TRUE if corner lot',
ADD COLUMN cul_de_sac BOOLEAN DEFAULT FALSE AFTER corner_lot
    COMMENT 'TRUE if on cul-de-sac',
ADD COLUMN lot_backing VARCHAR(50) AFTER cul_de_sac
    COMMENT 'greenbelt, pond, street, neighbor, preserve',
ADD COLUMN lot_premium VARCHAR(50) AFTER lot_backing
    COMMENT 'standard, premium, view_lot';

-- School Information (Critical for families)
ALTER TABLE properties
ADD COLUMN elementary_school VARCHAR(255) AFTER postal_code,
ADD COLUMN middle_school VARCHAR(255) AFTER elementary_school,
ADD COLUMN high_school VARCHAR(255) AFTER middle_school,
ADD COLUMN school_district VARCHAR(255) AFTER high_school,
ADD COLUMN school_ratings JSON AFTER school_district
    COMMENT 'JSON: {elementary: 9, middle: 8, high: 9}';

-- Pricing & Market Data
ALTER TABLE properties
ADD COLUMN original_price DECIMAL(10,2) AFTER price
    COMMENT 'Initial listing price',
ADD COLUMN price_per_sqft DECIMAL(10,2) AFTER original_price
    COMMENT 'Calculated: price / sqft',
ADD COLUMN days_on_market INTEGER DEFAULT 0 AFTER listed_at
    COMMENT 'Days since first listed',
ADD COLUMN price_reduction_count INTEGER DEFAULT 0 AFTER days_on_market
    COMMENT 'Number of price reductions',
ADD COLUMN incentives JSON AFTER price_reduction_count
    COMMENT 'JSON array of builder incentives';

-- Builder-Specific Flags
ALTER TABLE properties
ADD COLUMN model_home BOOLEAN DEFAULT FALSE AFTER property_status
    COMMENT 'TRUE if this is a model home',
ADD COLUMN quick_move_in BOOLEAN DEFAULT FALSE AFTER model_home
    COMMENT 'TRUE if ready within 60 days',
ADD COLUMN under_construction BOOLEAN DEFAULT FALSE AFTER quick_move_in
    COMMENT 'TRUE if currently being built',
ADD COLUMN spec_home BOOLEAN DEFAULT FALSE AFTER under_construction
    COMMENT 'TRUE if spec built (not custom)';

-- Add indexes for common queries
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_stories ON properties(stories);
CREATE INDEX idx_properties_garage ON properties(garage_spaces);
CREATE INDEX idx_properties_school_district ON properties(school_district);
CREATE INDEX idx_properties_price_sqft ON properties(price_per_sqft);
CREATE INDEX idx_properties_days_market ON properties(days_on_market);
CREATE INDEX idx_properties_quick_move ON properties(quick_move_in);
CREATE INDEX idx_properties_model ON properties(model_home);

-- Update existing records with default values
UPDATE properties
SET
    property_type = 'single_family',  -- Default assumption
    stories = CASE
        WHEN sqft < 2000 THEN 1
        ELSE 2
    END,
    garage_spaces = 2,  -- Default assumption
    corner_lot = FALSE,
    cul_de_sac = FALSE,
    days_on_market = DATEDIFF(NOW(), COALESCE(listed_at, created_at)),
    price_per_sqft = CASE
        WHEN sqft > 0 THEN ROUND(price / sqft, 2)
        ELSE NULL
    END
WHERE property_type IS NULL;

COMMIT;
```

---

## Database Migration - Phase 2 (Builder Features)

### Migration Script: `20251125_enhance_properties_phase2.sql`

```sql
-- ============================================================
-- Phase 2: Builder-Specific Features
-- Priority: HIGH - Critical for new construction
-- ============================================================

USE artitec;

-- Construction Timeline
ALTER TABLE properties
ADD COLUMN construction_stage VARCHAR(50) AFTER under_construction
    COMMENT 'not_started, foundation, framing, drywall, completed',
ADD COLUMN estimated_completion DATE AFTER construction_stage
    COMMENT 'Expected completion date for under-construction',
ADD COLUMN build_start_date DATE AFTER estimated_completion
    COMMENT 'Date construction began',
ADD COLUMN build_completion_date DATE AFTER build_start_date
    COMMENT 'Date construction completed';

-- Builder Plan Information
ALTER TABLE properties
ADD COLUMN builder_plan_name VARCHAR(255) AFTER model_name
    COMMENT 'Floor plan name: The Oakmont, The Madison',
ADD COLUMN builder_series VARCHAR(255) AFTER builder_plan_name
    COMMENT 'Series: Signature, Executive, Classic',
ADD COLUMN builder_warranty_years INTEGER AFTER builder_series
    COMMENT 'Years of builder warranty (1, 2, 10)',
ADD COLUMN elevation VARCHAR(50) AFTER builder_warranty_years
    COMMENT 'Design elevation: A, B, C, D';

-- Add indexes
CREATE INDEX idx_properties_construction_stage ON properties(construction_stage);
CREATE INDEX idx_properties_completion_date ON properties(estimated_completion);
CREATE INDEX idx_properties_plan_name ON properties(builder_plan_name);

COMMIT;
```

---

## Database Migration - Phase 3 (Amenities & Features)

### Migration Script: `20251126_enhance_properties_phase3.sql`

```sql
-- ============================================================
-- Phase 3: Interior/Exterior Amenities
-- Priority: MEDIUM - Value-add features
-- ============================================================

USE artitec;

-- Interior Features
ALTER TABLE properties
ADD COLUMN flooring_types JSON AFTER bathrooms
    COMMENT 'JSON: [hardwood_main, carpet_bedrooms, tile_wet]',
ADD COLUMN countertops VARCHAR(50) AFTER flooring_types
    COMMENT 'granite, quartz, marble, laminate',
ADD COLUMN appliances_included BOOLEAN DEFAULT FALSE AFTER countertops,
ADD COLUMN smart_home_features JSON AFTER appliances_included
    COMMENT 'JSON: [smart_thermostat, ring_doorbell, security]',
ADD COLUMN fireplace_count INTEGER DEFAULT 0 AFTER smart_home_features,
ADD COLUMN study_office BOOLEAN DEFAULT FALSE AFTER fireplace_count
    COMMENT 'Dedicated study/office room',
ADD COLUMN game_room BOOLEAN DEFAULT FALSE AFTER study_office
    COMMENT 'Upstairs game room',
ADD COLUMN media_room BOOLEAN DEFAULT FALSE AFTER game_room
    COMMENT 'Dedicated media/theater room',
ADD COLUMN flex_room BOOLEAN DEFAULT FALSE AFTER media_room
    COMMENT 'Flexible use room';

-- Outdoor Amenities
ALTER TABLE properties
ADD COLUMN pool_type VARCHAR(50) AFTER has_pool
    COMMENT 'in_ground, above_ground, infinity, spa',
ADD COLUMN outdoor_kitchen BOOLEAN DEFAULT FALSE AFTER pool_type,
ADD COLUMN covered_patio BOOLEAN DEFAULT FALSE AFTER outdoor_kitchen,
ADD COLUMN patio_sqft INTEGER AFTER covered_patio,
ADD COLUMN sprinkler_system BOOLEAN DEFAULT FALSE AFTER patio_sqft,
ADD COLUMN fence_type VARCHAR(50) AFTER sprinkler_system
    COMMENT 'wood, vinyl, iron, none',
ADD COLUMN landscaping_status VARCHAR(50) AFTER fence_type
    COMMENT 'full, partial, sod_only, none';

-- HOA & Restrictions (Property-specific)
ALTER TABLE properties
ADD COLUMN hoa_fee_monthly DECIMAL(10,2) AFTER community_id
    COMMENT 'Property-specific HOA fee (may differ from community)',
ADD COLUMN hoa_includes JSON AFTER hoa_fee_monthly
    COMMENT 'JSON: [lawn_care, pool_access, trash, security]',
ADD COLUMN pet_restrictions VARCHAR(255) AFTER hoa_includes
    COMMENT 'no_pets, 2_pets_max, breed_restrictions',
ADD COLUMN lease_allowed BOOLEAN DEFAULT TRUE AFTER pet_restrictions
    COMMENT 'Can property be leased',
ADD COLUMN minimum_lease_term INTEGER AFTER lease_allowed
    COMMENT 'Minimum lease term in months';

-- Add indexes for amenity searches
CREATE INDEX idx_properties_game_room ON properties(game_room);
CREATE INDEX idx_properties_covered_patio ON properties(covered_patio);
CREATE INDEX idx_properties_study ON properties(study_office);

COMMIT;
```

---

## Database Migration - Phase 4 (Media & Advanced)

### Migration Script: `20251127_enhance_properties_phase4.sql`

```sql
-- ============================================================
-- Phase 4: Media, Energy, Financial
-- Priority: MEDIUM - Nice-to-have features
-- ============================================================

USE artitec;

-- Virtual & Media URLs
ALTER TABLE properties
ADD COLUMN virtual_tour_url VARCHAR(1024) AFTER media_urls,
ADD COLUMN video_walkthrough_url VARCHAR(1024) AFTER virtual_tour_url,
ADD COLUMN floor_plan_url VARCHAR(1024) AFTER video_walkthrough_url,
ADD COLUMN matterport_url VARCHAR(1024) AFTER floor_plan_url,
ADD COLUMN drone_video_url VARCHAR(1024) AFTER matterport_url,
ADD COLUMN blueprint_pdf_url VARCHAR(1024) AFTER drone_video_url;

-- Energy & Utilities
ALTER TABLE properties
ADD COLUMN energy_rating VARCHAR(50) AFTER year_built
    COMMENT 'energy_star, leed_certified, net_zero, none',
ADD COLUMN water_source VARCHAR(50) AFTER energy_rating
    COMMENT 'city, well, shared_well',
ADD COLUMN sewer_type VARCHAR(50) AFTER water_source
    COMMENT 'city, septic, aerobic_system',
ADD COLUMN gas_type VARCHAR(50) AFTER sewer_type
    COMMENT 'natural_gas, propane, electric_only',
ADD COLUMN internet_providers JSON AFTER gas_type
    COMMENT 'JSON: [comcast, att_fiber, spectrum]',
ADD COLUMN internet_speed VARCHAR(50) AFTER internet_providers
    COMMENT 'fiber_1gbps, cable_500mbps, dsl';

-- Special Features
ALTER TABLE properties
ADD COLUMN view_description VARCHAR(255) AFTER lot_premium
    COMMENT 'golf_course_view, lake_view, preserve_view',
ADD COLUMN upgrades_estimated_value DECIMAL(10,2) AFTER view_description
    COMMENT 'Estimated value of included upgrades',
ADD COLUMN design_center_completed BOOLEAN DEFAULT FALSE AFTER upgrades_estimated_value
    COMMENT 'Has buyer completed design center selections',
ADD COLUMN structural_options JSON AFTER design_center_completed
    COMMENT 'JSON: [extended_primary, bonus_room, outdoor_fp]';

-- Tax & Financial
ALTER TABLE properties
ADD COLUMN annual_property_tax DECIMAL(10,2) AFTER price_reduction_count,
ADD COLUMN tax_year INTEGER AFTER annual_property_tax,
ADD COLUMN homestead_exempt BOOLEAN DEFAULT FALSE AFTER tax_year,
ADD COLUMN assumable_loan BOOLEAN DEFAULT FALSE AFTER homestead_exempt
    COMMENT 'Can buyer assume existing mortgage',
ADD COLUMN builder_financing_available BOOLEAN DEFAULT FALSE AFTER assumable_loan,
ADD COLUMN builder_financing_rate DECIMAL(5,3) AFTER builder_financing_available
    COMMENT 'Builder preferred lender rate (6.5% = 6.500)';

-- Availability & Status
ALTER TABLE properties
ADD COLUMN showing_instructions TEXT AFTER occupancy_status,
ADD COLUMN occupancy_status VARCHAR(50) AFTER property_status
    COMMENT 'vacant, occupied, model_home, under_contract';

COMMIT;
```

---

## Enhanced Collection Prompts

### Property Collection Prompt (Complete)

```python
def generate_property_collection_prompt(builder_name, community_name, location):
    """
    Generate comprehensive Claude prompt for property data collection.
    """
    return f"""
Search the web for available properties/homes by {builder_name} in {community_name}, {location}.

Extract ALL available information for each property. Be thorough and capture every detail.

## Required Information:

### 1. BASIC INFORMATION
- Property title/name
- Full address (street, city, state, zip)
- Description/marketing text
- Model/floor plan name
- Property type: single_family, townhome, condo, duplex

### 2. SPECIFICATIONS
- Price (current asking price)
- Original listing price (if different)
- Bedrooms (count)
- Bathrooms (count, including half baths as 0.5)
- Square footage (total living area)
- Lot size in square feet
- Lot dimensions (e.g., "75x100 feet")
- Number of stories (1, 2, 3)
- Year built or estimated year
- Garage spaces (0, 1, 2, 3, 4)
- Garage type: attached, detached, tandem, carport

### 3. LOT DETAILS
- Corner lot? (yes/no)
- Cul-de-sac location? (yes/no)
- Lot backing: greenbelt, pond, lake, street, neighbor, preserve, golf_course
- Lot premium level: standard, premium, view_lot
- View description: golf_course_view, lake_view, preserve_view, etc.

### 4. SCHOOLS
- Elementary school name
- Middle school name
- High school name
- School district name
- School ratings (if available, scale 1-10)

### 5. BUILDER-SPECIFIC
- Model home? (yes/no)
- Quick move-in ready (within 60 days)? (yes/no)
- Under construction? (yes/no)
- Spec home or custom?
- Construction stage: not_started, foundation, framing, drywall, completed
- Estimated completion date (if under construction)
- Build start date (if known)
- Builder series: Signature, Executive, Classic, etc.
- Builder warranty duration (years)
- Design elevation: A, B, C, D

### 6. INTERIOR FEATURES
- Flooring types: hardwood, carpet, tile, vinyl, laminate (specify rooms)
- Countertop material: granite, quartz, marble, laminate
- Appliances included? (yes/no)
- Smart home features: thermostat, doorbell, security, lighting
- Number of fireplaces
- Study/office room? (yes/no)
- Game room? (yes/no)
- Media room? (yes/no)
- Flex room? (yes/no)

### 7. OUTDOOR AMENITIES
- Pool? (yes/no)
- Pool type: in_ground, above_ground, infinity, spa
- Outdoor kitchen? (yes/no)
- Covered patio? (yes/no)
- Patio square footage
- Sprinkler system? (yes/no)
- Fence type: wood, vinyl, iron, none
- Landscaping: full, partial, sod_only, none

### 8. PRICING & MARKET
- Days on market
- Number of price reductions
- Incentives offered: closing_cost_credit, design_center_credit, rate_buydown, etc.
- Estimated value of upgrades included
- Price per square foot (calculate if not stated)

### 9. HOA & RESTRICTIONS
- Monthly HOA fee (property-specific)
- What HOA includes: lawn_care, pool_access, trash, security
- Pet restrictions
- Lease/rental allowed? (yes/no)
- Minimum lease term (months)

### 10. ENERGY & UTILITIES
- Energy rating: energy_star, leed_certified, net_zero
- Water source: city, well, shared_well
- Sewer type: city, septic, aerobic_system
- Gas type: natural_gas, propane, electric_only
- Internet providers available
- Internet speed available

### 11. TAX & FINANCIAL
- Annual property tax amount
- Tax year
- Homestead exempt? (yes/no)
- Assumable loan available? (yes/no)
- Builder financing available? (yes/no)
- Builder financing rate (if available)

### 12. MEDIA & VIRTUAL
- Virtual tour URL
- Video walkthrough URL
- Floor plan image/PDF URL
- Matterport 3D tour URL
- Drone video URL
- Photo gallery URLs (main media_urls)

### 13. AVAILABILITY & STATUS
- Property status: available, pending, sold, under_contract
- Move-in ready? (yes/no)
- Occupancy status: vacant, occupied, model_home
- Showing instructions
- Construction stage (if applicable)

## Output Format:

Return data as structured JSON:

{{
  "properties": [
    {{
      "title": "The Oakmont - Quick Move-In",
      "address": {{
        "street": "23456 Oak Meadow Lane",
        "city": "Katy",
        "state": "TX",
        "postal_code": "77494"
      }},
      "specs": {{
        "price": 485000,
        "original_price": 495000,
        "bedrooms": 4,
        "bathrooms": 3.5,
        "sqft": 3200,
        "lot_sqft": 7500,
        "lot_dimensions": "75x100 feet",
        "stories": 2,
        "garage_spaces": 3,
        "garage_type": "attached"
      }},
      "lot_details": {{
        "corner_lot": false,
        "cul_de_sac": true,
        "backing": "greenbelt",
        "lot_premium": "premium",
        "view": "greenbelt_view"
      }},
      "schools": {{
        "elementary": "Robertson Elementary",
        "middle": "Beckendorff Junior High",
        "high": "Cinco Ranch High School",
        "district": "Katy ISD",
        "ratings": {{"elementary": 9, "middle": 9, "high": 9}}
      }},
      "builder_details": {{
        "model_home": false,
        "quick_move_in": true,
        "under_construction": false,
        "spec_home": true,
        "plan_name": "The Oakmont",
        "series": "Signature Series",
        "elevation": "B",
        "warranty_years": 10
      }},
      "interior": {{
        "flooring": ["hardwood_main", "carpet_bedrooms", "tile_wet_areas"],
        "countertops": "quartz",
        "appliances_included": true,
        "smart_home": ["smart_thermostat", "video_doorbell"],
        "fireplace_count": 1,
        "study_office": true,
        "game_room": true,
        "media_room": false
      }},
      "outdoor": {{
        "has_pool": false,
        "outdoor_kitchen": false,
        "covered_patio": true,
        "patio_sqft": 400,
        "sprinkler_system": true,
        "fence_type": "wood",
        "landscaping": "full"
      }},
      "market": {{
        "days_on_market": 45,
        "price_reductions": 1,
        "incentives": ["$10,000 closing cost credit", "$5,000 design center credit"],
        "upgrades_value": 25000
      }},
      "hoa": {{
        "monthly_fee": 125,
        "includes": ["lawn_care", "pool_access", "security"],
        "pet_restrictions": "2 pets maximum, breed restrictions apply",
        "lease_allowed": true,
        "min_lease_months": 12
      }},
      "energy": {{
        "rating": "energy_star",
        "water": "city",
        "sewer": "city",
        "gas": "natural_gas",
        "internet_providers": ["AT&T Fiber", "Comcast"],
        "internet_speed": "fiber_1gbps"
      }},
      "financial": {{
        "annual_tax": 12000,
        "tax_year": 2024,
        "homestead_exempt": false,
        "assumable_loan": false,
        "builder_financing": true,
        "builder_rate": 6.25
      }},
      "media": {{
        "virtual_tour": "https://perryhomes.com/tours/oakmont-23456",
        "video": "https://youtube.com/watch?v=...",
        "floor_plan": "https://perryhomes.com/plans/oakmont-b.pdf",
        "matterport": "https://matterport.com/...",
        "photos": [
          "https://perryhomes.com/gallery/oakmont-1.jpg",
          "https://perryhomes.com/gallery/oakmont-2.jpg"
        ]
      }},
      "status": {{
        "property_status": "available",
        "move_in_ready": true,
        "occupancy": "vacant",
        "showing_instructions": "Call listing agent 24 hours in advance"
      }},
      "confidence": 0.95,
      "source_url": "https://perryhomes.com/homes/cinco-ranch/oakmont-23456"
    }}
  ]
}}

## Important Notes:
1. Include confidence score (0-1) for the data
2. Include source URL for each property
3. If a field is not available, set it to null
4. For boolean fields, use true/false (not yes/no)
5. Be thorough - extract EVERY detail you can find
6. Calculate price_per_sqft if not explicitly stated
7. Look for builder incentives/promotions carefully
8. School ratings are critical - try multiple sources

Return only valid JSON, no additional text.
"""
```

---

## Pydantic Schema Updates

### Update `schema/property.py`

```python
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, conint, confloat, constr
from decimal import Decimal


# ================================================================
# Enhanced Property Schemas
# ================================================================

class PropertySpecs(BaseModel):
    """Detailed property specifications."""
    price: confloat(ge=0)
    original_price: Optional[confloat(ge=0)] = None
    bedrooms: conint(ge=0)
    bathrooms: confloat(ge=0)
    sqft: Optional[conint(ge=0)] = None
    lot_sqft: Optional[conint(ge=0)] = None
    lot_dimensions: Optional[str] = None
    stories: Optional[conint(ge=1, le=5)] = None
    garage_spaces: Optional[conint(ge=0, le=6)] = None
    garage_type: Optional[str] = None  # attached, detached, tandem


class LotDetails(BaseModel):
    """Lot-specific information."""
    corner_lot: bool = False
    cul_de_sac: bool = False
    backing: Optional[str] = None  # greenbelt, pond, street, neighbor
    lot_premium: Optional[str] = None  # standard, premium, view_lot
    view_description: Optional[str] = None


class SchoolInfo(BaseModel):
    """School district information."""
    elementary: Optional[str] = None
    middle: Optional[str] = None
    high: Optional[str] = None
    district: Optional[str] = None
    ratings: Optional[dict] = None  # {elementary: 9, middle: 8, high: 9}


class BuilderDetails(BaseModel):
    """Builder-specific property details."""
    model_home: bool = False
    quick_move_in: bool = False
    under_construction: bool = False
    spec_home: bool = False
    construction_stage: Optional[str] = None
    estimated_completion: Optional[date] = None
    build_start_date: Optional[date] = None
    plan_name: Optional[str] = None
    series: Optional[str] = None
    elevation: Optional[str] = None
    warranty_years: Optional[int] = None


class InteriorFeatures(BaseModel):
    """Interior amenities and features."""
    flooring_types: Optional[List[str]] = None
    countertops: Optional[str] = None
    appliances_included: bool = False
    smart_home_features: Optional[List[str]] = None
    fireplace_count: int = 0
    study_office: bool = False
    game_room: bool = False
    media_room: bool = False
    flex_room: bool = False


class OutdoorAmenities(BaseModel):
    """Outdoor features."""
    has_pool: bool = False
    pool_type: Optional[str] = None
    outdoor_kitchen: bool = False
    covered_patio: bool = False
    patio_sqft: Optional[int] = None
    sprinkler_system: bool = False
    fence_type: Optional[str] = None
    landscaping_status: Optional[str] = None


class MarketData(BaseModel):
    """Market and pricing information."""
    days_on_market: int = 0
    price_reductions: int = 0
    incentives: Optional[List[str]] = None
    upgrades_value: Optional[Decimal] = None
    price_per_sqft: Optional[Decimal] = None


class HOAInfo(BaseModel):
    """HOA and restrictions."""
    monthly_fee: Optional[Decimal] = None
    includes: Optional[List[str]] = None
    pet_restrictions: Optional[str] = None
    lease_allowed: bool = True
    min_lease_months: Optional[int] = None


class EnergyUtilities(BaseModel):
    """Energy and utility information."""
    energy_rating: Optional[str] = None
    water_source: Optional[str] = None
    sewer_type: Optional[str] = None
    gas_type: Optional[str] = None
    internet_providers: Optional[List[str]] = None
    internet_speed: Optional[str] = None


class MediaURLs(BaseModel):
    """Virtual tours and media."""
    virtual_tour: Optional[HttpUrl] = None
    video: Optional[HttpUrl] = None
    floor_plan: Optional[HttpUrl] = None
    matterport: Optional[HttpUrl] = None
    drone_video: Optional[HttpUrl] = None
    photos: Optional[List[HttpUrl]] = None


class FinancialInfo(BaseModel):
    """Tax and financial details."""
    annual_tax: Optional[Decimal] = None
    tax_year: Optional[int] = None
    homestead_exempt: bool = False
    assumable_loan: bool = False
    builder_financing: bool = False
    builder_rate: Optional[Decimal] = None


# ================================================================
# Main Enhanced Property Schemas
# ================================================================

class PropertyCreate(BaseModel):
    """Create new property with enhanced fields."""
    # Basic
    title: constr(strip_whitespace=True, min_length=3, max_length=255)
    description: Optional[constr(max_length=5000)] = None
    property_type: Optional[str] = None
    architectural_style: Optional[str] = None

    # Location
    address1: constr(strip_whitespace=True, min_length=1, max_length=255)
    address2: Optional[str] = None
    city: constr(strip_whitespace=True, min_length=1, max_length=120)
    state: constr(strip_whitespace=True, min_length=2, max_length=120)
    postal_code: constr(strip_whitespace=True, min_length=3, max_length=20)
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None

    # Relationships
    builder_id: Optional[int] = None
    community_id: Optional[int] = None

    # Nested structures
    specs: PropertySpecs
    lot_details: Optional[LotDetails] = None
    schools: Optional[SchoolInfo] = None
    builder_details: Optional[BuilderDetails] = None
    interior: Optional[InteriorFeatures] = None
    outdoor: Optional[OutdoorAmenities] = None
    market: Optional[MarketData] = None
    hoa: Optional[HOAInfo] = None
    energy: Optional[EnergyUtilities] = None
    media: Optional[MediaURLs] = None
    financial: Optional[FinancialInfo] = None

    # Status
    property_status: str = 'available'
    occupancy_status: Optional[str] = None
    showing_instructions: Optional[str] = None


class PropertyOut(PropertyCreate):
    """Property response with all fields."""
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    listed_at: Optional[datetime] = None
    data_source: str = 'manual'
    last_data_sync: Optional[datetime] = None
    data_confidence: float = 1.0

    class Config:
        orm_mode = True
```

---

## Summary

### What's Added

**45+ new fields** across 4 migration phases:
- ✅ Phase 1: 20 fields (property type, garage, lot, schools, pricing, builder flags)
- ✅ Phase 2: 8 fields (construction timeline, plan details)
- ✅ Phase 3: 17 fields (interior/exterior features, HOA)
- ✅ Phase 4: 17 fields (media, energy, financial, availability)

### Collection Priority

1. **Phase 1** → Run immediately (core buyer data)
2. **Phase 2** → Week 2 (builder-specific)
3. **Phase 3** → Week 3 (amenities)
4. **Phase 4** → Week 4 (nice-to-have)

### Claude Prompt
- ✅ Comprehensive 13-section prompt
- ✅ Structured JSON output
- ✅ Confidence scoring
- ✅ Source URL tracking

---

**Ready for Implementation!**

Next steps:
1. Run Phase 1 migration
2. Update property collection service
3. Test with sample builder
4. Deploy to production