# Solution 3: Enhanced with Location Matching

## Overview

**Enhanced Strategy**: Use community name + location (city, state) for more accurate matching, preventing false matches when multiple communities have similar names.

---

## The Enhancement

### Problem Without Location
```
Community A: "Willow Bend" in Plano, TX
Community B: "Willow Bend" in Austin, TX
Builder collected: "Willow Bend" (which one??) ❌
```

### Solution With Location
```
Community A: "Willow Bend" in Plano, TX
Community B: "Willow Bend" in Austin, TX
Builder collected: "Willow Bend" + "Plano, TX" → Matches Community A ✅
```

---

## Implementation

### Step 1: Update Builder Collection Prompt

**File**: `src/collection/prompts.py`
**Function**: `generate_builder_collection_prompt`

```python
def generate_builder_collection_prompt(builder_name: str, location: Optional[str] = None) -> str:
    """Generate prompt for collecting builder data."""

    location_context = f" in {location}" if location else ""

    return f"""
You are collecting data about a home builder{location_context}.

BUILDER NAME: {builder_name}

Please search the web and collect the following information about this builder:

1. BASIC INFORMATION
   - Official company name (full legal name if different from search name)
   - Website URL
   - Headquarters address (full street address, city, state, ZIP)
   - Sales office address (if different from headquarters)
   - Phone number
   - Email address

2. COMMUNITY INFORMATION (IMPORTANT!)
   - Primary community where this builder operates (community name)
   - City and state where this builder primarily operates
   - If the builder operates in multiple communities, list the main one

   EXAMPLE:
   "community_name": "Willow Bend",
   "community_city": "Plano",
   "community_state": "TX"

3. COMPANY DETAILS
   - Year founded
   - Number of employees
   - Service areas (list of cities/regions served)
   - Specialties (types of homes: luxury, starter homes, custom, etc.)
   - Price range (minimum and maximum)

4. RATINGS & REVIEWS
   - Overall rating (out of 5 if available)
   - Number of reviews

5. AWARDS & RECOGNITION
   - List any awards received (title, awarded by, year)

6. CERTIFICATIONS & MEMBERSHIPS
   - Professional certifications
   - Industry memberships
   - Licenses

Return the data in JSON format with the following structure:

{{
    "name": "Official Builder Name",
    "community_name": "Primary Community Name",
    "community_city": "City",
    "community_state": "State Code (e.g., TX)",
    "description": "Brief description of builder",
    "website": "https://...",
    "phone": "123-456-7890",
    "email": "contact@...",
    "headquarters_address": "Full address with street, city, state, ZIP",
    "sales_office_address": "Full address (if different)",
    "founded_year": 2010,
    "employee_count": 50,
    "service_areas": ["City 1", "City 2"],
    "specialties": ["Luxury homes", "Custom builds"],
    "price_range_min": 500000,
    "price_range_max": 2000000,
    "rating": 4.5,
    "review_count": 120,
    "awards": [
        {{"title": "Award name", "awarded_by": "Organization", "year": 2023}}
    ],
    "certifications": ["Certification 1", "Certification 2"],
    "sources": ["url1", "url2"],
    "confidence": {{
        "overall": 0.85,
        "name": 0.95,
        "contact": 0.80,
        "community": 0.90
    }}
}}

IMPORTANT:
- Set confidence.overall to a value between 0.0 and 1.0 based on data quality
- Set confidence.community to reflect how confident you are about the community association
- Include sources URLs where you found the information
- Use "N/A" or null for any fields you cannot find
"""
```

### Step 2: Update Builder Collector Logic

**File**: `src/collection/builder_collector.py`
**Function**: `_process_new_builder`

Add enhanced community lookup with location matching:

