# Enterprise Builder Community Selection

## Overview

The Provision Enterprise Builder form now supports fetching and selecting communities for builder assignment. This allows admins to associate builders with specific communities during the provisioning process.

## API Endpoints

### 1. Get Available Communities

**Endpoint:** `GET /v1/admin/communities/available`

**Description:** Fetches all available communities that can be assigned to builders

**Authorization:** Admin role required

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
[
  {
    "community_id": "CMY-ACA5D173",
    "name": "Cane Island",
    "city": "Katy",
    "state": "TX",
    "property_count": 0,
    "active_status": "active"
  },
  {
    "community_id": "CMY-146CC8B7",
    "name": "Cross Creek Ranch",
    "city": "Fulshear",
    "state": "TX",
    "property_count": 0,
    "active_status": "active"
  }
  // ... 26 more communities
]
```

**Response Fields:**
- `community_id` (string): Unique identifier for the community (CMY-xxx format)
- `name` (string): Community name
- `city` (string): City where community is located
- `state` (string): State abbreviation
- `property_count` (integer): Not used for selection, always 0
- `active_status` (string): Status (always "active")

### 2. Provision Enterprise Builder with Communities

**Endpoint:** `POST /v1/admin/builders/enterprise/provision`

**Description:** Creates an enterprise builder account and optionally assigns communities

**Authorization:** Admin role required

**Request Body:**
```json
{
  "company_name": "Perry Homes",
  "website_url": "https://www.perryhomes.com",
  "company_address": "2222 Quitman St, Houston, TX 77009",
  "primary_contact_email": "john.doe@perryhomes.com",
  "primary_contact_first_name": "John",
  "primary_contact_last_name": "Doe",
  "primary_contact_phone": "+12815551234",
  "plan_tier": "enterprise",
  "community_ids": [
    "CMY-ACA5D173",
    "CMY-146CC8B7",
    "CMY-9E2C7164"
  ],
  "invitation_expires_days": 7,
  "custom_message": "Welcome to Artitec! Your account has been set up."
}
```

**Request Body Fields:**

**Required:**
- `company_name` (string): Builder company name
- `primary_contact_email` (string): Email for primary contact
- `primary_contact_first_name` (string): First name
- `primary_contact_last_name` (string): Last name

**Optional:**
- `website_url` (string): Company website
- `company_address` (string): Physical address
- `primary_contact_phone` (string): Phone number (E.164 format)
- `plan_tier` (string): "pro" or "enterprise" (default: "enterprise")
- **`community_ids` (array of strings): List of community IDs to assign**
- `invitation_expires_days` (integer): Days until invitation expires (default: 7)
- `custom_message` (string): Custom message for invitation email

## Frontend Implementation Guide

### Step 1: Fetch Communities on Form Load

```javascript
// Fetch available communities when admin opens the form
async function fetchAvailableCommunities() {
  const response = await fetch('/v1/admin/communities/available', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    throw new Error('Failed to fetch communities');
  }

  const communities = await response.json();
  return communities;
}
```

### Step 2: Populate Multi-Select/Dropdown

```javascript
// Example using React
import { useState, useEffect } from 'react';

function EnterpriseBuilderForm() {
  const [communities, setCommunities] = useState([]);
  const [selectedCommunities, setSelectedCommunities] = useState([]);

  useEffect(() => {
    fetchAvailableCommunities()
      .then(setCommunities)
      .catch(console.error);
  }, []);

  return (
    <form>
      {/* Other form fields... */}

      <label>Communities</label>
      <select
        multiple
        value={selectedCommunities}
        onChange={(e) => {
          const selected = Array.from(e.target.selectedOptions, option => option.value);
          setSelectedCommunities(selected);
        }}
      >
        {communities.map(community => (
          <option key={community.community_id} value={community.community_id}>
            {community.name} - {community.city}, {community.state}
          </option>
        ))}
      </select>

      {/* Submit button */}
    </form>
  );
}
```

### Step 3: Submit Form with Selected Communities

```javascript
async function provisionEnterpriseBuilder(formData) {
  const response = await fetch('/v1/admin/builders/enterprise/provision', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      company_name: formData.companyName,
      website_url: formData.websiteUrl,
      company_address: formData.companyAddress,
      primary_contact_email: formData.primaryEmail,
      primary_contact_first_name: formData.firstName,
      primary_contact_last_name: formData.lastName,
      primary_contact_phone: formData.phone,
      plan_tier: 'enterprise',
      community_ids: formData.selectedCommunities, // Array of community IDs
      invitation_expires_days: 7
    })
  });

  if (!response.ok) {
    throw new Error('Failed to provision builder');
  }

  return await response.json();
}
```

## Currently Available Communities

As of the latest database load, there are **28 communities** available across **16 cities** in the Houston area:

### By City:
- **Conroe** (4): Artavia, Evergreen, Grand Central Park, Harper's Preserve
- **Cypress** (2): Bridgeland, Towne Lake
- **Friendswood** (1): West Ranch
- **Fulshear** (2): Cross Creek Ranch, Jordan Ranch
- **Humble** (2): Balmoral, Fall Creek
- **Iowa Colony** (1): Meridiana
- **Katy** (3): Cane Island, Cinco Ranch, Elyson
- **League City** (2): Legacy, Tuscan Lakes
- **Manvel** (1): Pomona
- **Missouri City** (1): Sienna Plantation
- **Richmond** (3): Aliana, Harvest Green, Lakes of Bella Terra
- **Spring** (1): Woodson's Reserve
- **Sugar Land** (2): Imperial, Riverstone
- **Tomball** (2): Amira, Wildwood at Northpointe
- **Willis** (1): The Woodlands Hills

## Benefits

1. **Accurate Builder-Community Association**: Ensures builders are linked to the correct communities from the start
2. **Better Data Organization**: Properties can be properly filtered by builder and community
3. **Improved User Experience**: Buyers can find homes filtered by both builder and community
4. **Analytics**: Better reporting on builder activity per community

## Database Schema

The builder-community association is stored in the `builder_communities` junction table:

```sql
CREATE TABLE builder_communities (
    builder_id BIGINT UNSIGNED NOT NULL,
    community_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (builder_id, community_id),
    FOREIGN KEY (builder_id) REFERENCES builder_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE
);
```

## Error Handling

### 403 Forbidden
If a non-admin tries to access the communities endpoint:
```json
{
  "detail": "Only administrators can view available communities"
}
```

### 500 Internal Server Error
If there's a database error:
```json
{
  "detail": "Failed to fetch available communities: <error details>"
}
```

## Testing

Run the test script to verify the endpoint:

```bash
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
source .venv/bin/activate
python test_communities_endpoint.py
```

**Note:** Update the `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the test script before running.

## Next Steps

1. **Frontend Implementation**: Add the community selection dropdown to the Enterprise Builder provisioning form
2. **UI/UX**: Consider using a searchable multi-select component for better user experience with 28+ communities
3. **Validation**: Add frontend validation to ensure at least one community is selected (if required)
4. **Testing**: Test the end-to-end flow of provisioning a builder with community assignments

## Related Documentation

- [Enterprise Builder Test Guide](./ENTERPRISE_TEST_GUIDE.md)
- [API Documentation](../routes/enterprise.py)
- [Community Model](../model/profiles/community.py)
- [Builder Model](../model/profiles/builder.py)
