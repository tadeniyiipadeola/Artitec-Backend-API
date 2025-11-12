# Community Amenity Integration Guide

## Overview

The iOS app uses **boolean toggles** for amenities in the registration form, while the backend stores amenities as **separate records** in the `community_amenities` table. This guide explains how to convert between the two formats.

---

## iOS Form → Backend API

### Form Fields (Boolean Toggles)

The iOS `FormSelectionView` has 14 boolean `@State` variables:

```swift
@State private var hasPool = false
@State private var hasFitnessCenter = false
@State private var hasClubhouse = false
@State private var hasTrails = false
@State private var hasPlayground = false
@State private var hasDogPark = false
@State private var hasWaterPark = false
@State private var hasTennisCourts = false
@State private var hasBasketballCourts = false
@State private var hasSoccerField = false
@State private var hasGolfCourse = false
@State private var hasLakeAccess = false
@State private var hasSecurity = false
@State private var isMasterPlanned = false
```

### Convert to API Format

Before sending to the API, convert boolean toggles to a `amenity_names` array:

```swift
// Helper function to convert amenity booleans to names array
func getSelectedAmenities() -> [String] {
    var amenities: [String] = []

    if isMasterPlanned { amenities.append("Master-planned community") }
    if hasPool { amenities.append("Pool") }
    if hasWaterPark { amenities.append("Water park") }
    if hasFitnessCenter { amenities.append("Fitness center") }
    if hasClubhouse { amenities.append("Clubhouse") }
    if hasTrails { amenities.append("Walking/biking trails") }
    if hasPlayground { amenities.append("Playground") }
    if hasDogPark { amenities.append("Dog park") }
    if hasTennisCourts { amenities.append("Tennis courts") }
    if hasBasketballCourts { amenities.append("Basketball courts") }
    if hasSoccerField { amenities.append("Soccer field") }
    if hasGolfCourse { amenities.append("Golf course") }
    if hasLakeAccess { amenities.append("Lake access") }
    if hasSecurity { amenities.append("24/7 Security") }

    return amenities
}
```

### API Request Example

**POST /v1/communities**

```json
{
  "name": "Oak Meadows HOA",
  "city": "Austin",
  "state": "TX",
  "postal_code": "78701",
  "community_dues": "$500/year",
  "monthly_fee": "125",
  "tax_rate": "2.5%",
  "homes": 524,
  "residents": 1200,
  "member_count": 480,
  "founded_year": 2005,
  "about": "A beautiful master-planned community with resort-style amenities...",
  "intro_video_url": "https://youtube.com/watch?v=example",
  "community_website_url": "https://oakmeadows.com",
  "amenity_names": [
    "Master-planned community",
    "Pool",
    "Water park",
    "Fitness center",
    "Tennis courts",
    "Dog park"
  ]
}
```

---

## Backend API → iOS Form

### Loading Existing Community

When fetching a community profile, the API returns amenities in the `amenities` array:

**GET /v1/communities/{id}?include=amenities**

```json
{
  "id": 123,
  "name": "Oak Meadows HOA",
  "city": "Austin",
  "state": "TX",
  "amenities": [
    {
      "id": 1,
      "community_id": 123,
      "name": "Pool",
      "gallery": null
    },
    {
      "id": 2,
      "community_id": 123,
      "name": "Water park",
      "gallery": null
    },
    {
      "id": 3,
      "community_id": 123,
      "name": "Master-planned community",
      "gallery": null
    }
  ]
}
```

### Convert to Form State

```swift
// Helper function to set amenity toggles from API response
func setAmenitiesFromAPI(_ amenities: [CommunityAmenity]) {
    // Reset all toggles
    hasPool = false
    hasFitnessCenter = false
    hasClubhouse = false
    hasTrails = false
    hasPlayground = false
    hasDogPark = false
    hasWaterPark = false
    hasTennisCourts = false
    hasBasketballCourts = false
    hasSoccerField = false
    hasGolfCourse = false
    hasLakeAccess = false
    hasSecurity = false
    isMasterPlanned = false

    // Set toggles based on amenity names
    for amenity in amenities {
        switch amenity.name.lowercased() {
        case "pool":
            hasPool = true
        case "water park":
            hasWaterPark = true
        case "fitness center":
            hasFitnessCenter = true
        case "clubhouse":
            hasClubhouse = true
        case "walking/biking trails", "trails":
            hasTrails = true
        case "playground":
            hasPlayground = true
        case "dog park":
            hasDogPark = true
        case "tennis courts":
            hasTennisCourts = true
        case "basketball courts":
            hasBasketballCourts = true
        case "soccer field":
            hasSoccerField = true
        case "golf course":
            hasGolfCourse = true
        case "lake access":
            hasLakeAccess = true
        case "24/7 security", "security":
            hasSecurity = true
        case "master-planned community", "master planned":
            isMasterPlanned = true
        default:
            break
        }
    }
}
```