```python
def _process_new_builder(self, collected_data: Dict[str, Any]):
    """Process collected data for new builder discovery."""
    if "raw_response" in collected_data:
        self.log("Claude returned non-JSON response", "WARNING", "parsing")
        logger.warning("Claude returned non-JSON response")
        return

    confidence = collected_data.get("confidence", {}).get("overall", 0.8)
    sources = collected_data.get("sources", [])
    source_url = sources[0] if sources else None
    builder_name = collected_data.get("name", "Unknown")

    # ===== ENHANCED COMMUNITY LOOKUP WITH LOCATION =====
    community_id = None
    community_name = collected_data.get("community_name")
    community_city = collected_data.get("community_city")
    community_state = collected_data.get("community_state")

    if community_name:
        self.log(
            f"Looking up community: {community_name} in {community_city}, {community_state}",
            "INFO",
            "matching"
        )

        # Build query with location filters
        from model.profiles.community import Community
        from model.collection import CollectionChange

        query = self.db.query(Community).filter(Community.name.ilike(f"%{community_name}%"))

        # Add location filters if available
        if community_city:
            query = query.filter(Community.city.ilike(f"%{community_city}%"))
        if community_state:
            query = query.filter(Community.state == community_state.upper())

        community = query.first()

        if community:
            # Found approved community with location match
            community_id = community.id
            self.log(
                f"Found approved community: {community.name} (ID: {community.id}) in {community.city}, {community.state}",
                "INFO",
                "matching",
                {
                    "community_id": community.id,
                    "community_name": community.name,
                    "location": f"{community.city}, {community.state}"
                }
            )
        else:
            # Check for pending community change with location
            self.log("No approved community found, checking pending changes", "INFO", "matching")

            # Query pending community changes with location matching
            from sqlalchemy import and_, or_

            change_query = self.db.query(CollectionChange).filter(
                CollectionChange.entity_type == "community",
                CollectionChange.status.in_(["pending", "approved"]),
                CollectionChange.proposed_entity_data["name"].astext.ilike(f"%{community_name}%")
            )

            # Add location filters to pending changes
            if community_city:
                change_query = change_query.filter(
                    CollectionChange.proposed_entity_data["city"].astext.ilike(f"%{community_city}%")
                )
            if community_state:
                change_query = change_query.filter(
                    CollectionChange.proposed_entity_data["state"].astext == community_state.upper()
                )

            community_change = change_query.first()

            if community_change and community_change.entity_id:
                # Found pending community with location match
                community_id = community_change.entity_id
                change_data = community_change.proposed_entity_data or {}
                self.log(
                    f"Found pending community change: {change_data.get('name')} (ID: {community_change.entity_id}) in {change_data.get('city')}, {change_data.get('state')}",
                    "INFO",
                    "matching",
                    {
                        "change_id": community_change.id,
                        "entity_id": community_change.entity_id,
                        "community_name": change_data.get("name"),
                        "location": f"{change_data.get('city')}, {change_data.get('state')}"
                    }
                )
            else:
                self.log(
                    f"No community found for {community_name} in {community_city}, {community_state}",
                    "WARNING",
                    "matching"
                )

    # ===== FALLBACK TO JOB METADATA =====
    # If community lookup failed, try using job.parent_entity_id as before
    if not community_id and self.job.parent_entity_type == "community" and self.job.parent_entity_id:
        community_id = self.job.parent_entity_id
        self.log(
            f"Using community ID from job metadata: {community_id}",
            "INFO",
            "matching"
        )

    # Check for duplicate builder BEFORE processing
    self.log(f"Checking for duplicate builder: {builder_name}", "INFO", "matching")

    from .duplicate_detection import find_duplicate_builder

    duplicate_id, match_confidence, match_method = find_duplicate_builder(
        db=self.db,
        name=builder_name,
        city=collected_data.get("city") or community_city,
        state=collected_data.get("state") or community_state,
        website=collected_data.get("website"),
        phone=collected_data.get("phone"),
        email=collected_data.get("email")
    )

    if duplicate_id:
        self.log(
            f"Found existing builder match: ID {duplicate_id} (confidence: {match_confidence:.2f}, method: {match_method})",
            "INFO",
            "matching",
            {"duplicate_id": duplicate_id, "confidence": match_confidence, "method": match_method}
        )

        # Record entity match for tracking
        self.record_entity_match(
            discovered_entity_type="builder",
            discovered_name=builder_name,
            discovered_data=collected_data,
            discovered_location=f"{community_city or ''}, {community_state or ''}".strip(', '),
            matched_entity_id=duplicate_id,
            match_confidence=match_confidence,
            match_method=match_method
        )

        # Skip creating new entity change - it's a duplicate
        self.log(f"Skipping duplicate builder: {builder_name}", "INFO", "matching")
        return

    # ... rest of existing code ...

    entity_data = {
        "name": builder_name,
        "description": collected_data.get("description"),
        "website": collected_data.get("website"),
        "phone": collected_data.get("phone"),
        "email": collected_data.get("email"),
        "headquarters_address": collected_data.get("headquarters_address"),
        "sales_office_address": collected_data.get("sales_office_address"),
        "city": collected_data.get("city") or community_city,
        "state": collected_data.get("state") or community_state,
        "zip_code": collected_data.get("zip_code"),
        "founded_year": collected_data.get("founded_year"),
        "employee_count": collected_data.get("employee_count"),
        "service_areas": collected_data.get("service_areas", []),
        "specialties": collected_data.get("specialties", []),
        "price_range_min": collected_data.get("price_range_min"),
        "price_range_max": collected_data.get("price_range_max"),
        "rating": collected_data.get("rating"),
        "review_count": collected_data.get("review_count"),
        "awards": collected_data.get("awards", []),
        "certifications": collected_data.get("certifications", []),
        "data_source": "collected",
        "data_confidence": confidence
    }

    # Add community_id if found
    if community_id:
        entity_data["community_id"] = community_id
        self.log(f"Linking builder to community ID: {community_id}", "INFO", "matching")

    # ... rest of existing code to record change ...
```

