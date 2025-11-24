"""
Claude AI Prompts for Data Collection

Contains all prompts used for different collection tasks.
"""
from typing import Optional


def generate_community_collection_prompt(community_name: str, location: str) -> str:
    """Generate prompt for collecting community data."""
    return f"""
Search the web for information about the residential community "{community_name}" in {location}.

Extract ALL available information about this community. Be thorough and capture every detail you can find.

## Required Information:

1. BASIC INFORMATION
   - Name (official name)
   - Description (detailed overview)
   - Location (full address if available)
   - City, State, ZIP code
   - Website URL
   - Phone number
   - Email

2. HOA INFORMATION
   - HOA fee (monthly/yearly)
   - HOA management company
   - HOA contact phone
   - HOA contact email
   - What HOA covers

3. COMMUNITY DETAILS
   - Total number of homes
   - Year established
   - Developer name
   - School district
   - Zoned schools (elementary, middle, high school names)

4. AMENITIES
   - List all amenities (pool, clubhouse, trails, parks, etc.)
   - Amenity details and hours

5. BUILDERS
   - List of builders operating in this community
   - Builder names and contact info

6. REVIEWS & RATINGS
   - Overall community rating
   - Number of reviews
   - Common feedback themes

## Output Format:
Return data as structured JSON:
{{
  "name": "string",
  "description": "string",
  "location": "string",
  "city": "string",
  "state": "string",
  "zip_code": "string",
  "website": "string",
  "phone": "string",
  "email": "string",
  "hoa_fee": number,
  "hoa_fee_frequency": "monthly|yearly",
  "hoa_management_company": "string",
  "hoa_contact_phone": "string",
  "hoa_contact_email": "string",
  "total_homes": number,
  "year_established": number,
  "developer_name": "string",
  "school_district": "string",
  "elementary_school": "string",
  "middle_school": "string",
  "high_school": "string",
  "amenities": ["array", "of", "amenities"],
  "builders": [
    {{
      "name": "string",
      "website": "string",
      "phone": "string"
    }}
  ],
  "rating": number,
  "review_count": number,
  "confidence": {{
    "overall": 0.0-1.0,
    "field_confidence": {{
      "field_name": 0.0-1.0
    }}
  }},
  "sources": ["url1", "url2"]
}}

IMPORTANT:
- Only return data you can verify from web sources
- Include confidence scores for each field
- List all source URLs where data was found
- If a field is not found, omit it or set to null
"""


def generate_builder_collection_prompt(builder_name: str, location: Optional[str] = None) -> str:
    """Generate prompt for collecting builder data."""
    location_str = f" in {location}" if location else ""
    return f"""
Search the web for information about the home builder "{builder_name}"{location_str}.

Extract ALL available information about this builder. Be thorough and capture every detail.

## Required Information:

1. BASIC INFORMATION
   - Name (official company name)
   - Description (company overview)
   - Website URL
   - Phone number
   - Email
   - Headquarters address

2. COMPANY DETAILS
   - Year founded
   - Number of employees
   - Service areas (cities/regions where they build)
   - Specialties (custom homes, production homes, luxury, etc.)
   - Price range

3. RATINGS & REVIEWS
   - Overall rating
   - Number of reviews
   - Review sources (BBB, Google, etc.)
   - Awards and certifications

4. COMMUNITIES
   - List of active communities where builder operates
   - Community names and locations

5. HOME PLANS
   - Available home plans/series
   - Plan names, square footage ranges, price ranges

6. CONTACT INFORMATION
   - Sales representatives
   - Office locations

## Output Format:
Return data as structured JSON:
{{
  "name": "string",
  "description": "string",
  "website": "string",
  "phone": "string",
  "email": "string",
  "headquarters_address": "string",
  "founded_year": number,
  "employee_count": number,
  "service_areas": ["array", "of", "locations"],
  "specialties": ["array", "of", "specialties"],
  "price_range_min": number,
  "price_range_max": number,
  "rating": number,
  "review_count": number,
  "awards": [
    {{
      "title": "string",
      "awarded_by": "string",
      "year": number
    }}
  ],
  "certifications": ["array", "of", "certifications"],
  "communities": [
    {{
      "name": "string",
      "location": "string",
      "status": "active|coming_soon"
    }}
  ],
  "home_plans": [
    {{
      "series_name": "string",
      "min_sqft": number,
      "max_sqft": number,
      "min_price": number,
      "max_price": number,
      "bedrooms": number,
      "bathrooms": number
    }}
  ],
  "confidence": {{
    "overall": 0.0-1.0,
    "field_confidence": {{
      "field_name": 0.0-1.0
    }}
  }},
  "sources": ["url1", "url2"]
}}

IMPORTANT:
- Only return data you can verify from web sources
- Include confidence scores
- List all source URLs
- If a field is not found, omit it or set to null
"""


