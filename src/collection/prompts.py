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
Search the web for ALL residential communities in {location}.

IMPORTANT SEARCH STRATEGY:
- Search for ALL types of communities: actively developing, completed, sold out, or under development
- Include MASTER-PLANNED COMMUNITIES (comprehensive planning, multiple phases, extensive amenities)
- Include smaller neighborhood communities and subdivisions
- Cast a WIDE NET - we want comprehensive coverage of the entire area

DATA QUALITY REQUIREMENTS:
- For EACH field, try to find data from AT LEAST 2 different sources
- Cross-validate data across multiple websites when possible
- Assign confidence >0.70 ONLY if data is verified from 2+ independent sources
- Assign confidence 0.50-0.70 for single-source data that appears reliable
- Assign confidence <0.50 for uncertain or incomplete data

RECOMMENDED DATA SOURCES (check multiple):
- Realtor.com, Zillow, Trulia (real estate listings)
- Official community websites
- Builder websites (Perry Homes, David Weekley, etc.)
- HOA management company websites
- County property records and assessor websites
- Local real estate agency websites
- Google Maps and reviews
- Community Facebook pages or social media

COMMUNITY VERIFICATION AND DEDICATED WEBSITES:
- When you discover a potential community name, SEARCH for that community's dedicated website
- Many communities have their own official websites (e.g., "txgrandranch.com" for TX Grand Ranch)
- Search patterns to try: "[Community Name] official website", "[Community Name] [City] TX"
- Community websites are typically the BEST source for accurate data (highest confidence)
- If a community website exists, use it as the PRIMARY data source

COMPLETENESS EMPHASIS:
- If a field is missing, perform ADDITIONAL targeted searches specifically for that information
- For small communities, check builder websites and local real estate listings
- ALWAYS attempt to find the community's official website first
- If you can't find data after thorough searching, leave the field empty rather than guessing

Find as many residential communities as possible in {location}. For EACH community found, extract the following information.

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
   - List all amenities the community offers. Use these standardized names when applicable:
     * "Pool" or "Swimming pool"
     * "Water park" or "Waterpark"
     * "Fitness center" or "Gym"
     * "Clubhouse" or "Club house"
     * "Walking/biking trails" or "Trails"
     * "Playground" or "Children's playground"
     * "Dog park" or "Pet park"
     * "Tennis courts"
     * "Basketball courts"
     * "Soccer field"
     * "Golf course"
     * "Lake access" or "Water access"
     * "24/7 Security" or "Gated security"
     * "Master-planned community"
   - Include any other amenities not listed above

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
- Include confidence scores reflecting the number of sources (2+ sources = higher confidence)
- List ALL source URLs where data was found for each community
- Aim to find as many communities as possible in the area (target: 15-30+ depending on market size)
- Perform MULTIPLE search passes if needed to ensure comprehensive coverage:
  * First pass: Major real estate sites (Realtor.com, Zillow)
  * Second pass: Builder websites and community sites
  * Third pass: Local listings and county records
- For small markets with fewer communities, ensure each community has COMPLETE data
"""

    # Specific community search
    return f"""
Search the web for information about the residential community "{community_name}" in {location}.

DATA QUALITY REQUIREMENTS:
- For EACH field, try to find data from AT LEAST 2 different sources
- Cross-validate data across multiple websites when possible
- Assign confidence >0.70 ONLY if data is verified from 2+ independent sources
- Assign confidence 0.50-0.70 for single-source data that appears reliable
- Assign confidence <0.50 for uncertain or incomplete data

RECOMMENDED DATA SOURCES (check multiple):
- Realtor.com, Zillow, Trulia (real estate listings)
- Official community website
- Builder websites operating in this community
- HOA management company website
- County property records and assessor websites
- Google Maps and reviews
- Community Facebook pages or social media

COMMUNITY VERIFICATION AND DEDICATED WEBSITE:
- SEARCH for this community's dedicated official website as your PRIMARY data source
- Many communities have their own websites (e.g., "txgrandranch.com" for TX Grand Ranch)
- Search patterns to try: "{community_name} official website", "{community_name} {location}"
- Community websites are typically the BEST source for accurate data (highest confidence)