---

## Benefits of Location Enhancement

### 1. Prevents False Matches
```
WITHOUT LOCATION:
"Willow Bend" matches first community named "Willow Bend" (could be wrong city)

WITH LOCATION:
"Willow Bend" + "Plano, TX" matches only the correct community
```

### 2. Increases Confidence
```python
confidence: {
    "overall": 0.85,
    "community": 0.90  # Higher confidence with location match
}
```

### 3. Better Logging
```
Before: "Found community: Willow Bend (ID: 123)"
After:  "Found community: Willow Bend (ID: 123) in Plano, TX"
```

### 4. Handles Edge Cases
- Multiple communities with same name in different states
- Communities with similar names in same state
- Typos in community names (ILIKE fuzzy matching)

---

## Query Examples

### Approved Community Lookup
```python
# Before (name only):
Community.name == "Willow Bend"

# After (name + location):
Community.name.ilike("%Willow Bend%") AND
Community.city.ilike("%Plano%") AND
Community.state == "TX"
```

### Pending Community Change Lookup
```python
# Before (name only):
CollectionChange.proposed_entity_data["name"].astext == "Willow Bend"

# After (name + location):
CollectionChange.proposed_entity_data["name"].astext.ilike("%Willow Bend%") AND
CollectionChange.proposed_entity_data["city"].astext.ilike("%Plano%") AND
CollectionChange.proposed_entity_data["state"].astext == "TX"
```

---

## Error Handling

### Scenario 1: Location Not Collected
```python
if community_name:
    query = db.query(Community).filter(Community.name.ilike(f"%{community_name}%"))

    # Location filters only added if available
    if community_city:
        query = query.filter(Community.city.ilike(f"%{community_city}%"))
    if community_state:
        query = query.filter(Community.state == community_state.upper())

    # Falls back to name-only match if location missing
```

### Scenario 2: Multiple Matches
```python
# Use .first() to get best match
# Log warning if multiple matches found
communities = query.all()
if len(communities) > 1:
    logger.warning(f"Multiple communities found for {community_name} in {community_city}, {community_state}")
community = communities[0] if communities else None
```

### Scenario 3: State Code Normalization
```python
# Always uppercase state codes
if community_state:
    community_state = community_state.upper()
```

---

## Testing Plan

### Test Case 1: Exact Match with Location
```
Input:
- community_name: "Willow Bend"
- community_city: "Plano"
- community_state: "TX"

Expected: Matches community in Plano, TX (not Austin, TX)
```

### Test Case 2: Partial Name Match
```
Input:
- community_name: "Willow"
- community_city: "Plano"
- community_state: "TX"

Expected: Matches "Willow Bend" using ILIKE
```

### Test Case 3: Missing City
```
Input:
- community_name: "Willow Bend"
- community_city: None
- community_state: "TX"

Expected: Matches any "Willow Bend" in TX
```

### Test Case 4: Pending Community
```
Input:
- community_name: "New Community"
- community_city: "Dallas"
- community_state: "TX"

Scenario: Community exists as pending change only

Expected: Finds pending change and uses entity_id
```

---

## Summary

**Enhanced Solution 3 with Location**:
- ✅ Prevents false matches (different cities, same name)
- ✅ Higher confidence in community association
- ✅ Better audit trail with location logging
- ✅ Handles edge cases gracefully
- ✅ Falls back to name-only if location missing
- ✅ Works with both approved and pending communities

**Implementation Complexity**: Medium (still worth it for accuracy!)

This is now the **most robust solution** for preventing orphaned builders.
