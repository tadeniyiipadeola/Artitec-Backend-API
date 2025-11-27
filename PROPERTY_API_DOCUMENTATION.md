# Property API Documentation

This document describes the Property API endpoints available for the frontend to fetch and display property listing data.

## Base URL
```
http://127.0.0.1:8000/v1
```

---

## Endpoints

### 1. List Properties (with filters)

**Endpoint:** `GET /property/`

**Description:** Retrieve a list of properties with optional filtering and sorting.

**Query Parameters:**
- `skip` (int): Number of records to skip for pagination (default: 0)
- `limit` (int): Maximum number of records to return (default: 20, max: 100)
- `city` (string): Filter by city (partial match, case-insensitive)
- `state` (string): Filter by state (partial match, case-insensitive)
- `min_price` (float): Minimum price filter
- `max_price` (float): Maximum price filter
- `min_beds` (int): Minimum number of bedrooms
- `min_baths` (float): Minimum number of bathrooms
- `builder_id` (int): Filter by specific builder ID
- `community_id` (int): Filter by specific community ID
- `has_pool` (bool): Filter properties with/without pool
- `sort` (string): Sort order - options:
  - `listed_at_desc` (default) - Most recently listed first
  - `listed_at_asc` - Oldest listings first
  - `price_desc` - Highest price first
  - `price_asc` - Lowest price first
  - `beds_desc` - Most bedrooms first
  - `beds_asc` - Least bedrooms first

**Example Request:**
```bash
curl "http://127.0.0.1:8000/v1/property/?city=Richmond&min_beds=3&max_price=500000&sort=price_asc"
```

**Response:** Array of PropertyOut objects (see Data Model below)

---

### 2. Get Single Property

**Endpoint:** `GET /property/{property_id}`

**Description:** Retrieve detailed information about a specific property.

**Path Parameters:**
- `property_id` (int): The unique ID of the property

**Example Request:**
```bash
curl "http://127.0.0.1:8000/v1/property/123"
```

**Response:** Single PropertyOut object (see Data Model below)

---

### 3. Get Property with Builder/Community Relations

**Endpoint:** `GET /property/{property_id}/relations`

**Description:** Retrieve a property with its associated builder and community information.

**Path Parameters:**
- `property_id` (int): The unique ID of the property

**Example Request:**
```bash
curl "http://127.0.0.1:8000/v1/property/123/relations"
```

**Response:**
```json
{
  "property_id": 123,
  "primary_builder": {
    "id": 45,
    "name": "Sitterle Homes",
    "builder_id": "BLD-1234567890-ABC123"
  },
  "builders": [
    {
      "id": 45,
      "name": "Sitterle Homes",
      "builder_id": "BLD-1234567890-ABC123"
    }
  ],
  "community": {
    "id": 78,
    "name": "Lakes of Bella Terra",
    "community_id": "CMY-1234567890-XYZ789"
  }
}
```

---

### 4. Create Property (Authenticated)

**Endpoint:** `POST /property/`

**Description:** Create a new property listing (requires authentication).

**Headers:**
- `Authorization: Bearer {access_token}`

**Request Body:** PropertyCreate object (see Data Model below)

**Response:** Created PropertyOut object with ID and timestamps

---

### 5. Update Property (Authenticated)

**Endpoint:** `PATCH /property/{property_id}`

**Description:** Update an existing property (only owner can update).

**Headers:**
- `Authorization: Bearer {access_token}`

**Path Parameters:**
- `property_id` (int): The unique ID of the property

**Request Body:** PropertyUpdate object (any subset of fields)

**Response:** Updated PropertyOut object

---

### 6. Delete Property (Authenticated)

**Endpoint:** `DELETE /property/{property_id}`

**Description:** Delete a property listing (only owner can delete).

**Headers:**
- `Authorization: Bearer {access_token}`

**Path Parameters:**
- `property_id` (int): The unique ID of the property

**Response:** 204 No Content

---

### 7. Toggle Favorite Property (Authenticated)

**Endpoint:** `POST /property/{property_id}/favorite`

**Description:** Add or remove a property from user's favorites.

**Headers:**
- `Authorization: Bearer {access_token}`

**Path Parameters:**
- `property_id` (int): The unique ID of the property

**Response:**
```json
{
  "message": "Added to favorites"
}
```
or
```json
{
  "message": "Removed from favorites"
}
```

---

### 8. List My Favorite Properties (Authenticated)

**Endpoint:** `GET /property/me/favorites`

**Description:** Retrieve all properties favorited by the current user.

**Headers:**
- `Authorization: Bearer {access_token}`

**Response:** Array of PropertyOut objects

---

## Data Model

### PropertyOut Object

Complete property object returned by the API:

