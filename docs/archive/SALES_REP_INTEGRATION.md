# Sales Rep Profile Integration Guide

## Overview

Sales Representatives are associated with a Builder and optionally assigned to a specific Community. The iOS form collects all necessary information and submits to the backend API.

---

## Form Flow

### iOS Form Collection

**Personal Information:**
- First Name (required)
- Last Name (required)
- Job Title (optional)

**Builder Association:**
- Builder ID (required) - Numeric ID of the builder they work for

**Community Assignment:**
- Community ID (optional) - Numeric ID if assigned to specific community

**Contact Information:**
- Email (optional)
- Phone (optional)

**Work Details:**
- Region/Territory (optional)
- Office Address (optional)

---

## Database Schema

### `sales_reps` Table

```sql
CREATE TABLE sales_reps (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    builder_id BIGINT UNSIGNED NOT NULL,  -- FK to builder_profiles.id
    community_id BIGINT UNSIGNED NULL,    -- FK to communities.id (optional)
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(128),
    email VARCHAR(255),
    phone VARCHAR(64),
    avatar_url VARCHAR(1024),
    region VARCHAR(128),
    office_address VARCHAR(255),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (builder_id) REFERENCES builder_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (community_id) REFERENCES communities(id) ON DELETE CASCADE
);
```

### Relationships

- **Many-to-One** with `builder_profiles`: Each sales rep belongs to one builder
- **Many-to-One** with `communities`: Each sales rep can be assigned to one community (optional)

---

## API Integration

### Create Sales Rep

**Endpoint:** `POST /v1/profiles/sales-reps`

**Request:**
```json
{
  "full_name": "John Smith",
  "builder_id": 123,
  "title": "Senior Sales Representative",
  "email": "john.smith@builder.com",
  "phone": "(555) 123-4567",
  "region": "Greater Houston Area",
  "office_address": "123 Main St, Houston, TX 77001",
  "verified": false,
  "community_id": 456
}
```

**Response:** `201 Created`
```json
{
  "id": 789,
  "full_name": "John Smith",
  "builder_id": 123,
  "community_id": 456,
  "title": "Senior Sales Representative",
  "email": "john.smith@builder.com",
  "phone": "(555) 123-4567",
  "region": "Greater Houston Area",
  "office_address": "123 Main St, Houston, TX 77001",
  "avatar_url": null,
  "verified": false,
  "created_at": "2025-11-11T20:45:00Z",
  "updated_at": "2025-11-11T20:45:00Z"
}
```

### Field Requirements

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `full_name` | ✅ Yes | String | First + Last name concatenated |
| `builder_id` | ✅ Yes | Integer | FK to builder_profiles.id |
| `community_id` | No | Integer | FK to communities.id (optional) |
| `title` | No | String | Job title/role |
| `email` | No | String | Contact email |
| `phone` | No | String | Contact phone |
| `region` | No | String | Territory/service area |
| `office_address` | No | String | Office location |
| `avatar_url` | No | String | Profile photo URL |
| `verified` | No | Boolean | Verification status (default: false) |

---

## iOS Implementation

### 1. SalesRepProfileCreate Model

```swift
public struct SalesRepProfileCreate: Codable {
    public var fullName: String
    public var builderId: Int
    public var title: String?
    public var email: String?
    public var phone: String?
    public var avatarUrl: String?
    public var region: String?
    public var officeAddress: String?
    public var verified: Bool?
    public var communityId: Int?
}
```

### 2. Form Submission Logic

```swift
if roleSlug == "salesrep" {
    let fullName = [repFirstName, repLastName]
        .filter { !$0.isEmpty }
        .joined(separator: " ")

    guard let builderId = Int(repBuilderId) else {
        showToast("Invalid Builder ID")
        return
    }

    let payload = SalesRepProfileCreate(
        fullName: fullName,
        builderId: builderId,
        title: repTitle.isEmpty ? nil : repTitle,
        email: repEmail.isEmpty ? nil : repEmail,
        phone: repPhone.isEmpty ? nil : repPhone,
        region: repRegion.isEmpty ? nil : repRegion,
        officeAddress: repOfficeAddress.isEmpty ? nil : repOfficeAddress,
        verified: false,
        communityId: repCommunityId.isEmpty ? nil : Int(repCommunityId)
    )

    bodyData = try encoder.encode(payload)
}
```

### 3. Validation Rules

**Required Fields:**
- First Name (not empty)
- Last Name (not empty)
- Builder ID (not empty, must be valid integer)

**Optional Fields:**
- All other fields

### 4. Navigation

After successful submission, user is redirected to `SalesRepDashboard`

---

## Backend Implementation

### Routes (`routes/profiles/sales_rep.py`)

```python
@router.post("/", response_model=SalesRepOut, status_code=status.HTTP_201_CREATED)
def create_sales_rep(
    *,
    db: Session = Depends(get_db),
    payload: SalesRepCreate,
):
    data = payload.model_dump(exclude_none=True)
    obj = SalesRepModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return SalesRepOut.model_validate(obj)
```

### Schema (`schema/builder.py`)

```python
class SalesRepBase(BaseModel):
    full_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    region: Optional[str] = None
    office_address: Optional[str] = None
    verified: Optional[bool] = False
    builder_id: Optional[int] = None
    community_id: Optional[int] = None

class SalesRepCreate(SalesRepBase):
    builder_id: int  # Required on create

class SalesRepOut(SalesRepBase):
    id: int
    builder_id: int
    community_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

---

## Testing

### Test Case 1: Create Sales Rep with Builder Only

```bash
curl -X POST http://localhost:8000/v1/profiles/sales-reps \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_HERE" \
  -d '{
    "full_name": "Jane Doe",
    "builder_id": 123,
    "title": "Sales Associate",
    "email": "jane.doe@builder.com",
    "phone": "(555) 987-6543"
  }'
```

Expected: 201 Created

### Test Case 2: Create Sales Rep with Builder and Community

```bash
curl -X POST http://localhost:8000/v1/profiles/sales-reps \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_HERE" \
  -d '{
    "full_name": "John Smith",
    "builder_id": 123,
    "community_id": 456,
    "title": "Senior Sales Representative",
    "email": "john.smith@builder.com",
    "phone": "(555) 123-4567",
    "region": "Greater Houston Area",
    "office_address": "123 Main St, Houston, TX"
  }'
```

Expected: 201 Created

### Test Case 3: Invalid Builder ID

```bash
curl -X POST http://localhost:8000/v1/profiles/sales-reps \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_HERE" \
  -d '{
    "full_name": "Test Rep",
    "builder_id": 99999
  }'
```

Expected: 500 or 404 (Foreign key constraint violation)

---

## Future Enhancements

1. **Builder Dropdown**: Replace text field with searchable builder list
2. **Community Dropdown**: Replace text field with searchable community list filtered by selected builder
3. **Avatar Upload**: Add profile photo upload capability
4. **Email Verification**: Implement email verification flow
5. **Multi-Community Assignment**: Allow sales reps to be assigned to multiple communities
6. **Performance Metrics**: Track sales rep performance (leads, conversions, etc.)

---

## Summary

| iOS Side | Backend Side |
|----------|-------------|
| Form with 9 fields | `sales_reps` table |
| SalesRepProfileCreate payload | SalesRepCreate schema |
| POST to `/v1/profiles/sales-reps` | Creates DB record |
| Navigates to SalesRepDashboard | Returns SalesRepOut |

**Key Points:**
- Sales reps MUST be associated with a builder (builder_id required)
- Community assignment is optional
- Full name is created by concatenating first + last name
- All contact and work detail fields are optional
