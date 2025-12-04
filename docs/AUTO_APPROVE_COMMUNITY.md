# Automatic Community Approval on Builder Approval

## Overview

When approving a builder that references an unapproved parent community, the system can automatically approve the parent community **if the community's confidence score is 75% or higher**.

## How It Works

### Workflow

1. **User approves a builder** via the review changes API
2. **System checks** if the builder references a community (via `community_id` in proposed_entity_data)
3. **If community doesn't exist yet**, system looks for a pending community change with matching `entity_id`
4. **System checks community confidence**:
   - **If confidence >= 0.75**: Community is automatically approved and created
   - **If confidence < 0.75**: Builder approval is blocked with error message

### Auto-Approval Process

When a community is auto-approved:

1. **Community record is created** in the `communities` table
2. **Community amenities are auto-created** (if provided in collected data)
3. **Change record is updated** with status "approved" and review notes indicating it was auto-approved
4. **Builder-community relationship is established** in both:
   - `builder_communities` join table
   - Legacy `community_id` field in builder_profiles

## Confidence Threshold

**Threshold: 75% (0.75)**

The confidence score comes from the Claude API's assessment of data quality during collection. It can be:
- Flat format: `{"confidence": 0.85}`
- Nested format: `{"confidence": {"overall": 0.85}}`

Both formats are supported.

## Error Messages

### Community Confidence Too Low
```
HTTP 400 Bad Request
{
  "detail": "Cannot approve builder: parent community has insufficient confidence (68% < 75%). Please manually review and approve the community first."
}
```

### Community Not Found
```
HTTP 400 Bad Request
{
  "detail": "Cannot approve builder: parent community (ID 123) does not exist. Please approve the community first."
}
```

## Code Location

**File**: `routes/admin/collection.py`
**Lines**: 1242-1352
**Section**: Builder approval logic - auto-approve parent community

## Testing

Use the test script to verify the auto-approval logic:

```bash
python test_auto_approve_community.py
```

The test script will:
1. Find a builder that references an unapproved community
2. Check the community's confidence score
3. Approve the builder
4. Verify whether auto-approval succeeded or was blocked (depending on confidence)
5. Verify the builder-community relationship in the database

## Benefits

1. **Streamlined Workflow**: No need to manually approve communities before builders
2. **Data Quality Control**: Only high-confidence communities (>= 75%) are auto-approved
3. **Prevents Orphaned Builders**: Ensures builders are always linked to their communities
4. **Transparent**: Auto-approval is logged with clear notes in the review_notes field

## Review Notes

When a community is auto-approved, the `review_notes` field will contain:
```
Auto-approved (confidence: 85.00%) as dependency for builder approval
```

This makes it clear in the audit trail that the community was auto-approved and why.

## Manual Override

If a community has confidence < 75%, you can still:
1. Manually approve the community first
2. Then approve the builder

The system will detect the community already exists and skip auto-approval.