```json
{
  "id": 123,
  "owner_id": 456,
  "created_at": "2025-11-26T12:00:00",
  "updated_at": "2025-11-26T12:00:00",
  "listed_at": "2025-11-26T12:00:00",

  // Core Details
  "title": "Beautiful 4BR Home in Lakes of Bella Terra",
  "description": "Stunning single-family home with modern upgrades...",

  // Address / Location
  "address1": "1234 Lakeside Drive",
  "address2": null,
  "city": "Richmond",
  "state": "TX",
  "postal_code": "77406",
  "latitude": 29.5826,
  "longitude": -95.7548,

  // Core Specifications
  "price": 425000.00,
  "bedrooms": 4,
  "bathrooms": 2.5,
  "sqft": 2500,
  "lot_sqft": 8000,
  "year_built": 2024,

  // Property Classification
  "property_type": "single_family",
  "listing_status": "available",

  // Structural Details
  "stories": 2,
  "garage_spaces": 2,

  // Lot Characteristics
  "corner_lot": false,
  "cul_de_sac": true,
  "lot_backing": "greenbelt",
  "views": "golf course, pond",

  // School Information
  "school_district": "Fort Bend ISD",
  "elementary_school": "Travis Elementary",
  "middle_school": "Garcia Middle School",
  "high_school": "Foster High School",
  "school_ratings": {
    "elementary": 9,
    "middle": 8,
    "high": 9
  },

  // Builder-Specific Information
  "model_home": false,
  "quick_move_in": true,
  "construction_stage": "completed",
  "estimated_completion": null,
  "builder_plan_name": "The Oakmont",
  "builder_series": "Executive Series",
  "elevation_options": "A, B, C",

  // Interior Features
  "flooring_types": "hardwood, tile, carpet",
  "countertop_materials": "granite, quartz",
  "appliances": "stainless steel",
  "game_room": true,
  "study_office": true,
  "bonus_rooms": "media room, flex space",

  // Outdoor Amenities
  "pool_type": "private",
  "covered_patio": true,
  "outdoor_kitchen": true,
  "landscaping": "professional, sprinkler system",

  // Pricing & Market Information
  "price_per_sqft": 170.00,
  "days_on_market": 5,
  "builder_incentives": "$10,000 closing cost assistance",
  "upgrades_included": "Upgraded flooring, smart home package",
  "upgrades_value": 25000.00,

  // HOA & Restrictions
  "hoa_fee_monthly": 150.00,
  "pet_restrictions": "2 pets max, no aggressive breeds",
  "lease_allowed": true,

  // Energy & Utilities
  "energy_rating": "HERS 55",
  "internet_providers": "AT&T Fiber, Xfinity",

  // Tax & Financial
  "annual_property_tax": 8500.00,
  "assumable_loan": false,

  // Media & Virtual Tours
  "virtual_tour_url": "https://example.com/tour/123",
  "floor_plan_url": "https://example.com/floorplan/123.pdf",
  "matterport_link": "https://matterport.com/show/xyz",

  // Availability & Showing
  "move_in_date": "January 2026",
  "showing_instructions": "Call listing agent 24hrs in advance",

  // Collection Metadata
  "source_url": "https://sitterlehomes.com/property/123",
  "data_confidence": 0.95,

  // Associations
  "builder_id": 45,
  "community_id": 78,
  "has_pool": true,

  // Media
  "media_urls": [
    "https://example.com/photos/1.jpg",
    "https://example.com/photos/2.jpg",
    "https://example.com/photos/3.jpg"
  ]
}
```

---

## Usage Examples for Frontend

### Example 1: Display Property Listing Grid

Fetch properties for a city and display in a grid:

```javascript
async function fetchProperties(city, page = 1, perPage = 20) {
  const skip = (page - 1) * perPage;
  const response = await fetch(
    `http://127.0.0.1:8000/v1/property/?city=${encodeURIComponent(city)}&skip=${skip}&limit=${perPage}&sort=listed_at_desc`
  );
  return await response.json();
}

// Usage
const properties = await fetchProperties('Richmond', 1, 20);

// Display each property
properties.forEach(property => {
  console.log(`${property.title} - $${property.price}`);
  console.log(`${property.bedrooms} bed, ${property.bathrooms} bath, ${property.sqft} sqft`);
  console.log(`Builder: ${property.builder_id}, Community: ${property.community_id}`);
  console.log(`Move-in: ${property.move_in_date || 'TBD'}`);
});
```

### Example 2: Property Detail Page

Fetch full property details with builder and community info:

```javascript
async function fetchPropertyDetails(propertyId) {
  // Fetch property data
  const propertyResponse = await fetch(
    `http://127.0.0.1:8000/v1/property/${propertyId}`
  );
  const property = await propertyResponse.json();

  // Fetch relations (builder/community)
  const relationsResponse = await fetch(
    `http://127.0.0.1:8000/v1/property/${propertyId}/relations`
  );
  const relations = await relationsResponse.json();

  return {
    ...property,
    builder: relations.primary_builder,
    community: relations.community
  };
}

// Usage
const property = await fetchPropertyDetails(123);

