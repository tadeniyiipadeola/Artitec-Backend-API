"""
Community Collector Service

Collects data about residential communities.
"""
import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from model.profiles.community import Community, CommunityBuilder
from model.profiles.builder import BuilderProfile
from model.collection import CollectionJob
from .base_collector import BaseCollector
from .prompts import generate_community_collection_prompt
from .status_management import ImprovedCommunityStatusManager
from src.media_scraper import MediaScraper

logger = logging.getLogger(__name__)

# Default admin user ID for collector-created entities
DEFAULT_ADMIN_USER_ID = "USR-1763443503-N3UTFX"


def parse_currency(value: str) -> Optional[float]:
    """
    Parse currency string to float.

    Examples:
        "$1,400" -> 1400.0
        "$16,800" -> 16800.0
        "1400" -> 1400.0
    """
    if not value:
        return None

    # Remove $, commas, and spaces
    cleaned = str(value).replace('$', '').replace(',', '').strip()

    try:
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def format_currency(amount: float) -> str:
    """
    Format number as currency string.

    Examples:
        1400.0 -> "$1,400"
        16800.0 -> "$16,800"
    """
    if amount is None:
        return None

    return f"${amount:,.0f}"


def calculate_fees(hoa_fee: Any, hoa_fee_frequency: str, monthly_fee: Any) -> tuple:
    """
    Calculate and format community_dues (yearly) and monthly_fee.

    Returns:
        (community_dues, monthly_fee) both formatted as currency strings
    """
    # Parse input values
    hoa_amount = parse_currency(hoa_fee) if hoa_fee else None
    monthly_amount = parse_currency(monthly_fee) if monthly_fee else None
    frequency = str(hoa_fee_frequency).lower() if hoa_fee_frequency else None

    # Determine yearly and monthly amounts
    yearly_amount = None
    final_monthly = None

    if hoa_amount and frequency:
        if 'year' in frequency or 'annual' in frequency:
            # HOA fee is yearly
            yearly_amount = hoa_amount
            final_monthly = hoa_amount / 12
        elif 'month' in frequency:
            # HOA fee is monthly
            final_monthly = hoa_amount
            yearly_amount = hoa_amount * 12
        elif 'quarter' in frequency:
            # Quarterly
            yearly_amount = hoa_amount * 4
            final_monthly = yearly_amount / 12

    # If we have monthly_fee but no HOA fee, use it
    if monthly_amount and not final_monthly:
        final_monthly = monthly_amount
        yearly_amount = monthly_amount * 12

    # If we have yearly but no monthly, calculate monthly
    if yearly_amount and not final_monthly:
        final_monthly = yearly_amount / 12

    # Format as currency
    community_dues = format_currency(yearly_amount) if yearly_amount else None
    monthly_fee_formatted = format_currency(final_monthly) if final_monthly else None

    return community_dues, monthly_fee_formatted


def determine_availability_status(
    development_stage: str,
    development_status: str,
    total_homes: Optional[int] = None,
    available_properties_count: Optional[int] = None,
    sold_properties_count: Optional[int] = None
) -> str:
    """
    Determine availability_status based on community and inventory data.

    Returns: available, limited_availability, sold_out, or closed

    Logic Priority:
    1. If development is completed/inactive → sold_out
    2. If we have property inventory data → calculate based on availability %
    3. If no inventory data → infer from development stage

    Thresholds:
    - sold_out: 0% available OR 100% sold
    - limited_availability: ≤10% available OR ≥90% sold
    - available: >10% available
    """
    # Rule 1: Completed/Inactive communities are sold out
    if development_stage == "Completed" or development_status == "inactive":
        return "sold_out"

    # Rule 2: Calculate from actual property inventory if available
    if total_homes and total_homes > 0:
        # Prefer available count
        if available_properties_count is not None:
            availability_percentage = (available_properties_count / total_homes) * 100

            if availability_percentage == 0:
                return "sold_out"
            elif availability_percentage <= 10:  # 10% or less remaining
                return "limited_availability"
            else:
                return "available"

        # Alternative: Use sold count if available count not known
        elif sold_properties_count is not None:
            sold_percentage = (sold_properties_count / total_homes) * 100

            if sold_percentage >= 100:
                return "sold_out"
            elif sold_percentage >= 90:  # 90%+ sold = limited availability
                return "limited_availability"
            else:
                return "available"

    # Rule 3: Fallback - infer from development status
    if development_status in ["planned", "under_development", "active"]:
        return "available"

    # Default
    return "available"


def normalize_development_stage(stage: str) -> Optional[str]:
    """
    Normalize development stage to standard format: Phase 1-5 or Completed.

    Examples:
        "phase 1" -> "Phase 1"
        "Phase I" -> "Phase 1"
        "1" -> "Phase 1"
        "complete" -> "Completed"
        "finished" -> "Completed"
        "under development" -> "Phase 1"
    """
    if not stage:
        return None

    stage_lower = str(stage).lower().strip()

    # Check for completed/finished
    if any(word in stage_lower for word in ['complete', 'finished', 'done', 'sold out', 'final']):
        return "Completed"

    # Extract phase number using regex
    # Look for patterns like: "phase 1", "phase i", "1", "i", etc.
    import re

    # Map of roman numerals to numbers
    roman_to_int = {
        'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
        '1': 1, '2': 2, '3': 3, '4': 4, '5': 5
    }

    # Try to find phase number
    for pattern in [
        r'phase\s*([1-5ivIV]+)',  # "phase 1", "phase I"
        r'^([1-5])$',  # Just "1"
        r'^([ivIV]+)$',  # Just "I"
    ]:
        match = re.search(pattern, stage_lower)
        if match:
            phase_str = match.group(1).lower()
            if phase_str in roman_to_int:
                phase_num = roman_to_int[phase_str]
                return f"Phase {phase_num}"

    # Default mappings for common terms
    if any(word in stage_lower for word in ['planning', 'pre-development']):
        return "Phase 1"
    elif any(word in stage_lower for word in ['under construction', 'building', 'development']):
        return "Phase 2"
    elif any(word in stage_lower for word in ['active', 'selling', 'sales']):
        return "Phase 3"

    # If we can't determine, return original value capitalized
    return stage.strip().title() if stage else None


def generate_enterprise_number_hoa(state: str, year_founded: int, community_name: str, db: Session) -> str:
    """
    Generate unique enterprise_number_hoa in format: HOA-{STATE}-{YEAR}-{INITIALS}-{SEQ}

    Example: HOA-TX-2010-HP-001

    Args:
        state: Two-letter state code (e.g., "TX")
        year_founded: Year the community was founded (e.g., 2010)
        community_name: Name of the community (e.g., "Highland Park")
        db: Database session to check for uniqueness

    Returns:
        Unique enterprise number in format HOA-STATE-YEAR-INITIALS-SEQ
    """
    # Extract initials from community name
    # Remove common words and get first letter of each remaining word
    words = re.findall(r'\b[A-Za-z]+\b', community_name)
    # Take first letter of each word, uppercase
    initials = ''.join([word[0].upper() for word in words if word.lower() not in ['the', 'at', 'a', 'an']])

    # Limit initials to 2-4 characters
    if len(initials) > 4:
        initials = initials[:4]
    elif len(initials) == 0:
        initials = "XX"

    # Format: HOA-STATE-YEAR-INITIALS
    state_code = (state or "XX").upper()[:2]
    year_str = str(year_founded) if year_founded else "0000"

    # Check for existing enterprise numbers with similar pattern
    base_pattern = f"HOA-{state_code}-{year_str}-{initials}"

    # Find highest sequence number for this pattern
    existing = db.query(Community).filter(
        Community.enterprise_number_hoa.like(f"{base_pattern}%")
    ).all()

    if not existing:
        # No conflicts, use sequence 001
        return f"{base_pattern}-001"

    # Find highest sequence number
    max_seq = 0
    for community in existing:
        if community.enterprise_number_hoa:
            # Extract sequence number from format: HOA-XX-XXXX-XXXX-NNN
            parts = community.enterprise_number_hoa.split('-')
            if len(parts) >= 5:
                try:
                    seq = int(parts[-1])
                    max_seq = max(max_seq, seq)
                except ValueError:
                    continue

    # Increment and format with leading zeros
    next_seq = max_seq + 1
    return f"{base_pattern}-{next_seq:03d}"


