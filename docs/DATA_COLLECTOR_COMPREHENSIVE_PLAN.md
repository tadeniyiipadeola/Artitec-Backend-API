# Artitec Data Collector - Comprehensive Implementation Plan

**Date**: November 24, 2025
**Purpose**: Automated collection and synchronization of Builder, Community, and Property data from web sources
**Status**: Planning Phase

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current Backend Schema Analysis](#current-backend-schema-analysis)
3. [System Architecture](#system-architecture)
4. [Collection Types](#collection-types)
5. [Database Schema Extensions](#database-schema-extensions)
6. [API Endpoints](#api-endpoints)
7. [Data Collection Flows](#data-collection-flows)
8. [Implementation Phases](#implementation-phases)
9. [Security & Compliance](#security--compliance)

---

## Executive Summary

### Goal
Build an automated system that:
- **Searches the web** for Builder, Community, and Property information using Claude AI
- **Validates** against existing database records
- **Detects changes** and creates change proposals
- **Allows admin review** and approval before applying updates
- **Creates new records** for discovered entities
- **Finds builder inventory** by discovering their properties

### Collection Scope

| Entity Type | What We Collect | Use Cases |
|-------------|-----------------|-----------|
| **Builders** | Company info, contact details, credentials, awards, service areas | Keep builder profiles up-to-date |
| **Communities** | HOA info, amenities, fees, location, active builders | Discover new communities, update existing |
| **Properties** | Builder inventory, listings, specs, pricing | Find builder's available homes |

### Why Backend?
- **Security**: API keys (Claude, web scraping) must stay server-side
- **Performance**: Resource-intensive operations shouldn't drain mobile devices
- **Centralization**: Single source of truth for all users
- **Scheduling**: Run automated collection jobs via cron
- **Cost Control**: Monitor and limit API usage centrally

---

## Current Backend Schema Analysis

### 1. BuilderProfile Schema (`model/profiles/builder.py`)

```python
class BuilderProfile(Base):
    __tablename__ = "builder_profiles"

    # IDs
    id                  # BIGINT (internal)
    builder_id          # String (public: "BLD-xxx")
    user_id             # String FK to users

    # Core
    name                # String(255)
    website             # String(1024)
    specialties         # JSON array
    rating              # Float (0-5)
    communities_served  # JSON array

    # Contact
    phone, email, address, city, state, postal_code

    # Meta
    about, bio, title, socials (JSON)
    verified            # Integer (0/1)

    # Relationships
    awards              # → builder_awards
    home_plans          # → builder_home_plans
    credentials         # → builder_credentials
    properties          # Many-to-many via builder_portfolio
    communities         # Many-to-many via builder_communities
```

### 2. Community Schema (`model/profiles/community.py`)

```python
class Community(Base):
    __tablename__ = "communities"

    # IDs
    id                  # BIGINT (internal)
    community_id        # String (public: "CMY-xxx")
    user_id             # String FK to users (owner)

    # Location
    name                # String(255)
    city, state, postal_code, address
    latitude, longitude
    total_acres         # Float

    # Financials
    community_dues      # String
    tax_rate            # String
    monthly_fee         # String

    # Stats
    homes               # Integer
    residents           # Integer
    founded_year        # Integer
    member_count        # Integer
    followers           # Integer

    # Development
    development_stage   # String (Phase 1-5, Completed)
    enterprise_number_hoa  # String

    # Media
    intro_video_url     # String
    community_website_url  # String

    # Meta
    about               # Text
    is_verified         # Boolean

    # Relationships
    amenities           # → community_amenities
    events              # → community_events
    awards              # → community_awards
    builders            # Many-to-many via builder_communities
```

### 3. Property Schema (`model/property/...`)

```python
class Property(Base):
    __tablename__ = "properties"

    # IDs
    id                  # BIGINT

    # Basic
    title               # String(140)
    description         # String(5000)

    # Location
    address1, address2, city, state, postal_code
    latitude, longitude

    # Specs
    price               # Float
    bedrooms            # Integer
    bathrooms           # Float
    sqft                # Integer
    lot_sqft            # Integer
    year_built          # Integer
    has_pool            # Boolean

    # Associations
    builder_id          # Integer FK
    community_id        # Integer FK
    owner_id            # Integer FK to users

    # Media
    media_urls          # JSON array

    # Timestamps
    created_at, updated_at, listed_at
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Admin Dashboard (iOS)                      │
│  ┌────────────┬──────────────┬───────────────────────────┐  │
│  │ Builder    │ Community    │ Property Inventory        │  │
│  │ Collection │ Collection   │ Discovery                 │  │
│  └────────────┴──────────────┴───────────────────────────┘  │
│  - Trigger collection jobs                                   │
│  - Review pending changes                                    │
│  - Approve/reject updates                                    │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTPS API
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Server                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Collection API Endpoints                    │   │
│  │  POST /admin/builders/{id}/collect                   │   │
│  │  POST /admin/communities/{id}/collect                │   │
│  │  POST /admin/builders/{id}/discover-properties       │   │
│  │  POST /admin/properties/discover                     │   │
│  │  GET  /admin/collection-jobs                         │   │
│  │  POST /admin/{entity}/apply-changes                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │       Multi-Entity Collection Service                │   │
│  │  ┌───────────┬────────────┬──────────────────────┐  │   │
│  │  │ Builder   │ Community  │ Property Inventory   │  │   │
│  │  │ Collector │ Collector  │ Collector            │  │   │
│  │  └───────────┴────────────┴──────────────────────┘  │   │
│  │  - Web search via Claude API                         │   │
│  │  - Data extraction & structuring                     │   │
│  │  - Entity linking (Builder ↔ Community ↔ Property)  │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │      Change Management Service                        │   │
│  │  - Store pending changes                             │   │
│  │  - Compare old vs new data                           │   │
│  │  - Generate change proposals                         │   │
│  │  - Handle entity relationships                       │   │
│  └──────────────────────┬──────────────────────────────┘   │
└─────────────────────────┼──────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                         │
│  Existing:                                                   │
│  - builder_profiles, builder_awards, builder_home_plans     │
│  - builder_credentials, builder_portfolio                   │
│  - communities, community_amenities, community_awards       │
│  - properties                                               │
│                                                             │
│  New:                                                        │
│  - collection_jobs                                          │
│  - collection_changes                                       │
│  - collection_sources                                       │
│  - entity_matches (linking discovered → existing)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Collection Types

### 1. Builder Collection
**Purpose**: Update/discover builder information

**Data Collected**:
- Company name, founded year, employee count
- Contact: phone, email, website
- Location: address, city, state, service areas
- Specialties: home types (custom, production, townhomes)
- Credentials: licenses, certifications, memberships
- Awards and recognitions
- Portfolio: Communities served, active projects

**Example Search**:
```
"Perry Homes Houston Texas home builder"
"Toll Brothers Dallas Fort Worth"
```

### 2. Community Collection
**Purpose**: Update/discover community (HOA) information

**Data Collected**:
- Community name, location
- HOA fees, monthly dues, tax rate
- Amenities: pools, parks, clubhouses, trails
- Stats: total homes, residents, acreage
- Development stage and phases
- Active builders in community
- Awards and ratings

**Example Search**:
```
"Cinco Ranch HOA Katy Texas"
"Aliana community Richmond TX amenities fees"
```

### 3. Property Inventory Discovery
**Purpose**: Find builder's available properties/listings

**Data Collected**:
- Property address and location
- Specs: beds, baths, sqft, lot size
- Price and availability
- Community association
- Property photos
- Model/plan name
- Move-in ready status

**Example Search**:
```
"Perry Homes available homes Houston"
"Toll Brothers inventory Dallas new construction"
"[Builder Name] new homes in [Community Name]"
```

---

## Database Schema Extensions

### New Tables

#### 1. `collection_jobs`
Tracks all collection operations

```sql
CREATE TABLE collection_jobs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,  -- "JOB-1699564234-ABC123"

    -- Target entity
    entity_type VARCHAR(50) NOT NULL,  -- "builder", "community", "property"
    entity_id BIGINT UNSIGNED,  -- FK to target entity (null for discovery)
    job_type VARCHAR(50) NOT NULL,  -- "update", "discovery", "inventory"

    -- For Builder → Property discovery
    parent_entity_type VARCHAR(50),  -- "builder" (when discovering builder's properties)
    parent_entity_id BIGINT UNSIGNED,  -- builder.id

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    priority INTEGER DEFAULT 0,  -- Higher = more urgent

    -- Search parameters
    search_query TEXT,  -- The query used for collection
    target_url VARCHAR(1024),  -- Specific URL to scrape (optional)
    search_filters JSON,  -- {"location": "Houston, TX", "price_max": 500000}

    -- Results
    items_found INTEGER DEFAULT 0,
    changes_detected INTEGER DEFAULT 0,
    new_entities_found INTEGER DEFAULT 0,  -- For discovery jobs
    error_message TEXT,

    -- Metadata
    initiated_by VARCHAR(50),  -- user_id who started it
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_status (status),
    INDEX idx_job_type (job_type),
    INDEX idx_parent (parent_entity_type, parent_entity_id)
);
```

#### 2. `collection_changes`
Stores detected changes before applying

```sql
CREATE TABLE collection_changes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,  -- FK to collection_jobs.job_id

    -- Target entity
    entity_type VARCHAR(50) NOT NULL,  -- "builder", "community", "property", "award", etc.
    entity_id BIGINT UNSIGNED,  -- ID of the entity (null for new entities)

    -- For new entities
    is_new_entity BOOLEAN DEFAULT FALSE,
    proposed_entity_data JSON,  -- Full entity data for new records

    -- For updates to existing entities
    field_name VARCHAR(100),  -- "name", "phone", "community_dues", etc.
    old_value TEXT,  -- Current value in DB (JSON if complex)
    new_value TEXT,  -- Proposed new value (JSON if complex)
    change_type VARCHAR(50) NOT NULL,  -- "added", "modified", "removed"

    -- Review
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, applied
    confidence FLOAT DEFAULT 1.0,  -- 0.0-1.0 confidence score
    source_url VARCHAR(1024),  -- Where data was found
    reviewed_by VARCHAR(50),  -- user_id who approved/rejected
    reviewed_at TIMESTAMP NULL,
    review_notes TEXT,

    -- Application
    applied_at TIMESTAMP NULL,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (job_id) REFERENCES collection_jobs(job_id) ON DELETE CASCADE,
    INDEX idx_job_id (job_id),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_status (status),
    INDEX idx_is_new (is_new_entity)
);
```

#### 3. `entity_matches`
Links discovered entities to existing records

```sql
CREATE TABLE entity_matches (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

    -- Discovered entity (from collection)
    discovered_entity_type VARCHAR(50) NOT NULL,  -- "builder", "community", "property"
    discovered_name VARCHAR(255) NOT NULL,
    discovered_location VARCHAR(255),  -- "Houston, TX"
    discovered_data JSON,  -- Full collected data

    -- Matched existing entity
    matched_entity_type VARCHAR(50),  -- Same as discovered_entity_type
    matched_entity_id BIGINT UNSIGNED,  -- ID in respective table
    match_confidence FLOAT,  -- 0.0-1.0 (1.0 = exact match)
    match_status VARCHAR(50) DEFAULT 'pending',  -- pending, confirmed, rejected, merged

    -- Matching metadata
    matched_by VARCHAR(50),  -- "auto" or user_id
    match_method VARCHAR(50),  -- "name_exact", "name_fuzzy", "website_match", "manual"
    match_notes TEXT,

    -- Job reference
    job_id VARCHAR(50),  -- FK to collection_jobs.job_id

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (job_id) REFERENCES collection_jobs(job_id) ON DELETE SET NULL,
    INDEX idx_discovered (discovered_entity_type, discovered_name),
    INDEX idx_matched (matched_entity_type, matched_entity_id),
    INDEX idx_status (match_status)
);
```

#### 4. `collection_sources`
Tracks data sources and reliability

```sql
CREATE TABLE collection_sources (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_id VARCHAR(50) UNIQUE NOT NULL,  -- "SRC-1699564234-XYZ"

    -- Source info
    source_name VARCHAR(255) NOT NULL,  -- "Perry Homes Official Website"
    source_url VARCHAR(1024) NOT NULL,  -- Base URL
    source_type VARCHAR(50) NOT NULL,  -- "official_website", "directory", "mls", "review_site"

    -- Applicable entities
    entity_types JSON,  -- ["builder", "property"]

    -- Reliability metrics
    reliability_score FLOAT DEFAULT 0.5,  -- 0.0-1.0 (updated based on accuracy)
    total_collections INTEGER DEFAULT 0,
    successful_collections INTEGER DEFAULT 0,
    failed_collections INTEGER DEFAULT 0,

    -- Rate limiting
    last_accessed TIMESTAMP NULL,
    access_count_today INTEGER DEFAULT 0,
    rate_limit_per_day INTEGER DEFAULT 100,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    blocked_until TIMESTAMP NULL,  -- If temporarily blocked

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_source_type (source_type),
    INDEX idx_reliability (reliability_score)
);
```

### Extensions to Existing Tables

#### Add to `builder_profiles`:
```sql
ALTER TABLE builder_profiles
ADD COLUMN founded_year INTEGER AFTER verified,
ADD COLUMN employee_count VARCHAR(50) AFTER founded_year,
ADD COLUMN service_areas JSON AFTER employee_count,
ADD COLUMN review_count INTEGER DEFAULT 0 AFTER rating,
ADD COLUMN last_data_sync TIMESTAMP NULL AFTER updated_at,
ADD COLUMN data_source VARCHAR(50) DEFAULT 'manual' AFTER last_data_sync,
ADD COLUMN data_confidence FLOAT DEFAULT 1.0 AFTER data_source;
```

#### Add to `communities`:
```sql
ALTER TABLE communities
ADD COLUMN school_district VARCHAR(255) AFTER state,
ADD COLUMN hoa_management_company VARCHAR(255) AFTER enterprise_number_hoa,
ADD COLUMN hoa_contact_phone VARCHAR(64) AFTER hoa_management_company,
ADD COLUMN hoa_contact_email VARCHAR(255) AFTER hoa_contact_phone,
ADD COLUMN last_data_sync TIMESTAMP NULL AFTER updated_at,
ADD COLUMN data_source VARCHAR(50) DEFAULT 'manual' AFTER last_data_sync,
ADD COLUMN data_confidence FLOAT DEFAULT 1.0 AFTER data_source;
```

#### Add to `properties`:
```sql
ALTER TABLE properties
ADD COLUMN property_status VARCHAR(50) DEFAULT 'available' AFTER has_pool,  -- available, pending, sold, model
ADD COLUMN move_in_ready BOOLEAN DEFAULT FALSE AFTER property_status,
ADD COLUMN model_name VARCHAR(255) AFTER move_in_ready,
ADD COLUMN lot_number VARCHAR(50) AFTER model_name,
ADD COLUMN last_data_sync TIMESTAMP NULL AFTER updated_at,
ADD COLUMN data_source VARCHAR(50) DEFAULT 'manual' AFTER last_data_sync,
ADD COLUMN data_confidence FLOAT DEFAULT 1.0 AFTER data_source;
```

---

## API Endpoints

### Builder Collection

#### 1. Update Builder Data
```http
POST /api/v1/admin/builders/{builder_id}/collect
Authorization: Bearer {admin_token}

Request:
{
  "search_query": "Perry Homes Houston Texas",  // Optional override
  "target_url": "https://perryhomes.com",  // Optional
  "priority": 5,  // 0-10
  "auto_apply": false
}

Response 202:
{
  "job_id": "JOB-BUILD-001",
  "builder_id": 123,
  "status": "pending",
  "estimated_completion": "2025-11-24T15:30:00Z"
}
```

#### 2. Discover Builder's Property Inventory
```http
POST /api/v1/admin/builders/{builder_id}/discover-properties
Authorization: Bearer {admin_token}

Request:
{
  "location_filter": "Houston, TX",  // Optional
  "community_filter": "Cinco Ranch",  // Optional
  "max_properties": 50
}

Response 202:
{
  "job_id": "JOB-PROP-DISC-001",
  "builder_id": 123,
  "builder_name": "Perry Homes",
  "job_type": "property_discovery",
  "status": "pending"
}
```

### Community Collection

#### 3. Update Community Data
```http
POST /api/v1/admin/communities/{community_id}/collect
Authorization: Bearer {admin_token}

Request:
{
  "search_query": "Cinco Ranch HOA Katy Texas",
  "include_builders": true,  // Also discover active builders
  "include_amenities": true
}

Response 202:
{
  "job_id": "JOB-COMM-001",
  "community_id": 456,
  "status": "pending"
}
```

#### 4. Discover New Communities
```http
POST /api/v1/admin/communities/discover
Authorization: Bearer {admin_token}

Request:
{
  "location": "Houston, TX",
  "radius_miles": 25,
  "min_homes": 100,  // Only discover communities with 100+ homes
  "max_communities": 20
}

Response 202:
{
  "job_id": "JOB-COMM-DISC-001",
  "search_area": "Houston, TX (25 miles)",
  "status": "pending"
}
```

### Property Collection

#### 5. Discover Properties (General)
```http
POST /api/v1/admin/properties/discover
Authorization: Bearer {admin_token}

Request:
{
  "location": "Houston, TX",
  "builder_id": 123,  // Optional: filter by builder
  "community_id": 456,  // Optional: filter by community
  "price_min": 300000,
  "price_max": 800000,
  "max_properties": 100
}

Response 202:
{
  "job_id": "JOB-PROP-DISC-002",
  "filters": {
    "location": "Houston, TX",
    "builder_id": 123,
    "price_range": "300000-800000"
  },
  "status": "pending"
}
```

### Job Management

#### 6. Get Job Status
```http
GET /api/v1/admin/collection-jobs/{job_id}
Authorization: Bearer {admin_token}

Response 200:
{
  "job_id": "JOB-BUILD-001",
  "entity_type": "builder",
  "entity_id": 123,
  "entity_name": "Perry Homes",
  "job_type": "update",
  "status": "completed",
  "started_at": "2025-11-24T15:00:00Z",
  "completed_at": "2025-11-24T15:02:30Z",
  "duration_seconds": 150,
  "results": {
    "items_found": 12,
    "changes_detected": 8,
    "new_entities_found": 0
  },
  "changes_summary": [
    {
      "change_id": 1001,
      "field": "phone",
      "old": "(713) 555-0100",
      "new": "(713) 555-0199",
      "confidence": 0.95
    },
    {
      "change_id": 1002,
      "entity_type": "award",
      "change_type": "added",
      "data": {
        "title": "Best Builder 2024",
        "issuer": "Houston Business Journal"
      },
      "confidence": 0.88
    }
  ]
}
```

#### 7. List Jobs
```http
GET /api/v1/admin/collection-jobs?entity_type=builder&status=completed&limit=20
Authorization: Bearer {admin_token}

Response 200:
{
  "jobs": [
    {
      "job_id": "JOB-BUILD-001",
      "entity_type": "builder",
      "entity_name": "Perry Homes",
      "job_type": "update",
      "status": "completed",
      "changes_detected": 8,
      "started_at": "2025-11-24T15:00:00Z"
    }
  ],
  "total": 156,
  "page": 1,
  "per_page": 20
}
```

### Change Management

#### 8. Get Pending Changes
```http
GET /api/v1/admin/{entity_type}/{entity_id}/pending-changes
# Examples:
# GET /api/v1/admin/builders/123/pending-changes
# GET /api/v1/admin/communities/456/pending-changes

Response 200:
{
  "entity_type": "builder",
  "entity_id": 123,
  "entity_name": "Perry Homes",
  "pending_changes": [
    {
      "change_id": 1001,
      "field": "phone",
      "current": "(713) 555-0100",
      "proposed": "(713) 555-0199",
      "confidence": 0.95,
      "source": "https://perryhomes.com/contact"
    }
  ],
  "pending_new_entities": [
    {
      "change_id": 2001,
      "entity_type": "property",
      "data": {
        "title": "The Oakmont - Model Home",
        "address": "123 Oak Street",
        "city": "Houston",
        "price": 485000,
        "beds": 4,
        "baths": 3.5
      },
      "confidence": 0.92,
      "source": "https://perryhomes.com/homes/oakmont"
    }
  ]
}
```

#### 9. Apply Changes
```http
POST /api/v1/admin/{entity_type}/{entity_id}/apply-changes
# Examples:
# POST /api/v1/admin/builders/123/apply-changes
# POST /api/v1/admin/communities/456/apply-changes

Request:
{
  "change_ids": [1001, 1002],  // Specific changes
  "apply_all": false,
  "min_confidence": 0.8,
  "create_new_entities": true,  // Apply pending new entity creations
  "review_notes": "Verified against official website"
}

Response 200:
{
  "applied_changes": 2,
  "created_entities": 1,
  "skipped": 0,
  "failed": 0,
  "details": {
    "updated_fields": ["phone", "awards"],
    "created_entities": [
      {
        "entity_type": "property",
        "entity_id": 789,
        "title": "The Oakmont - Model Home"
      }
    ]
  }
}
```

---

## Data Collection Flows

### Flow 1: Builder Data Update

```
Admin triggers → Job created → Claude searches web
                                    ↓
                        Finds: website, phone, awards, etc.
                                    ↓
                        Compare with existing DB record
                                    ↓
                        Detect 8 changes:
                        - Phone number updated
                        - 2 new awards
                        - Employee count added
                        - Website URL changed
                        - 3 new licenses
                                    ↓
                        Store in collection_changes (pending)
                                    ↓
                        Notify admin: "8 changes detected"
                                    ↓
Admin reviews → Approves 7, rejects 1 → System applies changes
                                    ↓
                        Builder profile updated
                        last_data_sync = NOW()
                        data_source = 'collected'
```

### Flow 2: Builder Property Inventory Discovery

```
Admin: "Find Perry Homes inventory in Houston"
                                    ↓
Job created: entity_type=property, parent_entity=builder(123)
                                    ↓
Claude searches: "Perry Homes available homes Houston Texas"
                                    ↓
Finds 15 properties:
  - The Oakmont ($485K, 4bd/3.5ba)
  - The Madison ($525K, 5bd/4ba)
  - ...
                                    ↓
For each property:
  1. Check if exists in DB (by address)
  2. If new → Create change record (is_new_entity=true)
  3. If exists → Compare specs, update if changed
                                    ↓
Store 15 pending changes:
  - 12 new properties
  - 3 existing (price updates)
                                    ↓
Admin reviews → Bulk approve new properties
                                    ↓
System creates 12 new Property records:
  - Links to builder_id = 123
  - Links to community_id (if found)
  - Sets property_status = 'available'
  - Sets data_source = 'collected'
```

### Flow 3: Community Data Collection

```
Admin: "Update Cinco Ranch community data"
                                    ↓
Job created: entity_type=community, entity_id=456
                                    ↓
Claude searches: "Cinco Ranch Katy Texas HOA fees amenities"
                                    ↓
Finds:
  - HOA fees: $125/month (was $115)
  - New amenity: Dog park (2024)
  - 3 active builders: Perry Homes, Toll Brothers, David Weekley
  - Total homes: 8500 (was 8200)
                                    ↓
Compare with DB:
  - monthly_fee changed
  - homes count increased
  - 1 new amenity
  - Detect 3 active builders
                                    ↓
Store changes:
  - monthly_fee: $115 → $125
  - homes: 8200 → 8500
  - New amenity: "Dog Park"
  - Link builders via builder_communities
                                    ↓
Admin reviews → Approves all
                                    ↓
System applies:
  - Updates community record
  - Creates community_amenity record
  - Links 3 builders (if not already linked)
```

### Flow 4: Community Discovery

```
Admin: "Discover communities in Houston, 100+ homes"
                                    ↓
Job created: job_type=discovery, entity_type=community
                                    ↓
Claude searches: "Houston Texas master planned communities HOA"
                                    ↓
Finds 25 communities:
  - Cinco Ranch (Katy) - 8500 homes
  - Bridgeland (Cypress) - 6200 homes
  - Aliana (Richmond) - 4500 homes
  - ...
                                    ↓
For each community:
  1. Try to match with existing DB records:
     - Name + City match? → Link to existing
     - No match? → Create as new
  2. Store in entity_matches for review
                                    ↓
Results:
  - 15 matched to existing (updates available)
  - 10 are new discoveries
                                    ↓
Admin reviews matches:
  - Confirms 14 matches
  - Rejects 1 (duplicate)
  - Approves 8 new communities
                                    ↓
System:
  - Updates 14 existing communities
  - Creates 8 new Community records
```

---

## Implementation Phases

### Phase 1: Database Schema (Week 1)
- [ ] Create Alembic migration for 4 new tables
- [ ] Add new columns to builder_profiles, communities, properties
- [ ] Create indexes for performance
- [ ] Test migration on dev database
- [ ] Write schema documentation

### Phase 2: Core Collection Service (Week 2-3)
- [ ] Create `services/data_collector/base.py` (base collector)
- [ ] Create `services/data_collector/builder_collector.py`
- [ ] Create `services/data_collector/community_collector.py`
- [ ] Create `services/data_collector/property_collector.py`
- [ ] Implement Claude API integration
- [ ] Build data extraction & parsing logic
- [ ] Create entity matching algorithm
- [ ] Add unit tests (80%+ coverage)

### Phase 3: Change Management Service (Week 4)
- [ ] Create `services/change_manager.py`
- [ ] Implement change detection algorithm
- [ ] Build diff comparison logic
- [ ] Add confidence scoring
- [ ] Create change application logic
- [ ] Add rollback capability
- [ ] Unit tests

### Phase 4: API Endpoints (Week 5)
- [ ] Create `routes/admin/collection.py`
- [ ] Implement all 9 endpoint groups
- [ ] Add authentication/authorization (admin only)
- [ ] Create Pydantic schemas for requests/responses
- [ ] Add input validation
- [ ] Create OpenAPI/Swagger docs
- [ ] Integration tests

### Phase 5: Background Jobs (Week 6)
- [ ] Set up Celery/RQ task queue
- [ ] Create async job processing
- [ ] Implement retry logic for failures
- [ ] Add job status updates
- [ ] Create job monitoring/logging
- [ ] Add alerting for failures

### Phase 6: Entity Matching & Deduplication (Week 7)
- [ ] Implement fuzzy name matching
- [ ] Create location-based matching
- [ ] Build confidence scoring for matches
- [ ] Add manual match override
- [ ] Create merge logic for duplicates
- [ ] Add tests for edge cases

### Phase 7: iOS Admin UI (Week 8-9)
- [ ] Create collection trigger views (Builder, Community, Property)
- [ ] Build job status monitoring view
- [ ] Create change review interface
- [ ] Add bulk approval features
- [ ] Implement real-time updates (WebSocket/polling)
- [ ] Add filtering and search

### Phase 8: Scheduling & Automation (Week 10)
- [ ] Create cron jobs for periodic collection
- [ ] Implement smart scheduling (collect stale data)
- [ ] Add rate limiting for external APIs
- [ ] Create cost monitoring
- [ ] Build admin monitoring dashboard
- [ ] Add email notifications

---

## Security & Compliance

### API Key Management
- Store Claude API key in environment variables (never in code)
- Use AWS Secrets Manager or similar for production
- Never expose keys in logs or responses
- Rotate keys quarterly
- Monitor API usage and costs

### Rate Limiting
- **Per User**: 20 collection jobs/hour
- **System-wide**: 200 jobs/day
- **Per Source**: Respect robots.txt and rate limits
- Track costs per job

### Data Privacy
- Only collect **publicly available** data
- Respect robots.txt and website terms of service
- Store source URLs for attribution and verification
- Allow builders/communities to opt-out of collection
- Never collect personal information (resident data)
- Comply with CCPA/GDPR for user data

### Access Control
- Only users with `role='admin'` or `role='super_admin'` can trigger collection
- Separate permission for auto-apply changes
- Audit log all collection activities
- Track who approved/rejected each change

### Error Handling
- Graceful degradation if Claude API fails
- Fallback to manual data entry
- Clear, actionable error messages for admins
- Retry failed jobs with exponential backoff (max 3 retries)
- Alert admins on repeated failures

### Data Validation
- Validate all collected data before storing
- Check data types and constraints
- Sanitize inputs to prevent injection
- Validate URLs and phone numbers
- Check for malicious content

---

## Cost Estimation

### Claude API Costs (Anthropic)
- **Model**: Claude Haiku (most cost-effective)
- **Prompt tokens per job**: ~800 (includes search results)
- **Response tokens per job**: ~1500 (structured data output)
- **Cost per job**: ~$0.03

**Monthly estimates**:
- 50 builder updates/day: $45/month
- 20 community updates/day: $18/month
- 100 property discoveries/week: $13/month
- **Total**: ~$76/month

### Infrastructure
- Background job worker (AWS EC2 t3.small): $15/month
- Database storage (additional): $5/month
- Monitoring & logging: $10/month
- **Total**: $30/month

### Grand Total
**~$106/month** for automated data collection across all entities

---

## Success Metrics

### Data Quality
1. **Accuracy**: % of approved changes vs total detected (target: >85%)
2. **Confidence**: Average confidence score of applied changes (target: >0.85)
3. **Error Rate**: % of failed jobs (target: <5%)

### Coverage
1. **Builder Coverage**: % of builders with collected data (target: >70% in 6 months)
2. **Community Coverage**: % of major communities documented (target: >60%)
3. **Property Inventory**: % of builders with up-to-date inventory (target: >50%)

### Efficiency
1. **Automation Rate**: % of high-confidence changes auto-applied (target: >40%)
2. **Time to Review**: Average time from detection to admin review (target: <2 days)
3. **Cost per Entity**: Cost per builder/community/property updated (target: <$0.10)

### Data Freshness
1. **Recency**: % of entities updated in last 90 days (target: >50%)
2. **Staleness**: Average days since last update (target: <120 days)

---

## Next Steps

### Immediate Actions
1. ✅ Review plan with team
2. ✅ Get approval for budget (~$106/month)
3. ⏳ Set up Claude API account (Anthropic)
4. ⏳ Create database migrations
5. ⏳ Start Phase 1 implementation

### Questions for Team

1. **Priority**: Which entity should we build first? (Builder → Property → Community?)
2. **Auto-Apply**: Should we auto-apply changes above 0.90 confidence?
3. **Frequency**: How often should automated collection run?
   - Builders: Monthly?
   - Communities: Quarterly?
   - Properties: Weekly?
4. **Notifications**: Email admins when >10 changes detected?
5. **Data Sources**: Any specific builder/community websites to prioritize?
6. **Verification**: Should we add a "human verified" flag that prevents auto-overwrite?

---

**Document Version**: v1.0
**Status**: Draft - Awaiting Team Review
**Next Review**: After team feedback
**Owner**: Backend Team
**Stakeholders**: iOS Team, Product, Data Team
