# Property Job Results Viewer

View detailed property information collected by property inventory jobs, including all the new fields like builder plan name, move-in date, features, and more.

## What It Does

The `view_property_job_results.py` script allows you to:

1. List all property inventory jobs
2. Select a job to view
3. See all properties collected by that job with full details:
   - Property name, description, and location
   - **Builder plan name and series** (NEW)
   - **Move-in date** (NEW)
   - Builder and community IDs for linking
   - Property specs (beds, baths, sqft)
   - Features (game room, study, pool, patio, etc.) (NEW)
   - School information with ratings (NEW)
   - Market information (incentives, upgrades, days on market) (NEW)
   - Virtual tour links (NEW)
   - Collection metadata (NEW)

## Usage

### 1. Ensure the API is running

```bash
# Terminal 1 - Start the backend API
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
source .venv/bin/activate
python app.py
```

### 2. Run the viewer

```bash
# Terminal 2 - Run the property viewer
cd "/Users/adeniyi_family_executor/Documents/Development/Artitec Backend Development"
source .venv/bin/activate
python view_property_job_results.py
```

## Example Output

```
================================================================================
PROPERTY JOB RESULTS VIEWER
================================================================================

📋 Fetching property inventory jobs...
✅ Found 179 property inventory jobs

1. ✅ JOB-1764196511-A656B3
   Status: completed
   Properties Found: 15
   Created: 2025-11-26 16:45:00
   Builder ID: 45
   Community ID: 78

2. ⏳ JOB-1764196522-B123C4
   Status: pending
   Properties Found: 0
   Created: 2025-11-26 16:46:00
   Builder ID: 46
   Community ID: 79

Enter job number to view properties (or 'q' to quit): 1

🔍 Fetching properties from job JOB-1764196511-A656B3...
✅ Found 15 properties

================================================================================
📍 Beautiful 4BR Executive Home in Lakes of Bella Terra
================================================================================

💰 Price: $425,000.00
📍 Location: 1234 Lakeside Drive, Richmond, TX
🏠 Specs: 4 bed | 2.5 bath | 2,500 sqft

🏗️  BUILDER INFORMATION:
   Plan Name: The Oakmont
   Series: Executive Series
   Builder ID: 45
   Community ID: 78

📅 AVAILABILITY:
   Move-in Date: January 2026
   Listing Status: available
   Quick Move-In: Yes
   Model Home: No
   Construction Stage: completed

🏡 PROPERTY DETAILS:
   Type: single_family
   Stories: 2
   Garage: 2 spaces

✨ FEATURES:
   • Game Room
   • Study/Office
   • Covered Patio
   • Outdoor Kitchen
   • Private Pool

🎓 SCHOOLS:
   District: Fort Bend ISD
   Elementary: Travis Elementary (Rating: 9/10)
   Middle: Garcia Middle School (Rating: 8/10)
   High: Foster High School (Rating: 9/10)

💼 MARKET INFO:
   Days on Market: 5
   Incentives: $10,000 closing cost assistance
   Upgrades: Upgraded flooring, smart home package
   Upgrades Value: $25,000.00

🔗 VIRTUAL TOURS:
   Virtual Tour: https://sitterlehomes.com/tour/123
   Floor Plan: https://sitterlehomes.com/floorplan/123.pdf
   Matterport: https://matterport.com/show/xyz

📊 COLLECTION METADATA:
   Source: https://sitterlehomes.com/property/123
   Data Confidence: 95%

--------------------------------------------------------------------------------

[... 14 more properties ...]

================================================================================
✅ Displayed 15 properties from job JOB-1764196511-A656B3
================================================================================
```

## Features Displayed

### Core Information
- Property title and description
- Full address and location
- Price and core specs (beds, baths, sqft)

### Builder Information (NEW)
- **Builder plan name** - e.g., "The Oakmont"
- **Builder series** - e.g., "Executive Series"
- Builder ID (for linking to builder profile)
- Community ID (for linking to community details)

### Availability (NEW)
- **Move-in date** - When the home is available
- Listing status (available, pending, sold)
- Quick move-in flag
- Model home flag
- Construction stage

### Property Details (NEW)
- Property type (single_family, townhome, condo)
- Number of stories
- Garage spaces

### Features (NEW)
- Game room
- Study/office
- Covered patio
- Outdoor kitchen
- Pool type (private, community, none)
- And more...

### School Information (NEW)
- School district
- Elementary, middle, and high school names
- School ratings (1-10 scale)

### Market Information (NEW)
- Days on market
- Builder incentives
- Included upgrades
- Upgrades value

### Virtual Tours (NEW)
- Virtual tour URL
- Floor plan URL
- Matterport link

### Collection Metadata (NEW)
- Source URL where data was collected
- Data confidence score (0-1, displayed as percentage)

## How It Works

1. **Fetches Property Jobs**: Queries the `/admin/collection/jobs` endpoint for all property inventory jobs

2. **Gets Job Changes**: For the selected job, fetches all changes from `/admin/collection/jobs/{job_id}/changes` to find property IDs

3. **Fetches Property Details**: For each property ID, calls `/property/{id}` to get complete property information with all 80+ fields

4. **Displays Results**: Formats and displays all the property information in an easy-to-read format

## API Endpoints Used

- `GET /v1/admin/collection/jobs` - List property inventory jobs
- `GET /v1/admin/collection/jobs/{job_id}` - Get job details
- `GET /v1/admin/collection/jobs/{job_id}/changes` - Get properties created by job
- `GET /v1/property/{id}` - Get full property details

## Requirements

- Python 3.8+
- `requests` library (already in requirements.txt)
- Backend API running on http://127.0.0.1:8000

## Next Steps

Once you've verified the property data is being collected correctly:

1. **Review the data quality** - Check that all fields are populated
2. **Update the frontend** - Use the iOS integration guide in `Artitec-iOS-UI/PROPERTY_INTEGRATION_GUIDE.md`
3. **Create more property jobs** - Use `bulk_property_collection.py` to create jobs for all your builder-community associations

## Troubleshooting

**No property jobs found:**
- Run `python bulk_property_collection.py` to create property inventory jobs

**Properties have missing fields:**
- Check the collection job logs: `GET /v1/admin/collection/jobs/{job_id}/logs`
- The AI collector may not have found all information on the builder's website

**API connection errors:**
- Ensure the backend API is running: `python app.py`
- Check that the API is accessible at http://127.0.0.1:8000

## Related Documentation

- **Backend API Documentation**: `/PROPERTY_API_DOCUMENTATION.md`
- **iOS Integration Guide**: `/Artitec-iOS-UI/PROPERTY_INTEGRATION_GUIDE.md`
- **Bulk Property Collection**: `bulk_property_collection.py`
