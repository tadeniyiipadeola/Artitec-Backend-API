"""
Claude AI Prompts for Data Collection

Contains all prompts used for different collection tasks.
"""
from typing import Optional


def generate_community_collection_prompt(community_name: Optional[str], location: str) -> str:
    """Generate prompt for collecting community data."""

    # If no specific community name, do area discovery
    if not community_name:
        return f"""
Search the web for ACTIVELY DEVELOPING residential communities in {location}.

IMPORTANT SEARCH FOCUS:
- Prioritize communities that are "actively being developed" or "under development"
- Focus on MASTER-PLANNED COMMUNITIES (communities with comprehensive planning, multiple phases, extensive amenities)
- EXCLUDE communities that are "completed", "sold out", or "fully built out"
- Look for communities with ongoing construction and available inventory

Find as many ACTIVE, DEVELOPING residential communities as possible. For EACH community found, extract the following information.

Extract ALL available information about this community. Be thorough and capture every detail you can find.

## Required Information:

1. BASIC INFORMATION
   - Name (official name)
   - Description (detailed overview)
   - Location (full address if available)
   - City, State, ZIP code
   - Latitude and Longitude (coordinates)
   - Website URL
   - Phone number
   - Email

2. PROPERTY DETAILS
   - Total acres (size of community)
   - Sales office address (or welcome center address)
   - Development stage (Planning, Under Development, Active, Sold Out, Completed)
   - Total number of homes (or planned homes)
   - Total residents (current population if available)
   - Year established/founded or year development started
   - Is this a master-planned community? (yes/no - look for comprehensive planning, multiple phases, extensive amenities)
   - Current development status (active development, nearing completion, completed, etc.)

3. FINANCIAL INFORMATION
   - HOA fee (monthly amount)
   - HOA fee frequency (monthly/yearly)
   - Monthly fee (if different from HOA)
   - Tax rate (property tax rate for the area)
   - What HOA covers
   - HOA management company
   - HOA contact phone
   - HOA contact email

4. DEVELOPER & BUILDER
   - Developer name
   - List of builders operating in this community
   - Builder names and contact info

5. SCHOOLS & EDUCATION
   - School district
   - Elementary school name
   - Middle school name
   - High school name

6. AMENITIES
   - List all amenities (pool, clubhouse, trails, parks, etc.)
   - Amenity details and hours

7. REVIEWS & RATINGS
   - Overall community rating
   - Number of reviews
   - Common feedback themes

## Output Format:
Return a JSON object with "communities" array:
{{
  "communities": [
    {{
      "name": "Community Name",
      "description": "Detailed description",
      "location": "Full address",
      "city": "City",
      "state": "TX",
      "zip_code": "75XXX",
      "latitude": 32.9483,
      "longitude": -96.7297,
      "website": "https://...",
      "phone": "123-456-7890",
      "email": "email@example.com",
      "total_acres": 500.0,
      "sales_office_address": "123 Sales Office Dr",
      "development_stage": "Active",
      "total_homes": 500,
      "total_residents": 1200,
      "year_established": 2015,
      "development_start_year": 2015,
      "is_master_planned": true,
      "development_status_description": "Active development with ongoing construction",
      "hoa_fee": 150,
      "hoa_fee_frequency": "monthly",
      "monthly_fee": 150,
      "tax_rate": "2.5%",
      "hoa_management_company": "Company Name",
      "hoa_contact_phone": "123-456-7890",
      "hoa_contact_email": "hoa@example.com",
      "developer_name": "Developer Name",
      "school_district": "District Name",
      "elementary_school": "School Name",
      "middle_school": "School Name",
      "high_school": "School Name",
      "amenities": ["pool", "clubhouse", "trails"],
      "builders": [
        {{
          "name": "Builder Name",
          "website": "https://...",
          "phone": "123-456-7890"
        }}
      ],
      "rating": 4.5,
      "review_count": 100,
      "confidence": {{
        "overall": 0.85
      }},
      "sources": ["https://source1.com", "https://source2.com"]
    }}
  ]
}}

IMPORTANT:
- Return multiple communities in the "communities" array
- Only return data you can verify from web sources
- Include confidence scores
- List all source URLs where data was found
- Aim to find at least 10-20 communities in the area
"""

    # Specific community search
    return f"""
Search the web for information about the residential community "{community_name}" in {location}.

IMPORTANT: Pay special attention to:
- Whether this is a MASTER-PLANNED COMMUNITY (comprehensive planning, multiple phases, extensive amenities)
- The current development status (actively developing, nearing completion, completed)
- When development started (founding year or development start year)
- Whether the community is still actively selling homes or is sold out/completed

Extract ALL available information about this community. Be thorough and capture every detail you can find.

## Required Information:

1. BASIC INFORMATION
   - Name (official name)
   - Description (detailed overview)
   - Location (full address if available)
   - City, State, ZIP code
   - Latitude and Longitude (coordinates)
   - Website URL
   - Phone number
   - Email

2. PROPERTY DETAILS
   - Total acres (size of community)
   - Sales office address (or welcome center address)
   - Development stage (Planning, Under Development, Active, Sold Out, Completed)
   - Total number of homes (or planned homes)
   - Total residents (current population if available)
   - Year established/founded or year development started
   - Is this a master-planned community? (yes/no - look for comprehensive planning, multiple phases, extensive amenities)
   - Current development status (active development, nearing completion, completed, etc.)

3. FINANCIAL INFORMATION
   - HOA fee (monthly amount)
   - HOA fee frequency (monthly/yearly)
   - Monthly fee (if different from HOA)
   - Tax rate (property tax rate for the area)
   - What HOA covers
   - HOA management company
   - HOA contact phone
   - HOA contact email

4. DEVELOPER & BUILDER
   - Developer name
   - List of builders operating in this community
   - Builder names and contact info

5. SCHOOLS & EDUCATION
   - School district
   - Elementary school name
   - Middle school name
   - High school name

6. AMENITIES
   - List all amenities (pool, clubhouse, trails, parks, etc.)
   - Amenity details and hours

7. REVIEWS & RATINGS
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
  "latitude": number,
  "longitude": number,
  "website": "string",
  "phone": "string",
  "email": "string",
  "total_acres": number,
  "sales_office_address": "string",
  "development_stage": "string",
  "total_homes": number,
  "total_residents": number,
  "year_established": number,
  "hoa_fee": number,
  "hoa_fee_frequency": "monthly|yearly",
  "monthly_fee": number,
  "tax_rate": "string",
  "hoa_management_company": "string",
  "hoa_contact_phone": "string",
  "hoa_contact_email": "string",
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
   - Headquarters address (full street address)
   - City (headquarters city)
   - State (headquarters state - 2-letter code)
   - Postal code (ZIP code)

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
  "city": "string",
  "state": "string",
  "postal_code": "string",
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
   - Year built
   - Stories
   - Garage spaces

3. LOT DETAILS
   - Lot number (for new construction properties without assigned addresses)
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
      "year_built": number,
      "stories": number,
      "garage_spaces": number,
      "lot_number": "string",
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


def generate_sales_rep_collection_prompt(
    builder_name: str,
    community_name: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """Generate prompt for collecting sales representative data."""

    # Build context string
    context_parts = [builder_name]
    if community_name:
        context_parts.append(f"at {community_name}")
    if location:
        context_parts.append(f"in {location}")

    context = " ".join(context_parts)

    return f"""