console.log('Property:', property.title);
console.log('Description:', property.description);
console.log('Builder:', property.builder.name);
console.log('Community:', property.community.name);
console.log('Move-in Date:', property.move_in_date);
console.log('Plan Name:', property.builder_plan_name);
console.log('Series:', property.builder_series);
```

### Example 3: Advanced Filtering

Filter properties by multiple criteria:

```javascript
async function searchProperties(filters) {
  const params = new URLSearchParams();

  if (filters.city) params.append('city', filters.city);
  if (filters.state) params.append('state', filters.state);
  if (filters.minPrice) params.append('min_price', filters.minPrice);
  if (filters.maxPrice) params.append('max_price', filters.maxPrice);
  if (filters.minBeds) params.append('min_beds', filters.minBeds);
  if (filters.minBaths) params.append('min_baths', filters.minBaths);
  if (filters.builderId) params.append('builder_id', filters.builderId);
  if (filters.communityId) params.append('community_id', filters.communityId);
  if (filters.hasPool !== undefined) params.append('has_pool', filters.hasPool);
  if (filters.sort) params.append('sort', filters.sort);

  params.append('skip', filters.skip || 0);
  params.append('limit', filters.limit || 20);

  const response = await fetch(
    `http://127.0.0.1:8000/v1/property/?${params.toString()}`
  );
  return await response.json();
}

// Usage
const properties = await searchProperties({
  city: 'Richmond',
  state: 'TX',
  minPrice: 300000,
  maxPrice: 500000,
  minBeds: 3,
  minBaths: 2,
  hasPool: true,
  sort: 'price_asc'
});
```

### Example 4: Property Card Component (React)

```jsx
function PropertyCard({ property }) {
  return (
    <div className="property-card">
      <img src={property.media_urls?.[0]} alt={property.title} />

      <h3>{property.title}</h3>
      <p className="price">${property.price.toLocaleString()}</p>

      <div className="specs">
        <span>{property.bedrooms} bed</span>
        <span>{property.bathrooms} bath</span>
        <span>{property.sqft?.toLocaleString()} sqft</span>
      </div>

      <div className="location">
        <p>{property.city}, {property.state} {property.postal_code}</p>
      </div>

      {property.builder_plan_name && (
        <p className="plan-name">{property.builder_plan_name}</p>
      )}

      {property.move_in_date && (
        <p className="move-in">Move-in: {property.move_in_date}</p>
      )}

      {property.quick_move_in && (
        <span className="badge">Quick Move-In</span>
      )}

      {property.model_home && (
        <span className="badge">Model Home</span>
      )}
    </div>
  );
}
```

---

## Field Reference Guide

### Key Fields for Frontend Display

**Essential Property Information:**
- `title` - Property headline/name
- `description` - Full property description
- `price` - Listing price
- `bedrooms`, `bathrooms`, `sqft` - Core specs
- `address1`, `city`, `state`, `postal_code` - Location

**Builder & Community Context:**
- `builder_plan_name` - Name of the floor plan (e.g., "The Oakmont")
- `builder_series` - Series/collection name (e.g., "Executive Series")
- `builder_id` - Link to builder profile
- `community_id` - Link to community profile

**Availability:**
- `move_in_date` - When the home will be ready
- `listing_status` - Current status (available, pending, sold)
- `quick_move_in` - Boolean flag for quick availability
- `construction_stage` - Construction progress

**Media:**
- `media_urls` - Array of photo URLs
- `virtual_tour_url` - Virtual tour link
- `matterport_link` - 3D tour link
- `floor_plan_url` - Floor plan document

**Features to Highlight:**
- `pool_type` - Pool information
- `game_room`, `study_office` - Special rooms
- `covered_patio`, `outdoor_kitchen` - Outdoor features
- `energy_rating` - Energy efficiency
- `upgrades_included` - Pre-installed upgrades

---

## Notes

1. **All fields are optional except:**
   - `id`, `owner_id`, `created_at` (set by system)
   - `title`, `address1`, `city`, `state`, `postal_code`, `price`, `bedrooms`, `bathrooms` (required for creation)

2. **Builder and Community IDs are required:**
   - Properties must be associated with a builder and community
   - Use the `/property/{id}/relations` endpoint to get full builder/community details

3. **Pagination:**
   - Default limit is 20 properties per request
   - Maximum limit is 100 properties per request
   - Use `skip` and `limit` for pagination

4. **Filtering:**
   - All text filters (city, state) use case-insensitive partial matching
   - Numeric filters support range queries (min/max)
   - Multiple filters can be combined

5. **Authentication:**
   - Read operations (GET) do not require authentication
   - Create, Update, Delete operations require Bearer token
   - Favorite operations require authentication

---

## Error Responses

**404 Not Found:**
```json
{
  "detail": "Property not found"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not authorized to update this property"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

---

## Next Steps

1. **Test the API endpoints** using the examples above
2. **Build your frontend components** using the PropertyOut data model
3. **Implement filtering and search** for your property listing pages
4. **Add property detail views** showing all available fields
5. **Wait for property collection jobs to complete** to populate the database with real data

For questions or issues, contact the backend development team.