def generate_sales_rep_collection_prompt(
    builder_name: str,
    community_name: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """Generate prompt for collecting sales representative data."""
    context = f"{builder_name}"
    if community_name:
        context += f" at {community_name}"
    if location:
        context += f" in {location}"

    return f"""
Search the web for sales representative contact information for {context}.

Find current sales representatives working for this builder/community.

## Required Information:

1. SALES REP DETAILS
   - Full name
   - Title/position
   - Phone number (direct line)
   - Email address
   - Photo URL (if available)

2. OFFICE INFORMATION
   - Office address
   - Office phone
   - Office hours

## Output Format:
Return data as structured JSON:
{{
  "sales_reps": [
    {{
      "name": "string",
      "title": "string",
      "phone": "string",
      "email": "string",
      "photo_url": "string",
      "office_address": "string",
      "office_phone": "string",
      "bio": "string",
      "is_active": true
    }}
  ],
  "confidence": {{
    "overall": 0.0-1.0
  }},
  "sources": ["url1", "url2"],
  "last_updated": "ISO date string"
}}

IMPORTANT:
- Only include reps you can verify are currently active
- Verify phone numbers and email addresses are current
- Include source URLs where rep info was found
- Mark confidence level for each rep
"""


def generate_property_collection_prompt(
    builder_name: str,
    community_name: str,
    location: str
) -> str:
    """Generate prompt for collecting property/inventory data."""
    return f"""
Search the web for available properties/homes by {builder_name} in {community_name}, {location}.

Extract ALL available information for each property. Be thorough and capture every detail.

## Required Information:

1. BASIC INFORMATION
   - Property title/name
   - Full address (street, city, state, zip)
   - Description
   - Property type (single_family, townhome, condo, etc.)
   - Status (available, under_contract, sold, model_home)

2. SPECIFICATIONS
   - Price
   - Bedrooms
   - Bathrooms
   - Square footage
   - Lot size (acres or sq ft)
   - Stories
   - Garage spaces

3. LOT DETAILS
   - Corner lot? (yes/no)
   - Cul-de-sac? (yes/no)
   - Lot backing (greenbelt, pond, street, etc.)
   - Views

4. SCHOOLS
   - School district
   - Elementary school name
   - Middle school name
   - High school name
   - School ratings (if available)

5. BUILDER-SPECIFIC
   - Model home? (yes/no)
   - Quick move-in? (yes/no)
   - Construction stage (pre_construction, under_construction, completed)
   - Estimated completion date
   - Builder plan name
   - Builder series
   - Elevation options

6. INTERIOR FEATURES
   - Flooring types
   - Countertop materials
   - Appliances
   - Game room? (yes/no)
   - Study/office? (yes/no)
   - Bonus rooms

7. OUTDOOR AMENITIES
   - Pool type (private, community, none)
   - Covered patio? (yes/no)
   - Outdoor kitchen?
   - Landscaping

8. PRICING & MARKET
   - Price per square foot
   - Days on market
   - Builder incentives
   - Upgrades included
   - Estimated upgrades value

9. HOA & RESTRICTIONS
   - HOA fee (monthly)
   - Pet restrictions
   - Lease allowed? (yes/no)

10. ENERGY & UTILITIES
    - Energy rating
    - Available internet providers

11. TAX & FINANCIAL
    - Annual property tax estimate
    - Assumable loan? (yes/no)

12. MEDIA & VIRTUAL
    - Virtual tour URL
    - Floor plan URL
    - Matterport link
    - Photo URLs

13. AVAILABILITY & STATUS
    - Property status (available, pending, sold)
    - Move-in date
    - Showing instructions

## Output Format:
Return data as structured JSON array:
{{
  "properties": [
    {{
      "title": "string",
      "address": "string",
      "city": "string",
      "state": "string",
      "zip_code": "string",
      "description": "string",
      "property_type": "string",
      "status": "string",
      "price": number,
      "beds": number,
      "baths": number,
      "sqft": number,
      "lot_size": number,
      "stories": number,
      "garage_spaces": number,
      "corner_lot": boolean,
      "cul_de_sac": boolean,
      "lot_backing": "string",
      "school_district": "string",
      "elementary_school": "string",
      "middle_school": "string",
      "high_school": "string",
      "school_ratings": {{}},
      "model_home": boolean,
      "quick_move_in": boolean,
      "construction_stage": "string",
      "estimated_completion": "date",
      "builder_plan_name": "string",
      "price_per_sqft": number,
      "days_on_market": number,
      "builder_incentives": "string",
      "upgrades_included": "string",
      "upgrades_value": number,
      "hoa_fee": number,
      "virtual_tour_url": "string",
      "floor_plan_url": "string",
      "images": ["url1", "url2"],
      "confidence": 0.0-1.0,
      "source_url": "string"
    }}
  ],
  "total_found": number,
  "sources": ["url1", "url2"]
}}

IMPORTANT:
- Find ALL available properties, not just featured ones
- Include confidence score for each property
- List source URL for each property
- If a field is not found, omit it or set to null
- Be thorough - buyers need complete information
"""