class CommunityCollector(BaseCollector):
    """
    Collects data about residential communities.

    Workflow:
    1. Search web for community information
    2. Match discovered community to existing record (or create new)
    3. Detect changes in community data
    4. Discover builders operating in community
    5. Create cascade jobs for each builder
    """

    def __init__(self, db: Session, job_id: str):
        super().__init__(db, job_id)
        self.community = None
        self.status_manager = ImprovedCommunityStatusManager(db)
        if self.job.entity_id:
            self.community = self.db.query(Community).filter(
                Community.id == self.job.entity_id
            ).first()

    def run(self):
        """Execute community data collection."""
        try:
            self.update_job_status("running")
            self.log("Starting community collection job", "INFO", "initialization")

            # Get community name and location from job
            if self.community:
                community_name = self.community.name
                location = f"{self.community.city}, {self.community.state}"
                self.log(f"Updating existing community: {community_name}", "INFO", "initialization",
                        {"community_id": self.community.id, "location": location})
            else:
                # For discovery jobs, get from search_query
                search_query = self.job.search_query
                # Extract location from search_filters
                filters = self.job.search_filters or {}
                location_from_filters = filters.get("location", "")

                # Detect if search_query is just a location (City, State format) vs. a community name
                # Pattern: "City, ST" or "City, State" (e.g., "Plano, TX", "McKinney, Texas")
                is_location_only = False
                if search_query:
                    # Check if it matches location pattern: text, 2-letter state code OR text, state name
                    import re
                    location_pattern = r'^[A-Za-z\s]+,\s*([A-Z]{2}|[A-Za-z\s]+)$'
                    if re.match(location_pattern, search_query.strip()):
                        is_location_only = True
                        location = search_query
                        community_name = None
                        self.log(f"Detected location-only search: {search_query} → triggering area discovery",
                                "INFO", "initialization",
                                {"search_query": search_query, "mode": "area_discovery_auto"})
                    else:
                        community_name = search_query
                        location = location_from_filters
                        self.log(f"Searching for specific community: {community_name} in {location}",
                                "INFO", "initialization",
                                {"search_query": community_name, "location": location})
                else:
                    community_name = None
                    location = location_from_filters
                    self.log(f"Area discovery mode for location: {location}", "INFO", "initialization",
                            {"location": location, "mode": "area_discovery"})

            # Call Claude to collect community data
            prompt = generate_community_collection_prompt(community_name, location)
            # Use higher token limit for area discovery (multiple communities)
            # Increased from 16000 to 24000 for better coverage
            max_tokens = 24000 if not community_name else 12000

            self.log(f"Calling Claude API (max_tokens={max_tokens})...", "INFO", "searching")
            collected_data = self.call_claude(prompt, max_tokens=max_tokens)
            self.log("Claude API call completed successfully", "SUCCESS", "searching")

            # Check for raw_response (non-JSON response from Claude)
            if "raw_response" in collected_data:
                raw_text = collected_data["raw_response"]
                error_msg = (
                    f"Claude returned non-JSON response. "
                    f"Response preview: {raw_text[:200]}..."
                )
                self.log(error_msg, "ERROR", "parsing", {"raw_response_length": len(raw_text)})
                logger.error(error_msg)
                self.update_job_status("failed", error_message="Claude returned non-JSON response")
                return

            # Log what we got back
            self.log(f"Claude response keys: {list(collected_data.keys())}", "INFO", "parsing")
            logger.info(f"Claude response keys: {list(collected_data.keys())}")

            if "communities" in collected_data:
                self.log(f"Found communities array with {len(collected_data['communities'])} items", "INFO", "parsing")
                logger.info(f"Found communities array with {len(collected_data['communities'])} items")

            # Check for raw_response (non-JSON response)
            if "raw_response" in collected_data:
                self.log("Claude returned non-JSON response", "WARNING", "parsing")
                logger.warning("Claude returned non-JSON response")
                self.update_job_status("failed", error_message="Claude returned non-JSON response")
                return

            # Check if this is area discovery (multiple communities)
            if "communities" in collected_data and not community_name:
                # Area discovery mode - process multiple communities
                try:
                    self.log("Entering area discovery mode", "INFO", "parsing")
                    communities_list = collected_data.get("communities", [])
                    self.log(f"Area discovery found {len(communities_list)} communities", "SUCCESS", "parsing",
                            {"count": len(communities_list)})

                    new_communities = 0

                    # PHASE 1: Create ALL community records first
                    self.log(f"Creating {len(communities_list)} community records", "INFO", "saving")
                    for idx, community_data in enumerate(communities_list, 1):
                        try:
                            community_name_current = community_data.get("name", "Unknown")
                            self.log(f"Creating community {idx}/{len(communities_list)}: {community_name_current}",
                                    "INFO", "saving", {"progress": f"{idx}/{len(communities_list)}"})

                            # Process each discovered community
                            self._process_new_community(community_data)
                            new_communities += 1

                            # Update progress after each community
                            self.update_progress(
                                items_found=len(communities_list),
                                new_entities_found=new_communities
                            )
                        except Exception as e:
                            error_msg = f"Failed to process community {idx}: {str(e)}"
                            self.log(error_msg, "ERROR", "saving", {"error": str(e), "community_name": community_name_current})
                            logger.error(error_msg, exc_info=True)
                            # Continue with next community instead of failing entire job
                            continue

                    self.log(
                        f"Created {new_communities} community records",
                        "SUCCESS",
                        "saving",
                        {"communities_created": new_communities}
                    )

                    # Auto-scrape media for communities (area discovery mode)
                    self._scrape_community_media()

                    # PHASE 2: Populate community_builders table
                    # This happens AFTER community creation but BEFORE builder job creation
                    # Allows iOS app to display builder names immediately while full builder profiles are collected later
                    self.log("Populating community_builders table with discovered builder names", "INFO", "saving")
                    for community_data in communities_list:
                        try:
                            self._populate_builder_cards(community_data)
                        except Exception as e:
                            community_name_for_error = community_data.get("name", "Unknown")
                            error_msg = f"Failed to populate builder cards for {community_name_for_error}: {str(e)}"
                            self.log(error_msg, "ERROR", "saving", {"error": str(e), "community": community_name_for_error})
                            logger.error(error_msg, exc_info=True)
                            continue

                    # PHASE 2.5: Create builder collection jobs from community_builders entries
                    # This creates jobs for full builder profile collection from the builder cards we just populated
                    self.log("Creating builder collection jobs from community_builders table", "INFO", "builder_jobs")
                    for community_data in communities_list:
                        try:
                            # Fetch the Community object by community_id
                            community_id = community_data.get("id")
                            if not community_id:
                                continue

                            community_obj = self.db.query(Community).filter(
                                Community.community_id == community_id
                            ).first()

                            if community_obj:
                                self._create_builder_jobs_from_cards(community_obj)
                        except Exception as e:
                            community_name_for_error = community_data.get("name", "Unknown")
                            error_msg = f"Failed to create builder jobs for {community_name_for_error}: {str(e)}"
                            self.log(error_msg, "ERROR", "builder_jobs", {"error": str(e), "community": community_name_for_error})
                            logger.error(error_msg, exc_info=True)
                            continue

                    # PHASE 3: Builder discovery is now DISABLED during initial collection
                    # Builder jobs will be created AFTER communities are approved by admin
                    # This prevents wasting resources on communities that may be rejected
                    builder_jobs_created = 0
                    self.log(
                        f"Builder discovery deferred - will be triggered after community approval",
                        "INFO",
                        "saving",
                        {"deferred_builders": True, "communities_pending_approval": new_communities}
                    )

                    # Note: Builder data is already stored in the proposed_entity_data JSON
                    # When admin approves a community, they can trigger builder discovery manually
                    # or it can be automated through an approval webhook

                    # COMMENTED OUT: Automatic builder job creation
                    # for community_data in communities_list:
                    #     try:
                    #         builder_jobs = self._create_builder_discovery_jobs(community_data)
                    #         builder_jobs_created += builder_jobs
                    #     except Exception as e:
                    #         community_name_for_error = community_data.get("name", "Unknown")
                    #         error_msg = f"Failed to create builder jobs for {community_name_for_error}: {str(e)}"
                    #         self.log(error_msg, "ERROR", "saving", {"error": str(e), "community": community_name_for_error})
                    #         logger.error(error_msg, exc_info=True)
                    #         continue

                    # Update job results
                    self.update_job_status(
                        "completed",
                        items_found=len(communities_list),
                        new_entities_found=new_communities
                    )

                    self.log(
                        f"Area discovery completed: {len(communities_list)} communities found (builder discovery deferred until approval)",
                        "SUCCESS", "completed",
                        {"communities": len(communities_list), "builder_jobs_queued": builder_jobs_created, "deferred": True}
                    )

                except Exception as e:
                    error_msg = f"Area discovery processing failed: {str(e)}"
                    self.log(error_msg, "ERROR", "failed", {"error": str(e), "error_type": type(e).__name__})
                    logger.error(error_msg, exc_info=True)
                    self.update_job_status("failed", error_message=error_msg)
                    raise

            else:
                # Single community mode (specific search or update)
                try:
                    self.log("Entering single community mode", "INFO", "parsing")

                    # Store collected_data for media scraping later
                    self.latest_collected_data = collected_data

                    # Process collected data
                    if self.community:
                        # Update existing community
                        self.log(f"Updating existing community: {self.community.name}", "INFO", "saving")
                        self._process_existing_community(collected_data)
                    else:
                        # Create new community
                        community_name_found = collected_data.get("name", "Unknown")
                        self.log(f"Creating new community: {community_name_found}", "INFO", "saving")
                        self._process_new_community(collected_data)

                    # Populate community_builders table for single community
                    self.log("Populating community_builders table with discovered builder names", "INFO", "saving")
                    self._populate_builder_cards(collected_data)

                    # Create builder collection jobs from community_builders entries
                    self.log("Creating builder collection jobs from community_builders table", "INFO", "builder_jobs")
                    try:
                        # Fetch the Community object by community_id
                        community_id = collected_data.get("id")
                        if community_id:
                            community_obj = self.db.query(Community).filter(
                                Community.community_id == community_id
                            ).first()

                            if community_obj:
                                self._create_builder_jobs_from_cards(community_obj)
                    except Exception as e:
                        community_name_for_error = collected_data.get("name", "Unknown")
                        error_msg = f"Failed to create builder jobs for {community_name_for_error}: {str(e)}"
                        self.log(error_msg, "ERROR", "builder_jobs", {"error": str(e), "community": community_name_for_error})
                        logger.error(error_msg, exc_info=True)

                    # Builder discovery is now DISABLED during initial collection
                    # Builder jobs will be created AFTER community is approved by admin
                    builder_jobs_created = 0
                    self.log(
                        f"Builder discovery deferred - will be triggered after community approval",
                        "INFO",
                        "saving",
                        {"deferred_builders": True}
                    )

                    # COMMENTED OUT: Automatic builder job creation
                    # builder_jobs_created = self._create_builder_discovery_jobs(collected_data)
                    # self.log(
                    #     f"Created {builder_jobs_created} builder discovery jobs",
                    #     "SUCCESS",
                    #     "saving",
                    #     {"builder_jobs": builder_jobs_created}
                    # )

                    # Update community activity status
                    if self.community:
                        self.log("Updating community activity status", "INFO", "saving")
                        self.status_manager.update_community_activity(self.community.id)
                        self.status_manager.update_availability_from_inventory(self.community.id)

                    # Auto-scrape media for single community
                    self._scrape_community_media()

                    # Update job results
                    self.update_job_status(
                        "completed",
                        items_found=1,
                        new_entities_found=0 if self.community else 1
                    )

                    self.log(
                        f"Community collection completed (builder discovery deferred until approval)",
                        "SUCCESS",
                        "completed",
                        {"builder_jobs_queued": builder_jobs_created, "deferred": True}
                    )

                except Exception as e:
                    error_msg = f"Single community processing failed: {str(e)}"
                    self.log(error_msg, "ERROR", "failed", {"error": str(e), "error_type": type(e).__name__})
                    logger.error(error_msg, exc_info=True)
                    self.update_job_status("failed", error_message=error_msg)
                    raise

        except Exception as e:
            error_msg = str(e)
            self.log(f"Collection failed: {error_msg}", "ERROR", "failed",
                    {"error": error_msg, "error_type": type(e).__name__})
            logger.error(f"Community collection failed: {error_msg}", exc_info=True)
            self.update_job_status(
                "failed",
                error_message=error_msg
            )
            raise

    def _process_existing_community(self, collected_data: Dict[str, Any]):
        """
        Process collected data for existing community.

        Detect changes and create CollectionChange records.
        Auto-applies high-quality changes for safe fields.
        """
        if "raw_response" in collected_data:
            logger.warning("Claude returned non-JSON response")
            return

        confidence = collected_data.get("confidence", {}).get("overall", 0.8)
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None

        # Calculate fees first
        community_dues, monthly_fee_formatted = calculate_fees(
            collected_data.get("hoa_fee"),
            collected_data.get("hoa_fee_frequency"),
            collected_data.get("monthly_fee")
        )

        # SAFE fields: Can be auto-applied with high confidence (>= 0.85)
        SAFE_FIELDS = {
            "phone", "email", "sales_office_address", "elementary_school",
            "middle_school", "high_school", "developer_name", "enterprise_number_hoa",
            "intro_video_url", "community_website_url", "latitude", "longitude",
            "total_acres", "tax_rate", "founded_year", "development_start_year",
            "is_master_planned", "rating", "review_count"
        }

        # RISKY fields: Always require manual review
        RISKY_FIELDS = {"name", "city", "state", "postal_code", "address"}

        # Comprehensive field mapping - covers ALL Community model fields
        field_mapping = {
            # Basic Info
            "name": "name",
            "city": "city",
            "state": "state",
            "postal_code": "postal_code",
            "address": "address",
            "phone": "phone",
            "email": "email",
            "sales_office_address": "sales_office_address",

            # Location
            "total_acres": "total_acres",
            "latitude": "latitude",
            "longitude": "longitude",

            # Finance
            "tax_rate": "tax_rate",
            "price_range_min": "price_range_min",
            "price_range_max": "price_range_max",

            # Stats
            "total_homes": "homes",
            "residents": "residents",
            "founded_year": "founded_year",
            "member_count": "member_count",

            # Schools
            "elementary_school": "elementary_school",
            "middle_school": "middle_school",
            "high_school": "high_school",

            # Development
            "development_start_year": "development_start_year",
            "is_master_planned": "is_master_planned",
            "enterprise_number_hoa": "enterprise_number_hoa",
            "developer_name": "developer_name",

            # Reviews
            "rating": "rating",
            "review_count": "review_count",

            # Media
            "intro_video_url": "intro_video_url",
            "community_website_url": "community_website_url",

            # Legacy/compatibility mappings
            "description": "about",
            "website": "community_website_url",
            "phone_number": "phone",
            "hoa_management_company": "hoa_management_company",
            "hoa_contact_phone": "hoa_contact_phone",
            "hoa_contact_email": "hoa_contact_email",
            "school_district": "school_district",
            "year_established": "founded_year",
        }

        changes_detected = 0
        auto_applied_count = 0

        for collected_field, db_field in field_mapping.items():
            if collected_field in collected_data:
                new_value = collected_data[collected_field]
                old_value = getattr(self.community, db_field, None)

                # Check if value changed
                if new_value != old_value and new_value is not None:
                    # Determine if auto-apply is appropriate
                    should_auto_apply = False
                    auto_apply_reason = None

                    # Check if field is in SAFE category
                    if db_field in SAFE_FIELDS and db_field not in RISKY_FIELDS:
                        if confidence >= 0.85:
                            if old_value is None or old_value == "":
                                # Filling empty field with high confidence
                                should_auto_apply = True
                                auto_apply_reason = "filling_empty_field"
                            elif self._is_data_quality_improvement(db_field, old_value, new_value):
                                # New value is demonstrably better
                                should_auto_apply = True
                                auto_apply_reason = "data_quality_improvement"

                    # Record the change
                    change_record = self.record_change(
                        entity_type="community",
                        entity_id=self.community.id,
                        change_type="modified",
                        field_name=db_field,
                        old_value=old_value,
                        new_value=new_value,
                        confidence=confidence,
                        source_url=source_url
                    )

                    changes_detected += 1

                    # Auto-apply if appropriate
                    if should_auto_apply and change_record:
                        try:
                            # Apply the change to the database
                            setattr(self.community, db_field, new_value)

                            # Mark as auto-applied
                            change_record.auto_applied = True
                            change_record.auto_apply_reason = auto_apply_reason
                            change_record.status = "applied"
                            change_record.applied_at = datetime.utcnow()

                            self.db.commit()
                            auto_applied_count += 1

                            logger.info(
                                f"Auto-applied change to {db_field}: {old_value} -> {new_value} "
                                f"(reason: {auto_apply_reason}, confidence: {confidence:.2f})"
                            )
                        except Exception as e:
                            logger.error(f"Failed to auto-apply change to {db_field}: {e}")
                            self.db.rollback()
                            change_record.auto_applied = False
                            change_record.status = "pending"

        # Check calculated fees
        if community_dues:
            old_community_dues = getattr(self.community, "community_dues", None)
            if community_dues != old_community_dues:
                self.record_change(
                    entity_type="community",
                    entity_id=self.community.id,
                    change_type="modified",
                    field_name="community_dues",
                    old_value=old_community_dues,
                    new_value=community_dues,
                    confidence=confidence,
                    source_url=source_url
                )

        if monthly_fee_formatted:
            old_monthly_fee = getattr(self.community, "monthly_fee", None)
            if monthly_fee_formatted != old_monthly_fee:
                self.record_change(
                    entity_type="community",
                    entity_id=self.community.id,
                    change_type="modified",
                    field_name="monthly_fee",
                    old_value=old_monthly_fee,
                    new_value=monthly_fee_formatted,
                    confidence=confidence,
                    source_url=source_url
                )

        # Check normalized development stage
        normalized_stage = None
        if "development_stage" in collected_data:
            normalized_stage = normalize_development_stage(collected_data.get("development_stage"))
            old_stage = getattr(self.community, "development_stage", None)
            if normalized_stage and normalized_stage != old_stage:
                self.record_change(
                    entity_type="community",
                    entity_id=self.community.id,
                    change_type="modified",
                    field_name="development_stage",
                    old_value=old_stage,
                    new_value=normalized_stage,
                    confidence=confidence,
                    source_url=source_url
                )

        # Recalculate and check availability_status when data that affects it changes
        current_development_stage = normalized_stage or getattr(self.community, "development_stage", None)
        current_development_status = getattr(self.community, "development_status", "active")

        # Update development_status based on development_stage
        new_development_status = current_development_status
        if current_development_stage == "Completed":
            new_development_status = "inactive"
        elif current_development_stage in ["Phase 1", "Phase 2"]:
            new_development_status = "under_development"
        elif current_development_stage in ["Phase 3", "Phase 4", "Phase 5"]:
            new_development_status = "active"

        # Calculate new availability_status
        total_homes = collected_data.get("total_homes") or getattr(self.community, "homes", None)
        new_availability_status = determine_availability_status(
            development_stage=current_development_stage,
            development_status=new_development_status,
            total_homes=total_homes,
            available_properties_count=None,
            sold_properties_count=None
        )

        # Check if availability_status changed
        old_availability_status = getattr(self.community, "availability_status", None)
        if new_availability_status != old_availability_status:
            # Generate reason for the change
            reason_parts = []
            if normalized_stage:
                reason_parts.append(f"Development stage changed to {normalized_stage}")
            if new_development_status != current_development_status:
                reason_parts.append(f"Development status changed to {new_development_status}")
            if total_homes and total_homes != getattr(self.community, "homes", None):
                reason_parts.append(f"Total homes updated to {total_homes}")

            status_change_reason = "; ".join(reason_parts) if reason_parts else f"Availability status changed from {old_availability_status} to {new_availability_status}"

            # Record the change
            self.record_change(
                entity_type="community",
                entity_id=self.community.id,
                change_type="modified",
                field_name="availability_status",
                old_value=old_availability_status,
                new_value=new_availability_status,
                confidence=confidence,
                source_url=source_url
            )

            # Update the tracking fields on the community object
            self.community.availability_status = new_availability_status
            self.community.status_changed_at = datetime.utcnow()
            self.community.status_change_reason = status_change_reason
            self.community.last_activity_at = datetime.utcnow()

            logger.info(f"Availability status changed: {old_availability_status} -> {new_availability_status}")
            logger.info(f"Reason: {status_change_reason}")

        # Handle amenities (array field)
        if "amenities" in collected_data:
            new_amenities = collected_data["amenities"]
            # Get existing amenities
            existing_amenities = [a.name for a in self.community.amenities] if self.community.amenities else []

            if set(new_amenities) != set(existing_amenities):
                self.record_change(
                    entity_type="community",
                    entity_id=self.community.id,
                    change_type="modified",
                    field_name="amenities",
                    old_value=existing_amenities,
                    new_value=new_amenities,
                    confidence=confidence,
                    source_url=source_url
                )

        # Update data_source only if other changes were detected
        # Skip redundant data_source updates when nothing else changed
        if changes_detected > 0:
            self.record_change(
                entity_type="community",
                entity_id=self.community.id,
                change_type="modified",
                field_name="data_source",
                old_value=getattr(self.community, "data_source", "manual"),
                new_value="collected",
                confidence=1.0,
                source_url=source_url
            )

        # Log summary
        if changes_detected > 0:
            logger.info(
                f"Update complete: {changes_detected} changes detected, "
                f"{auto_applied_count} auto-applied, "
                f"{changes_detected - auto_applied_count} pending review"
            )

    def _is_data_quality_improvement(self, field_name: str, old_value: Any, new_value: Any) -> bool:
        """
        Determine if new_value represents a data quality improvement over old_value.

        Returns True if new value is demonstrably better (more detailed, properly formatted, etc.).
        """
        if old_value is None or old_value == "":
            return True  # Any value is better than empty

        # Convert to strings for comparison
        old_str = str(old_value).strip()
        new_str = str(new_value).strip()

        if not new_str:
            return False  # Empty new value is never better

        # Length/detail comparison - new value significantly longer suggests more detail
        if len(new_str) > len(old_str) * 1.5:
            return True

        # Phone number formatting improvements
        if field_name in ["phone", "hoa_contact_phone"]:
            # Prefer formatted phone numbers (e.g., "(555) 123-4567" over "5551234567")
            if len(new_str) > len(old_str) and ("-" in new_str or "(" in new_str):
                return True

        # URL improvements (http -> https, more complete URLs)
        if field_name in ["intro_video_url", "community_website_url"]:
            if new_str.startswith("https://") and old_str.startswith("http://"):
                return True
            # Prefer full URLs over partial ones
            if new_str.count("/") > old_str.count("/"):
                return True

        # School names - prefer full names over acronyms
        if field_name in ["elementary_school", "middle_school", "high_school"]:
            # If new value has more words, it's likely more detailed
            if len(new_str.split()) > len(old_str.split()):
                return True

        # Email improvements - prefer complete emails
        if field_name == "email":
            if "@" in new_str and "@" not in old_str:
                return True

        return False

    def _process_new_community(self, collected_data: Dict[str, Any]):
        """
        Process collected data for new community discovery.

        Check for duplicates first, then create CollectionChange record.
        """
        self.log("Entered _process_new_community method", "INFO", "saving")

        if "raw_response" in collected_data:
            logger.warning("Claude returned non-JSON response")
            return

        self.log("Extracting metadata from collected data...", "INFO", "saving")
        confidence = collected_data.get("confidence", {}).get("overall", 0.8)
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None

        # Check for duplicate community BEFORE processing
        community_name = collected_data.get("name") or "Unknown Community"
        self.log(f"Checking for duplicate community: {community_name}", "INFO", "matching")

        from .duplicate_detection import find_duplicate_community

        duplicate_id, match_confidence, match_method = find_duplicate_community(
            db=self.db,
            name=community_name,
            city=collected_data.get("city"),
            state=collected_data.get("state"),
            website=collected_data.get("website"),
            address=collected_data.get("location")
        )

        if duplicate_id:
            self.log(
                f"Found existing community match: ID {duplicate_id} (confidence: {match_confidence:.2f}, method: {match_method})",
                "INFO",
                "matching",
                {"duplicate_id": duplicate_id, "confidence": match_confidence, "method": match_method}
            )

            # Record entity match for tracking
            self.record_entity_match(
                discovered_entity_type="community",
                discovered_name=community_name,
                discovered_data=collected_data,
                discovered_location=collected_data.get("location"),
                matched_entity_id=duplicate_id,
                match_confidence=match_confidence,
                match_method=match_method
            )

            # Skip creating new entity change - it's a duplicate
            self.log(f"Skipping duplicate community: {community_name}", "INFO", "matching")
            return

        # Generate enterprise_number_hoa
        self.log("Generating enterprise number...", "INFO", "saving")
        state = collected_data.get("state")
        year_founded = collected_data.get("year_established")
        community_name = collected_data.get("name") or "Unknown Community"

        enterprise_number = None
        if state and year_founded and community_name:
            enterprise_number = generate_enterprise_number_hoa(state, year_founded, community_name, self.db)
            logger.info(f"Generated unique enterprise_number_hoa: {enterprise_number}")
            self.log(f"Generated enterprise number: {enterprise_number}", "INFO", "saving")

        # Calculate and format fees
        self.log("Calculating fees...", "INFO", "saving")
        community_dues, monthly_fee_formatted = calculate_fees(
            collected_data.get("hoa_fee"),
            collected_data.get("hoa_fee_frequency"),
            collected_data.get("monthly_fee")
        )

        logger.info(f"Calculated fees - Community Dues: {community_dues}, Monthly Fee: {monthly_fee_formatted}")
        self.log("Fees calculated successfully", "INFO", "saving")

        # Normalize development stage
        self.log("Normalizing development stage...", "INFO", "saving")
        development_stage = normalize_development_stage(collected_data.get("development_stage"))
        logger.info(f"Normalized development stage: {collected_data.get('development_stage')} -> {development_stage}")
        self.log(f"Development stage normalized to: {development_stage}", "INFO", "saving")

        # Set development_status based on development_stage
        if development_stage == "Completed":
            development_status = "inactive"
        elif development_stage in ["Phase 1", "Phase 2"]:
            development_status = "under_development"
        elif development_stage in ["Phase 3", "Phase 4", "Phase 5"]:
            development_status = "active"
        else:
            development_status = "active"  # Default to active

        logger.info(f"Set development_status: {development_status}")

        # Determine availability_status
        total_homes = collected_data.get("total_homes")
        self.log("Determining availability status...", "INFO", "saving")
        availability_status = determine_availability_status(
            development_stage=development_stage,
            development_status=development_status,
            total_homes=total_homes,
            available_properties_count=None,  # Will be updated by inventory collector later
            sold_properties_count=None
        )

        logger.info(f"Set availability_status: {availability_status}")
        self.log(f"Availability status determined: {availability_status}", "INFO", "saving")

        # Generate status change reason for new community
        status_change_reason = f"Initial status set during discovery: {availability_status}"
        if development_stage == "Completed":
            status_change_reason = "Community marked as completed, set to sold_out"
        elif total_homes:
            status_change_reason = f"Status determined based on development stage ({development_stage})"

        # Prepare entity data for new community
        entity_data = {
            "name": collected_data.get("name"),
            "description": collected_data.get("description"),
            "location": collected_data.get("location"),
            "city": collected_data.get("city"),
            "state": state,
            "zip_code": collected_data.get("zip_code"),
            "latitude": collected_data.get("latitude"),
            "longitude": collected_data.get("longitude"),
            "website": collected_data.get("website"),
            "phone_number": collected_data.get("phone"),
            "email": collected_data.get("email"),
            "total_acres": collected_data.get("total_acres"),
            "sales_office_address": collected_data.get("sales_office_address"),
            "development_stage": development_stage,
            "development_status": development_status,
            "availability_status": availability_status,
            "status_changed_at": datetime.utcnow().isoformat(),
            "status_change_reason": status_change_reason,
            "last_activity_at": datetime.utcnow().isoformat(),
            "hoa_fee": collected_data.get("hoa_fee"),
            "hoa_fee_frequency": collected_data.get("hoa_fee_frequency"),
            "community_dues": community_dues,
            "monthly_fee": monthly_fee_formatted,
            "tax_rate": collected_data.get("tax_rate"),
            "price_range_min": collected_data.get("price_range_min"),
            "price_range_max": collected_data.get("price_range_max"),
            "school_district": collected_data.get("school_district"),
            "hoa_management_company": collected_data.get("hoa_management_company"),
            "hoa_contact_phone": collected_data.get("hoa_contact_phone"),
            "hoa_contact_email": collected_data.get("hoa_contact_email"),
            "homes": collected_data.get("total_homes"),
            "total_residents": collected_data.get("total_residents"),
            "year_established": year_founded,
            "development_start_year": collected_data.get("development_start_year") or year_founded,
            "is_master_planned": collected_data.get("is_master_planned", False),
            "developer_name": collected_data.get("developer_name"),
            "amenities": collected_data.get("amenities", []),
            "data_source": "collected",
            "data_confidence": confidence,
            "enterprise_number_hoa": enterprise_number,
            "user_id": DEFAULT_ADMIN_USER_ID
        }

        # Record as new entity
        self.log(f"Preparing to record change for new community: {entity_data.get('name')}", "INFO", "saving")
        self.record_change(
            entity_type="community",
            entity_id=None,
            change_type="added",
            is_new_entity=True,
            proposed_entity_data=entity_data,
            confidence=confidence,
            source_url=source_url
        )
        self.log("Change recorded successfully", "SUCCESS", "saving")

        # Record entity match (no match found, new entity)
        self.record_entity_match(
            discovered_entity_type="community",
            discovered_name=collected_data.get("name") or "Unknown Community",
            discovered_data=collected_data,
            discovered_location=collected_data.get("location"),
            matched_entity_id=None,
            match_confidence=None,
            match_method="no_match_found"
        )
        self.log("Entity match recorded successfully", "SUCCESS", "saving")

    def _create_builder_discovery_jobs(self, community_data: Dict[str, Any]) -> int:
        """
        Create builder discovery jobs for builders found in community data.

        This replaces the inline _discover_builders approach with a job-based approach.

        Args:
            community_data: Dictionary containing community info including builders list

        Returns:
            Number of builder jobs created
        """
        builders = community_data.get("builders", [])
        community_name = community_data.get("name", "Unknown")
        location = community_data.get("location") or community_data.get("city")

        if not builders:
            self.log(f"No builders found for {community_name}", "INFO", "saving")
            return 0

        self.log(
            f"Creating builder discovery jobs for {len(builders)} builders in {community_name}",
            "INFO",
            "saving",
            {"community_name": community_name, "builders_count": len(builders)}
        )

        jobs_created = 0
        for builder_data in builders:
            builder_name = builder_data.get("name")
            if not builder_name:
                continue

            # Create builder discovery job (will be picked up by job executor)
            builder_job = CollectionJob(
                entity_type="builder",
                entity_id=None,  # Don't try to match existing builders yet
                job_type="discovery",
                parent_entity_type="community",
                parent_entity_id=None,  # Community not created yet (pending approval)
                status="pending",
                priority=6,  # Medium-high priority
                search_query=builder_name,
                search_filters={
                    "community_name": community_name,
                    "location": location
                },
                initiated_by=self.job.initiated_by
            )

            self.db.add(builder_job)
            jobs_created += 1

        self.db.commit()

        self.log(
            f"Created {jobs_created} builder discovery jobs for {community_name}",
            "SUCCESS",
            "saving",
            {"community_name": community_name, "jobs_created": jobs_created}
        )

        return jobs_created

    def _discover_builders(self, collected_data: Dict[str, Any]) -> int:
        """
        Discover builders operating in this community.

        Create collection jobs for each discovered builder.

        Returns:
            Number of builders found
        """
        builders = collected_data.get("builders", [])

        if not builders:
            self.log("No builders found in community data", "INFO", "matching")
            logger.info("No builders found in community data")
            return 0

        self.log(f"Discovering builders in community: found {len(builders)} builders", "INFO", "matching",
                {"builders_count": len(builders)})
        logger.info(f"Found {len(builders)} builders in community")

        jobs_created = 0
        for idx, builder_data in enumerate(builders, 1):
            builder_name = builder_data.get("name")
            if not builder_name:
                continue

            self.log(f"Processing builder {idx}/{len(builders)}: {builder_name}", "INFO", "matching",
                    {"progress": f"{idx}/{len(builders)}", "builder_name": builder_name})

            # Check if builder already exists in database
            existing_builder = self.db.query(BuilderProfile).filter(
                BuilderProfile.name.ilike(f"%{builder_name}%")
            ).first()

            if existing_builder:
                self.log(f"Found existing builder match: {builder_name}", "INFO", "matching",
                        {"builder_id": existing_builder.id, "builder_name": builder_name})
            else:
                self.log(f"New builder discovered: {builder_name}", "INFO", "matching",
                        {"builder_name": builder_name})

            # Create builder collection job
            builder_job = CollectionJob(
                entity_type="builder",
                entity_id=existing_builder.id if existing_builder else None,
                job_type="update" if existing_builder else "discovery",
                parent_entity_type="community",
                parent_entity_id=self.community.id if self.community else None,
                status="pending",
                priority=5,  # High priority for builder updates
                search_query=builder_name,
                search_filters={
                    "community_id": self.community.id if self.community else None,
                    "community_name": self.community.name if self.community else collected_data.get("name"),
                    "location": f"{self.community.city}, {self.community.state}" if self.community else collected_data.get("location")
                },
                initiated_by=self.job.initiated_by
            )

            self.db.add(builder_job)
            jobs_created += 1

        self.db.commit()
        self.log(f"Created {jobs_created} builder collection jobs", "SUCCESS", "matching",
                {"jobs_created": jobs_created})
        return len(builders)

    def _scrape_community_media(self):
        """
        Automatically scrape media for communities that have intro_video_url or amenity galleries.

        This runs after community collection to download and store images
        from the URLs collected during the community scraping process.
        """
        try:
            # Determine which communities to process
            if self.community:
                # Single community mode
                communities_to_process = [self.community]
            else:
                # Area discovery mode - get all communities from current job
                # Get recently created communities (within last hour to avoid processing old ones)
                from datetime import datetime, timedelta
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)

                communities_to_process = self.db.query(Community).filter(
                    Community.created_at >= one_hour_ago
                ).all()

            if not communities_to_process:
                self.log(
                    "No communities found to scrape media for",
                    "INFO",
                    "media_scraping"
                )
                return

            self.log(
                f"Starting media scraping for {len(communities_to_process)} communities",
                "INFO",
                "media_scraping",
                {"communities_count": len(communities_to_process)}
            )

            # Initialize media scraper
            scraper = MediaScraper(db=self.db, uploaded_by="COLLECTOR")

            total_scraped = 0
            total_errors = 0

            # Process each community
            for community in communities_to_process:
                community_name = community.name or f"Community {community.id}"
                urls_to_scrape = []

                # First, check if we have latest_collected_data from this job (for update jobs)
                if hasattr(self, 'latest_collected_data') and self.latest_collected_data:
                    collected_data = self.latest_collected_data

                    # Log what fields are in collected data
                    self.log(
                        f"Collected data fields for {community_name}: {list(collected_data.keys())}",
                        "DEBUG",
                        "media_scraping"
                    )

                    # Log the images field value specifically
                    if 'images' in collected_data:
                        self.log(
                            f"Images field value for {community_name}: {collected_data['images']}",
                            "INFO",
                            "media_scraping"
                        )

                    # Look for common image field patterns
                    image_fields = [
                        'images', 'image_urls', 'photos', 'photo_urls', 'gallery',
                        'media_urls', 'cover_image', 'header_image', 'banner_image',
                        'thumbnail', 'thumbnails'
                    ]

                    for field in image_fields:
                        if field in collected_data:
                            value = collected_data[field]
                            # Handle list of URLs
                            if isinstance(value, list):
                                for url in value:
                                    if url and isinstance(url, str):
                                        urls_to_scrape.append({
                                            'url': url,
                                            'field': 'gallery',
                                            'description': f'From {field}'
                                        })
                            # Handle single URL string
                            elif isinstance(value, str) and value:
                                urls_to_scrape.append({
                                    'url': value,
                                    'field': 'cover' if 'cover' in field or 'header' in field or 'banner' in field else 'gallery',
                                    'description': f'From {field}'
                                })
                else:
                    # Fallback: check collection changes for proposed data (for new entity jobs)
                    from model.collection import CollectionChange
                    changes = self.db.query(CollectionChange).filter(
                        CollectionChange.entity_type == "community",
                        CollectionChange.entity_id == community.id,
                        CollectionChange.is_new_entity == True,
                        CollectionChange.proposed_entity_data.isnot(None)
                    ).all()

                    # Extract image URLs from proposed data
                    for change in changes:
                        if change.proposed_entity_data:
                            proposed_data = change.proposed_entity_data

                            # Debug: Log what fields are in proposed data
                            self.log(
                                f"Proposed data fields for {community_name}: {list(proposed_data.keys())}",
                                "DEBUG",
                                "media_scraping"
                            )

                            # Look for common image field patterns
                            image_fields = [
                                'images', 'image_urls', 'photos', 'photo_urls', 'gallery',
                                'media_urls', 'cover_image', 'header_image', 'banner_image',
                                'thumbnail', 'thumbnails'
                            ]

                            for field in image_fields:
                                if field in proposed_data:
                                    value = proposed_data[field]
                                    # Handle list of URLs
                                    if isinstance(value, list):
                                        for url in value:
                                            if url and isinstance(url, str):
                                                urls_to_scrape.append({
                                                    'url': url,
                                                    'field': 'gallery',
                                                    'description': f'From {field}'
                                                })
                                    # Handle single URL string
                                    elif isinstance(value, str) and value:
                                        urls_to_scrape.append({
                                            'url': value,
                                            'field': 'cover' if 'cover' in field or 'header' in field or 'banner' in field else 'gallery',
                                            'description': f'From {field}'
                                        })

                # Collect intro video URL (if it's actually an image URL)
                if community.intro_video_url:
                    # Check if it's an image URL (not a YouTube/Vimeo embed)
                    url_lower = community.intro_video_url.lower()
                    if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        urls_to_scrape.append({
                            'url': community.intro_video_url,
                            'field': 'cover',
                            'description': 'Cover image'
                        })

                # Collect amenity gallery images
                if hasattr(community, 'amenities'):
                    for amenity in community.amenities:
                        if amenity.gallery and isinstance(amenity.gallery, list):
                            for img_url in amenity.gallery:
                                if img_url:
                                    urls_to_scrape.append({
                                        'url': img_url,
                                        'field': 'gallery',
                                        'description': f'Amenity: {amenity.name}'
                                    })

                if not urls_to_scrape:
                    self.log(
                        f"No media URLs found for: {community_name}",
                        "INFO",
                        "media_scraping",
                        {"community_id": community.id, "community_name": community_name}
                    )
                    continue

                self.log(
                    f"Scraping {len(urls_to_scrape)} images for: {community_name}",
                    "INFO",
                    "media_scraping",
                    {
                        "community_id": community.id,
                        "community_name": community_name,
                        "media_count": len(urls_to_scrape)
                    }
                )

                # Download each media URL
                for idx, media_info in enumerate(urls_to_scrape, 1):
                    try:
                        url = media_info['url']
                        entity_field = media_info['field']
                        caption = media_info['description']

                        # Run async function in sync context
                        media = asyncio.run(scraper.download_from_url(
                            media_url=url,
                            entity_type="community",
                            entity_id=community.id,
                            entity_field=entity_field,
                            caption=caption
                        ))

                        if media:
                            total_scraped += 1
                            self.log(
                                f"✅ Downloaded image {idx}/{len(urls_to_scrape)} for {community_name}",
                                "SUCCESS",
                                "media_scraping",
                                {
                                    "community_id": community.id,
                                    "media_id": media.id,
                                    "media_public_id": media.public_id,
                                    "url": url,
                                    "field": entity_field
                                }
                            )
                        else:
                            self.log(
                                f"⚠️ No media returned for {url}",
                                "WARNING",
                                "media_scraping",
                                {"community_id": community.id, "url": url}
                            )

                    except Exception as e:
                        total_errors += 1
                        self.log(
                            f"❌ Failed to download image {idx}/{len(urls_to_scrape)}: {str(e)}",
                            "ERROR",
                            "media_scraping",
                            {
                                "community_id": community.id,
                                "community_name": community_name,
                                "url": media_info['url'],
                                "error": str(e)
                            }
                        )

            self.log(
                f"Media scraping completed: {total_scraped} images downloaded, {total_errors} errors",
                "SUCCESS",
                "media_scraping",
                {
                    "total_scraped": total_scraped,
                    "total_errors": total_errors,
                    "communities_processed": len(communities_to_process)
                }
            )

        except Exception as e:
            self.log(
                f"Media scraping failed: {str(e)}",
                "ERROR",
                "media_scraping",
                {"error": str(e), "error_type": type(e).__name__}
            )
            # Don't raise - media scraping is optional, shouldn't fail the entire job
            logger.error(f"Media scraping failed: {str(e)}", exc_info=True)

    def _get_builder_icon_by_size(self, builder_name: str) -> str:
        """
        Determine builder icon based on company size/prominence.

        Returns icon identifier (emoji-like string) based on builder tier:
        - 🏢 National/Large Builders (household names)
        - 🏗️ Regional Builders (multi-state presence)
        - 🏠 Local Builders (smaller, local companies)

        Args:
            builder_name: Name of the builder

        Returns:
            Icon string representing builder size
        """
        builder_lower = builder_name.lower()

        # National/Large Builders - Major household names
        national_builders = [
            "lennar", "d.r. horton", "dr horton", "pulte", "kb home",
            "toll brothers", "taylor morrison", "meritage homes",
            "century communities", "tri pointe", "beazer homes",
            "shea homes", "richmond american", "david weekley"
        ]

        # Regional Builders - Multi-state presence
        regional_builders = [
            "standard pacific", "ryland", "centex", "m/i homes",
            "ashton woods", "hovnanian", "drees homes", "montebello"
        ]

        # Check if builder is national/large
        for national in national_builders:
            if national in builder_lower:
                return "🏢"

        # Check if builder is regional
        for regional in regional_builders:
            if regional in builder_lower:
                return "🏗️"

        # Default to local builder icon
        return "🏠"

    def _populate_builder_cards(self, community_data: Dict[str, Any]):
        """
        Populate the community_builders table with basic builder information.

        This method is called AFTER a community is created but BEFORE detailed builder
        discovery jobs are created. It allows the iOS app to immediately display builder
        names while full builder profiles are collected later.

        Args:
            community_data: Dictionary containing community information including 'builders' list
        """
        try:
            # Extract builders list from community data
            builders = community_data.get("builders", [])

            if not builders:
                self.log(
                    "No builders found in community data to populate builder cards table",
                    "INFO",
                    "builder_cards"
                )
                return

            # Get the community's public ID
            community_name = community_data.get("name", "Unknown Community")

            # Query the community by name to get its public community_id
            from sqlalchemy import func
            community = self.db.query(Community).filter(
                func.lower(Community.name) == func.lower(community_name)
            ).first()

            if not community or not community.community_id:
                self.log(
                    f"Could not find community '{community_name}' in database",
                    "WARNING",
                    "builder_cards",
                    {"community_name": community_name}
                )
                return

            community_public_id = community.community_id
            community_numeric_id = community.id  # Get the internal numeric ID
            cards_created = 0
            cards_skipped = 0

            # Process each builder
            for builder_data in builders:
                if not isinstance(builder_data, dict):
                    continue

                builder_name = builder_data.get("name")
                if not builder_name:
                    continue

                # Check if this builder card already exists for this community
                existing_card = self.db.query(CommunityBuilder).filter(
                    CommunityBuilder.community_id == community_public_id,
                    func.lower(CommunityBuilder.name) == func.lower(builder_name)
                ).first()

                if existing_card:
                    cards_skipped += 1
                    self.log(
                        f"Builder card already exists: {builder_name}",
                        "DEBUG",
                        "builder_cards",
                        {
                            "community_id": community_public_id,
                            "builder_name": builder_name,
                            "card_id": existing_card.id
                        }
                    )
                    continue

                # Determine icon based on builder size/prominence
                builder_icon = self._get_builder_icon_by_size(builder_name)

                # Extract subtitle - try multiple fields
                subtitle = (
                    builder_data.get("subtitle") or
                    builder_data.get("specialties") or
                    builder_data.get("description") or
                    None
                )

                # Create new builder card
                new_card = CommunityBuilder(
                    community_id=community_public_id,
                    community_numeric_id=community_numeric_id,  # Set the internal numeric ID
                    name=builder_name,
                    subtitle=subtitle,
                    icon=builder_icon,
                    is_verified=False,  # Discovered builders start as unverified
                    followers=0
                )

                self.db.add(new_card)
                cards_created += 1

                self.log(
                    f"Created builder card: {builder_name} ({builder_icon})",
                    "SUCCESS",
                    "builder_cards",
                    {
                        "community_id": community_public_id,
                        "community_name": community_name,
                        "builder_name": builder_name,
                        "icon": builder_icon
                    }
                )

            # Commit all new cards
            if cards_created > 0:
                self.db.commit()

            self.log(
                f"Builder cards populated for {community_name}: {cards_created} created, {cards_skipped} skipped",
                "SUCCESS",
                "builder_cards",
                {
                    "community_id": community_public_id,
                    "community_name": community_name,
                    "cards_created": cards_created,
                    "cards_skipped": cards_skipped,
                    "total_builders": len(builders)
                }
            )

        except Exception as e:
            self.log(
                f"Failed to populate builder cards: {str(e)}",
                "ERROR",
                "builder_cards",
                {"error": str(e), "error_type": type(e).__name__}
            )
            # Don't raise - this is optional functionality
            logger.error(f"Failed to populate builder cards: {str(e)}", exc_info=True)
            # Rollback any partial changes
            self.db.rollback()

    def _create_builder_jobs_from_cards(self, community: Community):
        """
        Create builder collection jobs for builder cards that don't have a builder_profile_id yet.

        This is called after populating builder cards to trigger full builder profile collection.

        Args:
            community: Community object with builder cards
        """
        from model.collection import CollectionJob

        try:
            community_public_id = community.community_id
            community_name = community.name

            # Query all builder cards for this community that don't have a builder profile yet
            uncollected_cards = self.db.query(CommunityBuilder).filter(
                CommunityBuilder.community_id == community_public_id,
                CommunityBuilder.builder_profile_id.is_(None)
            ).all()

            if not uncollected_cards:
                self.log(
                    f"No builder cards need profile collection for {community_name}",
                    "INFO",
                    "builder_jobs",
                    {
                        "community_id": community_public_id,
                        "community_name": community_name
                    }
                )
                return

            jobs_created = 0
            jobs_skipped = 0

            for card in uncollected_cards:
                builder_name = card.name

                if not builder_name:
                    jobs_skipped += 1
                    continue

                # Check if a pending/running job already exists for this builder name
                existing_job = self.db.query(CollectionJob).filter(
                    CollectionJob.entity_type == "builder",
                    CollectionJob.search_query == builder_name,
                    CollectionJob.status.in_(["pending", "running"])
                ).first()

                if existing_job:
                    jobs_skipped += 1
                    self.log(
                        f"Builder job already exists: {builder_name}",
                        "DEBUG",
                        "builder_jobs",
                        {
                            "builder_name": builder_name,
                            "existing_job_id": existing_job.job_id,
                            "card_id": card.id
                        }
                    )
                    continue

                # Create new builder collection job
                new_job = CollectionJob(
                    entity_type="builder",
                    job_type="discovery",  # Discovery job to find and create builder profile
                    search_query=builder_name,  # Use builder name as search query
                    priority=5,  # Medium priority (community jobs are 10)
                    status="pending",
                    # Store card ID in search_filters so builder_collector can link back
                    search_filters={
                        "community_builder_card_id": card.id,
                        "community_id": community_public_id,
                        "community_name": community_name
                    }
                )

                self.db.add(new_job)
                jobs_created += 1

                self.log(
                    f"Created builder collection job: {builder_name}",
                    "SUCCESS",
                    "builder_jobs",
                    {
                        "builder_name": builder_name,
                        "job_id": new_job.job_id,
                        "card_id": card.id,
                        "community_id": community_public_id
                    }
                )

            # Commit all new jobs
            if jobs_created > 0:
                self.db.commit()

            self.log(
                f"Builder jobs created for {community_name}: {jobs_created} created, {jobs_skipped} skipped",
                "SUCCESS",
                "builder_jobs",
                {
                    "community_id": community_public_id,
                    "community_name": community_name,
                    "jobs_created": jobs_created,
                    "jobs_skipped": jobs_skipped,
                    "total_uncollected_cards": len(uncollected_cards)
                }
            )

        except Exception as e:
            self.log(
                f"Failed to create builder jobs: {str(e)}",
                "ERROR",
                "builder_jobs",
                {"error": str(e), "error_type": type(e).__name__}
            )
            # Don't raise - this is optional functionality
            logger.error(f"Failed to create builder jobs: {str(e)}", exc_info=True)
            # Rollback any partial changes
            self.db.rollback()