Search the web for sales representatives working for {context}.

Find ALL sales representatives associated with this builder{' and community' if community_name else ''}. Look for:
- Builder's official website (sales team page, meet our team, contact us)
- Community website (if specific community is mentioned)
- Real estate listings with sales agent information
- Social media profiles (LinkedIn, Facebook business pages)
- Online directories and review sites

Extract the following information for EACH sales representative found:

## Required Information:

1. BASIC INFORMATION
   - Full name
   - Title/Role (e.g., "Sales Consultant", "New Home Specialist", "Community Sales Manager")
   - Phone number (direct line if available)
   - Email address
   - Photo URL (professional headshot if available)

2. PROFESSIONAL DETAILS
   - Bio/Description (professional background, experience)
   - Years of experience (if mentioned)
   - Specialties or focus areas
   - Languages spoken (if mentioned)
   - License information (if mentioned)

3. CONTACT & SOCIAL
   - LinkedIn profile URL
   - Office location/address
   - Availability hours

## Output Format:
Return a JSON object with "sales_reps" array:
{{
  "sales_reps": [
    {{
      "name": "Full Name",
      "title": "Sales Consultant",
      "phone": "555-123-4567",
      "email": "email@builder.com",
      "photo_url": "https://example.com/photo.jpg",
      "bio": "Professional bio and background information",
      "confidence": 0.9,
      "source_url": "https://builder.com/team"
    }}
  ],
  "total_found": number,
  "sources": ["url1", "url2"]
}}

IMPORTANT:
- Find ALL sales representatives, not just featured ones
- Verify that the rep is associated with {builder_name}{f' at {community_name}' if community_name else ''}
- Include confidence score (0.0-1.0) for each rep based on source reliability
- List the source URL where you found each rep's information
- If a field is not found, omit it or set to null
- Only include reps that are currently active (not marked as "former" or "previous")
- Be thorough - complete sales team information is essential
"""