---

## Backend Implementation

### Database Schema

**`community_amenities` table:**
- `id` - Primary key
- `community_id` - Foreign key to communities table
- `name` - Amenity name (VARCHAR 255)
- `gallery` - JSON array of image URLs (optional, for future use)

### API Endpoints

#### Create Community with Amenities
**POST /v1/communities**
- Accepts `amenity_names` array in request body
- Automatically creates amenity records for each name
- Returns created community with all amenities in response

#### Update Community Amenities
**PATCH /v1/communities/{id}**
- Include `amenity_names` array to **replace all** existing amenities
- Deletes old amenities and creates new ones
- Omit `amenity_names` to leave amenities unchanged

#### Direct Amenity Management
- **GET** `/v1/communities/{id}/amenities` - List all amenities
- **POST** `/v1/communities/{id}/amenities` - Add single amenity
- **PATCH** `/v1/communities/{id}/amenities/{amenity_id}` - Update amenity
- **DELETE** `/v1/communities/{id}/amenities/{amenity_id}` - Delete amenity

---

## Best Practices

### 1. Consistent Naming
Use exact same names in iOS and backend to avoid mapping issues:

✅ **Good:** "Pool", "Fitness center", "Dog park"
❌ **Bad:** "Pool Facility", "Gym", "Pet Area"

### 2. Case-Insensitive Matching
When loading amenities from API, use `.lowercased()` comparison to handle variations.

### 3. Extensibility
The backend design allows for:
- Adding new amenity types without schema changes
- Storing photo galleries for each amenity
- Custom amenity names beyond the 14 standard toggles

### 4. Migration Path
For users who already have communities without amenities:
- The `amenity_names` field is optional
- Empty array is valid (no amenities)
- Can be added/updated anytime via PATCH

---

## Example: Complete iOS Integration

```swift
// FormSelectionView.swift

func submitCommunityProfile() async {
    // 1. Convert boolean toggles to amenity names
    let amenityNames = getSelectedAmenities()

    // 2. Build request payload
    let payload: [String: Any] = [
        "name": hoaName,
        "city": hoaCity,
        "state": hoaState,
        "postal_code": postalCode,
        "community_dues": communityDues,
        "monthly_fee": monthlyFee,
        "tax_rate": taxRate,
        "homes": Int(totalHomes) ?? 0,
        "residents": Int(totalResidents) ?? 0,
        "member_count": Int(memberCount) ?? 0,
        "founded_year": Int(foundedYear) ?? nil,
        "about": aboutCommunity,
        "intro_video_url": introVideoUrl,
        "community_website_url": communityWebsiteUrl,
        "amenity_names": amenityNames  // ✅ Include converted amenities
    ]

    // 3. POST to API
    guard let url = URL(string: "\(API_BASE_URL)/v1/communities") else { return }
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONSerialization.data(withJSONObject: payload)

    // 4. Send request
    let (data, response) = try await URLSession.shared.data(for: request)

    // 5. Handle response
    if let community = try? JSONDecoder().decode(Community.self, from: data) {
        print("✅ Community created with \(community.amenities.count) amenities")
    }
}
```

---

## Testing

### Test Case 1: Create with Amenities
```bash
curl -X POST http://localhost:8000/v1/communities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Community",
    "city": "Austin",
    "state": "TX",
    "postal_code": "78701",
    "amenity_names": ["Pool", "Fitness center", "Dog park"]
  }'
```

Expected: Community created with 3 amenity records.

### Test Case 2: Update Amenities
```bash
curl -X PATCH http://localhost:8000/v1/communities/123 \
  -H "Content-Type: application/json" \
  -d '{
    "amenity_names": ["Pool", "Water park"]
  }'
```

Expected: Old amenities deleted, 2 new amenities created.

### Test Case 3: Fetch with Amenities
```bash
curl http://localhost:8000/v1/communities/123?include=amenities
```

Expected: Community object with `amenities` array populated.

---

## Summary

| iOS Side | Backend Side |
|----------|-------------|
| 14 boolean `@State` variables | `community_amenities` table |
| `getSelectedAmenities()` → `[String]` | `amenity_names` field in schema |
| Sent in POST/PATCH request | Converted to DB records |
| `setAmenitiesFromAPI()` ← `[Amenity]` | Returned in `amenities` array |

This design provides:
✅ Simple UI (boolean toggles)
✅ Flexible backend (extensible table)
✅ Clean API contract (`amenity_names` array)
✅ Future-proof (can add photos, descriptions, etc.)
