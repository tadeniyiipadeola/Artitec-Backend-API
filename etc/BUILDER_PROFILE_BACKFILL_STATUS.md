# Builder Profile Backfill - Status & Next Steps

## Overview
This document outlines the current state of builder profile linking/backfill functionality and the steps needed to add a complete frontend for it.

## Current Implementation

### Backend Scripts ✅
- `/etc/create_jobs_for_unlinked_builders.py` - Creates collection jobs for unlinked builder cards
- `/etc/backfill_builder_profile_links.py` - Backfills builder profile links
- `/etc/validate_builder_profile_integration.py` - Validates the builder profile integration

### What Exists
- **Database Schema**: `community_builders.builder_profile_id` column with FK to `builder_profiles.id`
- **Auto-linking Logic**: Collection jobs store `community_builder_card_ids` in metadata for automatic linking
- **Manual Script**: `create_jobs_for_unlinked_builders.py` successfully creates jobs (tested, 10 jobs created)
- **Backend API Endpoints**: ✅ COMPLETE - Fully implemented and tested (lines 3033-3310 in `routes/admin/collection.py`)

### What's Missing
- **iOS Frontend**: No UI to view/manage builder profile linking

## Comparison with Community Builder Backfill

### Community Builder Backfill (Already Implemented)
**Purpose**: Create collection jobs for communities that have NO builder data at all

**Backend Endpoints**:
- `GET /v1/admin/collection/coverage/community-builders` - Get coverage statistics
- `POST /v1/admin/collection/backfill/community-builders` - Run backfill (create jobs)

**iOS Frontend**:
- `DataCoverageView.swift` - Shows coverage stats, backfill controls
- `DataCoverageViewModel.swift` - Handles API calls, state management
- DTOs: `CommunityBuilderCoverage`, `BackfillResult`, `BackfillJob`, etc.

### Builder Profile Linking (✅ BACKEND COMPLETE)
**Purpose**: Create collection jobs for builder CARDS that exist but have no `builder_profile_id` link

**Backend Endpoints** (Implemented in `routes/admin/collection.py:3033-3310`):
- `GET /v1/admin/collection/coverage/builder-profiles` - Get linking status
  ```json
  {
    "total_builder_cards": 159,
    "linked_cards": 134,
    "unlinked_cards": 25,
    "linking_percentage": 84.3,
    "unlinked_builders": [
      {
        "builder_name": "Drees Custom Homes",
        "card_count": 8,
        "communities": ["CMY-001", "CMY-002", ...]
      }
    ]
  }
  ```

- `POST /v1/admin/collection/backfill/builder-profiles` - Run backfill
  ```json
  Request: { "priority": 7, "dry_run": false }
  Response: {
    "message": "Created 10 collection jobs for unlinked builder cards",
    "builders_found": 10,
    "jobs_created": 10,
    "cards_affected": 25,
    "jobs": [...]
  }
  ```

**iOS Frontend Needed**:
- Option A: Add section to existing `DataCoverageView.swift`
- Option B: Create new `BuilderProfileLinkingView.swift` (cleaner separation)

## Recommended Implementation Steps

### Step 1: Backend API Endpoints
Create endpoints in `routes/admin/collection.py`:

```python
@router.get("/coverage/builder-profiles")
async def get_builder_profile_coverage(db: Session = Depends(get_db)):
    """Get builder profile linking coverage statistics"""
    # Query unlinked builder cards
    # Group by builder name
    # Return stats + list of unlinked builders

@router.post("/backfill/builder-profiles")
async def backfill_builder_profiles(
    priority: int = Query(7, ge=1, le=10),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Create collection jobs for unlinked builder cards"""
    # Logic from create_jobs_for_unlinked_builders.py
    # Create jobs with metadata for auto-linking
    # Return results
```

### Step 2: iOS DTOs
Add to `Data/DTO/CollectionDTO.swift` or create new file:

```swift
public struct BuilderProfileCoverage: Codable {
    let totalBuilderCards: Int
    let linkedCards: Int
    let unlinkedCards: Int
    let linkingPercentage: Double
    let unlinkedBuilders: [UnlinkedBuilder]

    enum CodingKeys: String, CodingKey {
        case totalBuilderCards = "total_builder_cards"
        case linkedCards = "linked_cards"
        case unlinkedCards = "unlinked_cards"
        case linkingPercentage = "linking_percentage"
        case unlinkedBuilders = "unlinked_builders"
    }
}

public struct UnlinkedBuilder: Codable, Identifiable {
    public let id = UUID()
    let builderName: String
    let cardCount: Int
    let communities: [String]

    enum CodingKeys: String, CodingKey {
        case builderName = "builder_name"
        case cardCount = "card_count"
        case communities
    }
}
```

### Step 3: Repository Methods
Add to `CollectionRepository.swift`:

```swift
func getBuilderProfileCoverage() async throws -> BuilderProfileCoverage
func backfillBuilderProfiles(priority: Int, dryRun: Bool) async throws -> BackfillResult
```

### Step 4: iOS Frontend
**Option A** - Enhance existing `DataCoverageView`:
- Add tabs or sections for both "Community Builders" and "Builder Profiles"
- Reuse existing UI components

**Option B** - Create new dedicated view:
- `BuilderProfileLinkingView.swift`
- `BuilderProfileLinkingViewModel.swift`
- Simpler, cleaner separation of concerns

## Test Data

From our successful test run:

**Unlinked Builder Cards**: 25 cards across 10 unique builders
1. Drees Custom Homes: 8 cards
2. Darling Homes: 5 cards
3. Princeton Classic Homes: 4 cards
4. LGI Homes: 2 cards
5. Various others: 1 card each

**Jobs Created**: 10 collection jobs (1 per unique builder)
- Job IDs: JOB-1765350614-1GDAX5, JOB-1765350614-49FPPL, etc.
- Priority: 5
- Status: pending
- Auto-linking metadata stored in `search_filters.community_builder_card_ids`

## Next Steps

1. **Immediate**: Decide between Option A (enhance DataCoverageView) or Option B (new view)
2. **Backend**: Implement the two API endpoints
3. **iOS**: Add DTOs and repository methods
4. **iOS**: Build the frontend view
5. **Test**: End-to-end testing with the 25 unlinked cards

## Files Modified/Created

### Backend
- `routes/admin/collection.py` - Add 2 new endpoints
- Test the endpoints work correctly

### iOS
- `Data/DTO/CollectionDTO.swift` - Add `BuilderProfileCoverage` and `UnlinkedBuilder`
- `Data/Repositories/CollectionRepository.swift` - Add 2 new methods
- `Data/Networking/CollectionService.swift` - Add 2 new service methods
- `Features/Admin/BuilderProfileLinkingView.swift` (new) - Main view
- `Features/Admin/BuilderProfileLinkingViewModel.swift` (new) - ViewModel

OR (if enhancing existing view):
- `Features/Admin/DataCoverageView.swift` - Add builder profile section
- `Features/Admin/DataCoverageViewModel.swift` - Add builder profile methods

## References

- Script that works: `/etc/create_jobs_for_unlinked_builders.py`
- Validation script: `/etc/validate_builder_profile_integration.py`
- Existing community builder backfill: lines 2741-2817 in `routes/admin/collection.py`
- Existing iOS implementation: `Features/Admin/DataCoverageView.swift`