COMPLETENESS EMPHASIS:
- If a field is missing, perform ADDITIONAL targeted searches specifically for that information
- Check builder websites for detailed community information
- Check the community's official website first (if it exists)
- If you can't find data after thorough searching, leave the field empty rather than guessing

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
   - List all amenities the community offers. Use these standardized names when applicable:
     * "Pool" or "Swimming pool"
     * "Water park" or "Waterpark"
     * "Fitness center" or "Gym"
     * "Clubhouse" or "Club house"
     * "Walking/biking trails" or "Trails"
     * "Playground" or "Children's playground"
     * "Dog park" or "Pet park"
     * "Tennis courts"
     * "Basketball courts"
     * "Soccer field"
     * "Golf course"
     * "Lake access" or "Water access"
     * "24/7 Security" or "Gated security"
     * "Master-planned community"
   - Include any other amenities not listed above

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


def generate_builder_collection_prompt(builder_name: str, location: Optional[str] = None, community_name: Optional[str] = None) -> str:
    """Generate prompt for collecting builder data.

    Args:
        builder_name: Name of the builder to search for
        location: City, State location context
        community_name: STRICT - Specific community name to search within (for backfill jobs)
    """
    # Escape curly braces in location to prevent f-string formatting errors
    safe_location = str(location).replace('{', '{{').replace('}', '}}') if location else None
    safe_community = str(community_name).replace('{', '{{').replace('}', '}}') if community_name else None

    # Build search context based on available information
    if safe_community and safe_location:
        search_context = f" in the '{safe_community}' community in {safe_location}"
        strict_instruction = f"""
CRITICAL - STRICT COMMUNITY SEARCH:
You MUST search for this builder specifically in the '{safe_community}' community in {safe_location}.
- Search queries should include: "{builder_name} {safe_community} {safe_location}"
- Only return information if the builder actually operates in '{safe_community}'
- Do NOT return information about this builder from other communities or locations
- The community name in your response MUST be '{safe_community}' if you find a match
- If you cannot confirm the builder operates in '{safe_community}', return null/empty data
"""
    elif safe_location:
        search_context = f" in {safe_location}"
        strict_instruction = ""
    else:
        search_context = ""
        strict_instruction = ""

    # Build community instruction based on whether we have strict community context
    if safe_community:
        community_instruction = f"""
6. COMMUNITIES (CRITICAL - STRICT MATCH REQUIRED!)
   IMPORTANT: This search is for the builder in the SPECIFIC community '{safe_community}'.

   - Primary community: MUST be '{safe_community}' if you confirm the builder operates there
   - If you CANNOT confirm the builder operates in '{safe_community}', return null for primary_community
   - Do NOT substitute with a different community name, even if similar
   - Community name, city, and state must match exactly

   Example response if builder is confirmed in '{safe_community}':
   "primary_community": {{"name": "{safe_community}", "city": "...", "state": "..."}}

   If builder is NOT in '{safe_community}', return:
   "primary_community": null
"""
    else:
        community_instruction = f"""
6. COMMUNITIES (IMPORTANT!)
   - Primary community where this builder operates{search_context}
   - Community name, city, and state
   - List of ALL active communities where builder operates{search_context}

   IMPORTANT: Use the location{search_context} to search for communities where this builder is actively building.
   Search for "{builder_name} communities{search_context}" or "{builder_name} new home communities{search_context}"

   NOTE: We need the community location to match the builder to the correct community.
   Example:
   "primary_community": {{"name": "Willow Bend", "city": "Plano", "state": "TX"}}
   "all_communities": [{{"name": "Willow Bend", "city": "Plano", "state": "TX"}}, {{"name": "Legacy Hills", "city": "Frisco", "state": "TX"}}]
"""

    return f"""
Search the web for information about the home builder "{builder_name}"{search_context}.
{strict_instruction}

Extract ALL available information about this builder. Be thorough and capture every detail.

## Required Information:

1. BASIC INFORMATION
   - Name (official company name)
   - Description (company overview)
   - Website URL (corporate website)

2. HEADQUARTERS INFORMATION (Corporate Office - SEPARATE from sales office)
   - Headquarters address (FULL address of corporate headquarters including street, city, state, and ZIP code)

3. SALES OFFICE INFORMATION (Local customer-facing office{search_context})
   CRITICAL: The following fields are for the LOCAL SALES OFFICE{search_context} where customers go to buy homes.
   This is NOT the corporate headquarters - it's the local sales center, information center, or model home location.

   - Title (Office type: "Sales Office", "Information Center", "Model Home Center", etc.)
   - Sales office address (IMPORTANT: FULL street address of the local sales office{search_context} including street number, street name, city, state, and ZIP code)
   - Phone number (IMPORTANT: Phone number for the SALES OFFICE at{search_context} - NOT corporate headquarters phone)
   - Email (IMPORTANT: Email for the SALES OFFICE at{search_context} - NOT corporate headquarters email. Look for sales team email, community-specific email, or local office email)
   - City (City of the sales office{search_context}, extracted from the sales office address above)
   - State (2-letter state code of the sales office{search_context}, extracted from the sales office address above)
   - Postal code (IMPORTANT: ZIP code extracted from the sales office address above. Must match the ZIP in the sales office address field)

4. COMPANY DETAILS
   - Year founded
   - Number of employees
   - Service areas (cities/regions where they build)
   - Specialties (custom homes, production homes, luxury, etc.)
   - Price range

5. RATINGS & REVIEWS
   - Overall rating
   - Number of reviews
   - Review sources (BBB, Google, etc.)
   - Awards and certifications

{community_instruction}

7. HOME PLANS
   - Available home plans/series
   - Plan names, square footage ranges, price ranges

8. CONTACT INFORMATION
   - Sales representatives
   - Office locations

## Output Format:
Return data as structured JSON:
{{
  "name": "string",
  "description": "string",
  "website": "string",
  "headquarters_address": "string (corporate HQ full address with street, city, state, ZIP)",
  "title": "string (office type: 'Sales Office', 'Information Center', etc.)",
  "sales_office_address": "string (local sales office full address with street, city, state, ZIP)",
  "phone": "string (sales office phone)",
  "email": "string (sales office email)",
  "city": "string (sales office city, extracted from sales_office_address)",
  "state": "string (sales office state, extracted from sales_office_address)",
  "postal_code": "string (sales office ZIP, extracted from sales_office_address)",
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
  "primary_community": {{
    "name": "string",
    "city": "string",
    "state": "string (2-letter state code)"
  }},
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


def generate_community_builders_prompt(community_name: str, location: str) -> str:
    """
    Generate prompt for discovering builders operating in a specific community.

    This is used by the backfill endpoint to find actual builder names before
    creating individual builder discovery jobs.
    """
    return f"""
Search the web to find which home builders operate in {community_name} located in {location}.

IMPORTANT:
- Return a LIST of builder NAMES only (not the community name itself)
- {community_name} is a COMMUNITY, not a builder - do not include it in the results
- Look for actual builder/construction companies that build homes in this community
- Common sources: community website, realtor.com, zillow, builder websites

RECOMMENDED DATA SOURCES:
- Official {community_name} community website
- Realtor.com and Zillow listings for {community_name}
- Local real estate agent listings
- Builder websites mentioning {community_name}
- Community HOA website
- Google search for "{community_name} home builders"

## Output Format:
Return data as structured JSON:
{{
  "builders": [
    {{
      "name": "Builder Company Name"
    }}
  ],
  "sources": ["url1", "url2", "url3"]
}}

IMPORTANT NOTES:
- Only include ACTUAL BUILDERS/CONSTRUCTION COMPANIES
- DO NOT include:
  * The community name itself
  * Real estate agencies
  * HOA management companies
  * Property management firms
- If you can't find any builders, return an empty array
- Each builder should be a separate object with just the "name" field
"""
