"""
Builder Collector Service

Collects data about home builders.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from model.profiles.builder import BuilderProfile, BuilderAward, BuilderCredential
from model.profiles.community import Community
from model.collection import CollectionJob
from .base_collector import BaseCollector
from .prompts import generate_builder_collection_prompt
from .status_management import ImprovedBuilderStatusManager

logger = logging.getLogger(__name__)


class BuilderCollector(BaseCollector):
    """
    Collects data about home builders.

    Workflow:
    1. Search web for builder information
    2. Match discovered builder to existing record (or create new)
    3. Detect changes in builder data
    4. Update awards and certifications
    5. Create cascade jobs for sales reps and properties
    """

    def __init__(self, db: Session, job_id: str):
        super().__init__(db, job_id)
        self.builder = None
        self.status_manager = ImprovedBuilderStatusManager(db)
        if self.job.entity_id:
            self.builder = self.db.query(BuilderProfile).filter(
                BuilderProfile.id == self.job.entity_id
            ).first()

    def run(self):
        """Execute builder data collection."""
        try:
            self.update_job_status("running")
            self.log("Starting builder collection job", "INFO", "initialization")

            # Get builder name and location from job
            if self.builder:
                builder_name = self.builder.name
                # Get location from builder profile (city, state)
                city = self.builder.city if hasattr(self.builder, 'city') and self.builder.city else None
                state = self.builder.state if hasattr(self.builder, 'state') and self.builder.state else None
                location = f"{city}, {state}" if city and state else (city or state or None)
                self.log(f"Updating existing builder: {builder_name}", "INFO", "initialization",
                        {"builder_id": self.builder.id, "builder_name": builder_name, "location": location})
            else:
                builder_name = self.job.search_query
                filters = self.job.search_filters or {}
                location = filters.get("location")
                self.log(f"Discovering new builder: {builder_name}", "INFO", "initialization",
                        {"builder_name": builder_name, "location": location})

            # Call Claude to collect builder data
            self.log(f"Calling Claude API to collect data for: {builder_name}", "INFO", "searching")
            prompt = generate_builder_collection_prompt(builder_name, location)
            collected_data = self.call_claude(prompt)
            self.log("Claude API call completed successfully", "SUCCESS", "searching")

            # Process collected data
            if self.builder:
                self.log(f"Processing updates for builder: {builder_name}", "INFO", "parsing")
                self._process_existing_builder(collected_data)
            else:
                self.log(f"Processing new builder data: {builder_name}", "INFO", "parsing")
                self._process_new_builder(collected_data)

            # Create cascade jobs for sales reps and properties
            self.log("Creating cascade jobs for sales reps and properties", "INFO", "saving")
            self._create_cascade_jobs(collected_data)

            # Update builder activity status
            if self.builder:
                self.log("Updating builder activity status", "INFO", "saving")
                self.status_manager.update_builder_activity(self.builder.id)

            # Update job results
            self.update_job_status(
                "completed",
                items_found=1,
                new_entities_found=0 if self.builder else 1
            )

            self.log("Builder collection completed successfully", "SUCCESS", "completed",
                    {"builder_name": builder_name, "changes_detected": self.job.changes_detected})

        except Exception as e:
            error_msg = str(e)
            self.log(f"Builder collection failed: {error_msg}", "ERROR", "failed",
                    {"error": error_msg, "error_type": type(e).__name__})
            logger.error(f"Builder collection failed: {error_msg}", exc_info=True)
            self.update_job_status(
                "failed",
                error_message=error_msg
            )
            raise

    def _process_existing_builder(self, collected_data: Dict[str, Any]):
        """Process collected data for existing builder."""
        if "raw_response" in collected_data:
            self.log("Claude returned non-JSON response", "WARNING", "parsing")
            logger.warning("Claude returned non-JSON response")
            return

        confidence = collected_data.get("confidence", {}).get("overall", 0.8)
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None

        # Map of fields to check
        field_mapping = {
            "description": "description",
            "website": "website",
            "title": "title",  # Office type
            "phone": "phone",
            "email": "email",
            "headquarters_address": "headquarters_address",
            "sales_office_address": "sales_office_address",
            "founded_year": "founded_year",
            "employee_count": "employee_count",
            "service_areas": "service_areas",
            "specialties": "specialties",
            "price_range_min": "price_range_min",
            "price_range_max": "price_range_max",
            "rating": "rating",
            "review_count": "review_count"
        }

        changes_found = 0
        for collected_field, db_field in field_mapping.items():
            if collected_field in collected_data:
                new_value = collected_data[collected_field]
                old_value = getattr(self.builder, db_field, None)

                if new_value != old_value and new_value is not None:
                    self.record_change(
                        entity_type="builder",
                        entity_id=self.builder.id,
                        change_type="modified",
                        field_name=db_field,
                        old_value=old_value,
                        new_value=new_value,
                        confidence=confidence,
                        source_url=source_url
                    )
                    changes_found += 1

        if changes_found > 0:
            self.log(f"Detected {changes_found} field changes", "INFO", "matching",
                    {"changes_count": changes_found})

        # Process awards
        if "awards" in collected_data and collected_data["awards"] is not None:
            awards_count = len(collected_data["awards"])
            self.log(f"Processing {awards_count} awards", "INFO", "matching")
            self._process_awards(collected_data["awards"], source_url)

        # Process certifications
        if "certifications" in collected_data and collected_data["certifications"] is not None:
            certs_count = len(collected_data["certifications"])
            self.log(f"Processing {certs_count} certifications", "INFO", "matching")
            self._process_certifications(collected_data["certifications"], source_url)

        # Update tracking fields
        self.record_change(
            entity_type="builder",
            entity_id=self.builder.id,
            change_type="modified",
            field_name="data_source",
            old_value=getattr(self.builder, "data_source", "manual"),
            new_value="collected",
            confidence=1.0,
            source_url=source_url
        )

        self.record_change(
            entity_type="builder",
            entity_id=self.builder.id,
            change_type="modified",
            field_name="data_confidence",
            old_value=getattr(self.builder, "data_confidence", 1.0),
            new_value=confidence,
            confidence=1.0,
            source_url=source_url
        )

    def _process_new_builder(self, collected_data: Dict[str, Any]):
        """Process collected data for new builder discovery."""
        if "raw_response" in collected_data:
            self.log("Claude returned non-JSON response", "WARNING", "parsing")
            logger.warning("Claude returned non-JSON response")
            return

        confidence = collected_data.get("confidence", {}).get("overall", 0.8)
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None
        builder_name = collected_data.get("name") or "Unknown Builder"

        # Check for duplicate builder BEFORE processing
        self.log(f"Checking for duplicate builder: {builder_name}", "INFO", "matching")

        from .duplicate_detection import find_duplicate_builder

        # Get community_id from collected data or job context for location-aware matching
        community_id_for_matching = None
        primary_community = collected_data.get("primary_community", {})
        if isinstance(primary_community, dict):
            community_name = primary_community.get("name")
            community_city = primary_community.get("city")
            community_state = primary_community.get("state")

            # Try to find existing community ID
            if community_name and (community_city or community_state):
                from model.profiles.community import Community
                query = self.db.query(Community).filter(Community.name.ilike(f"%{community_name}%"))
                if community_city:
                    query = query.filter(Community.city.ilike(f"%{community_city}%"))
                if community_state:
                    query = query.filter(Community.state == community_state.upper())
                community = query.first()
                if community:
                    community_id_for_matching = community.id
                    self.log(f"Using community ID {community_id_for_matching} for location-aware builder matching", "INFO", "matching")

        duplicate_id, match_confidence, match_method = find_duplicate_builder(
            db=self.db,
            name=builder_name,
            city=collected_data.get("city"),
            state=collected_data.get("state"),
            website=collected_data.get("website"),
            phone=collected_data.get("phone"),
            email=collected_data.get("email"),
            community_id=community_id_for_matching
        )

        if duplicate_id:
            self.log(
                f"Found existing builder match: ID {duplicate_id} (confidence: {match_confidence:.2f}, method: {match_method})",
                "INFO",
                "matching",
                {"duplicate_id": duplicate_id, "confidence": match_confidence, "method": match_method}
            )

            # Record entity match for tracking
            self.record_entity_match(
                discovered_entity_type="builder",
                discovered_name=builder_name,
                discovered_data=collected_data,
                discovered_location=f"{collected_data.get('city', '')}, {collected_data.get('state', '')}".strip(', '),
                matched_entity_id=duplicate_id,
                match_confidence=match_confidence,
                match_method=match_method
            )

            # Skip creating new entity change - it's a duplicate
            self.log(f"Skipping duplicate builder: {builder_name}", "INFO", "matching")
            return

        # Extract city and state from headquarters_address if available
        headquarters_address = collected_data.get("headquarters_address")
        city = collected_data.get("city")
        state = collected_data.get("state")
        zip_code = collected_data.get("zip_code")

        # Parse address to extract city/state if not provided
        if headquarters_address and (not city or not state):
            import re
            # Try to parse city, state from address (e.g., "123 Main St, Houston, TX 77001")
            match = re.search(r',\s*([A-Za-z\s]+),?\s*([A-Z]{2})\s*(\d{5})?', headquarters_address)
            if match:
                if not city:
                    city = match.group(1).strip()
                if not state:
                    state = match.group(2).strip()
                if not zip_code and match.group(3):
                    zip_code = match.group(3).strip()

        # ===== EXTRACT PRIMARY COMMUNITY DATA =====
        # Extract community name/city/state from collected data for orphaned builder handling
        community_name = None
        community_city = None
        community_state = None

        primary_community = collected_data.get("primary_community", {})
        if isinstance(primary_community, dict):
            community_name = primary_community.get("name")
            community_city = primary_community.get("city")
            community_state = primary_community.get("state")

        entity_data = {
            "name": builder_name,
            "description": collected_data.get("description"),
            "website": collected_data.get("website"),
            "title": collected_data.get("title"),  # Office type (Sales Office, etc.)
            "phone": collected_data.get("phone"),
            "email": collected_data.get("email"),
            "headquarters_address": headquarters_address,
            "sales_office_address": collected_data.get("sales_office_address"),
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "founded_year": collected_data.get("founded_year"),
            "employee_count": collected_data.get("employee_count"),
            "service_areas": collected_data.get("service_areas", []),
            "specialties": collected_data.get("specialties", []),
            "price_range_min": collected_data.get("price_range_min"),
            "price_range_max": collected_data.get("price_range_max"),
            "rating": collected_data.get("rating"),
            "review_count": collected_data.get("review_count"),
            "awards": collected_data.get("awards", []),
            "certifications": collected_data.get("certifications", []),
            "data_source": "collected",
            "data_confidence": confidence,
            # Store community data for orphaned builder handling
            "community_name": community_name,
            "community_city": community_city,
            "community_state": community_state
        }

        # ===== ENHANCED COMMUNITY LOOKUP WITH LOCATION =====
        # PRIORITY 1: Use community_id from search_filters (for backfill jobs)
        filters = self.job.search_filters or {}
        community_id = filters.get('community_id')

        if community_id:
            self.log(
                f"Using pre-assigned community ID from job filters: {community_id}",
                "INFO",
                "matching"
            )

        # PRIORITY 2: Look up community from Claude's response (for discovery jobs)
        # Only run this lookup if community_id was not already provided
        if not community_id:
            primary_community = collected_data.get("primary_community", {})

            # Handle case where primary_community might be a string instead of dict
            if isinstance(primary_community, str):
                # Escape curly braces to prevent f-string formatting errors
                safe_preview = str(primary_community[:50]).replace('{', '{{').replace('}', '}}')
                self.log(f"Warning: primary_community returned as string, attempting to parse: {safe_preview}...", "WARNING", "parsing")
                try:
                    import json
                    primary_community = json.loads(primary_community)
                except Exception as e:
                    self.log(f"Could not parse primary_community string: {str(e)}", "WARNING", "parsing")
                    primary_community = {}

            if primary_community and isinstance(primary_community, dict):
                community_name = primary_community.get("name")
                community_city = primary_community.get("city")
                community_state = primary_community.get("state")

                if community_name:
                    # Safely format log message (community_name might contain curly braces if it's malformed JSON)
                    safe_community_name = str(community_name).replace('{', '{{').replace('}', '}}') if community_name else 'None'
                    safe_community_city = str(community_city).replace('{', '{{').replace('}', '}}') if community_city else 'None'
                    safe_community_state = str(community_state).replace('{', '{{').replace('}', '}}') if community_state else 'None'
                    self.log(
                        f"Looking up community: {safe_community_name} in {safe_community_city}, {safe_community_state}",
                        "INFO",
                        "matching"
                    )

                    # Build query with location filters
                    from model.profiles.community import Community
                    from model.collection import CollectionChange

                    query = self.db.query(Community).filter(Community.name.ilike(f"%{community_name}%"))

                    # Add location filters if available
                    if community_city:
                        query = query.filter(Community.city.ilike(f"%{community_city}%"))
                    if community_state:
                        query = query.filter(Community.state == community_state.upper())

                    community = query.first()

                    if community:
                        # Found approved community with location match
                        community_id = community.community_id  # Use the CMY-XXX string ID, not the database integer ID
                        self.log(
                            f"Found approved community: {community.name} (ID: {community.community_id}) in {community.city}, {community.state}",
                            "INFO",
                            "matching",
                            {
                                "community_id": community.community_id,
                                "community_name": community.name,
                                "location": f"{community.city}, {community.state}"
                            }
                        )
                    else:
                        # Check for pending community change with location
                        self.log("No approved community found, checking pending changes", "INFO", "matching")

                        # Query pending community changes with location matching
                        from sqlalchemy import and_, or_, cast, String

                        change_query = self.db.query(CollectionChange).filter(
                            CollectionChange.entity_type == "community",
                            CollectionChange.status.in_(["pending", "approved"]),
                            cast(CollectionChange.proposed_entity_data["name"], String).ilike(f"%{community_name}%")
                        )

                        # Add location filters to pending changes
                        if community_city:
                            change_query = change_query.filter(
                                cast(CollectionChange.proposed_entity_data["city"], String).ilike(f"%{community_city}%")
                            )
                        if community_state:
                            change_query = change_query.filter(
                                cast(CollectionChange.proposed_entity_data["state"], String) == community_state.upper()
                            )

                        community_change = change_query.first()

                        if community_change and community_change.entity_id:
                            # Found pending community with location match
                            community_id = community_change.entity_id
                            change_data = community_change.proposed_entity_data or {}
                            self.log(
                                f"Found pending community change: {change_data.get('name')} (ID: {community_change.entity_id}) in {change_data.get('city')}, {change_data.get('state')}",
                                "INFO",
                                "matching",
                                {
                                    "change_id": community_change.id,
                                    "entity_id": community_change.entity_id,
                                    "community_name": change_data.get("name"),
                                    "location": f"{change_data.get('city')}, {change_data.get('state')}"
                                }
                            )
                        else:
                            self.log(
                                f"No community found for {community_name} in {community_city}, {community_state}",
                                "WARNING",
                                "matching"
                            )

                            # ===== AUTO-COLLECT AND CREATE COMMUNITY =====
                            # Always create community to prevent orphaned builders
                            # Confidence rating only affects auto-approval (>= 75%)
                            if False:  # DISABLED: Never auto-create communities during builder collection
                                self.log(
                                    f"Auto-collecting community data for {community_name} (builder confidence: {confidence:.2%} >= 75%)",
                                    "INFO",
                                    "auto_creation"
                                )

                                try:
                                    # Import community collection prompt
                                    from .prompts import generate_community_collection_prompt
                                    from model.profiles.community import Community
                                    import time
                                    import uuid

                                    # Build location string for Claude
                                    location = f"{community_city}, {community_state}" if community_city and community_state else None

                                    # Generate community collection prompt
                                    self.log(
                                        f"Calling Claude to collect full community data for {community_name} in {location}",
                                        "INFO",
                                        "auto_creation"
                                    )

                                    community_prompt = generate_community_collection_prompt(community_name, location)
                                    community_data = self.call_claude(community_prompt, max_tokens=8000)

                                    # Check if Claude returned valid data
                                    if "raw_response" in community_data:
                                        self.log(
                                            f"Claude returned non-JSON response for community {community_name}",
                                            "WARNING",
                                            "auto_creation"
                                        )
                                        # Fall back to minimal community creation
                                        raise ValueError("Claude returned non-JSON response")

                                    # Extract community data (might be in 'communities' array or direct)
                                    if "communities" in community_data and isinstance(community_data["communities"], list) and len(community_data["communities"]) > 0:
                                        # Area discovery mode - take first community
                                        comm_info = community_data["communities"][0]
                                    else:
                                        # Single community mode
                                        comm_info = community_data

                                    # Generate unique community ID
                                    timestamp = int(time.time())
                                    random_suffix = uuid.uuid4().hex[:6].upper()
                                    community_id_str = f"CMY-{timestamp}-{random_suffix}"

                                    # Create community with full collected data
                                    new_community = Community(
                                        community_id=community_id_str,
                                        name=comm_info.get("name", community_name),
                                        description=comm_info.get("description"),
                                        city=comm_info.get("city", community_city),
                                        state=comm_info.get("state", community_state).upper() if comm_info.get("state") or community_state else None,
                                        postal_code=comm_info.get("postal_code") or comm_info.get("zip_code"),
                                        address=comm_info.get("address"),
                                        latitude=comm_info.get("latitude"),
                                        longitude=comm_info.get("longitude"),
                                        year_built=comm_info.get("year_built"),
                                        total_homes=comm_info.get("total_homes"),
                                        available_properties_count=comm_info.get("available_properties_count"),
                                        sold_properties_count=comm_info.get("sold_properties_count"),
                                        community_dues=comm_info.get("community_dues"),
                                        monthly_fee=comm_info.get("monthly_fee"),
                                        amenities=comm_info.get("amenities", []),
                                        schools=comm_info.get("schools", []),
                                        website=comm_info.get("website"),
                                        phone=comm_info.get("phone"),
                                        email=comm_info.get("email"),
                                        rating=comm_info.get("rating"),
                                        review_count=comm_info.get("review_count"),
                                        development_status=comm_info.get("development_status", "active"),
                                        development_stage=comm_info.get("development_stage"),
                                        availability_status=comm_info.get("availability_status", "available"),
                                        user_id=None,  # No owner yet
                                        is_active=True,
                                        data_source="collected",
                                        data_confidence=comm_info.get("confidence", {}).get("overall", 0.8)
                                    )

                                    self.db.add(new_community)
                                    self.db.flush()

                                    community_id = new_community.id

                                    self.log(
                                        f"Auto-created community with full data: {new_community.name} (ID: {new_community.id}, {community_id_str}) in {new_community.city}, {new_community.state}",
                                        "SUCCESS",
                                        "auto_creation",
                                        {
                                            "community_id": new_community.id,
                                            "community_id_str": community_id_str,
                                            "community_name": new_community.name,
                                            "location": f"{new_community.city}, {new_community.state}",
                                            "trigger": "builder_collection",
                                            "builder_confidence": confidence,
                                            "community_confidence": new_community.data_confidence,
                                            "data_fields_collected": len([k for k, v in comm_info.items() if v is not None])
                                        }
                                    )

                                except Exception as e:
                                    self.log(
                                        f"Failed to auto-collect community {community_name}: {str(e)}. Creating minimal record.",
                                        "WARNING",
                                        "auto_creation"
                                    )
                                    logger.warning(f"Failed to auto-collect community, falling back to minimal: {e}")

                                    try:
                                        # Fallback: Create minimal community record
                                        import time
                                        import uuid
                                        timestamp = int(time.time())
                                        random_suffix = uuid.uuid4().hex[:6].upper()
                                        community_id_str = f"CMY-{timestamp}-{random_suffix}"

                                        from model.profiles.community import Community
                                        new_community = Community(
                                            community_id=community_id_str,
                                            name=community_name,
                                            city=community_city,
                                            state=community_state.upper() if community_state else None,
                                            user_id=None,
                                            is_active=True,
                                            development_status='active',
                                            availability_status='available'
                                        )
                                        self.db.add(new_community)
                                        self.db.flush()
                                        community_id = new_community.id

                                        self.log(
                                            f"Created minimal community record: {community_name} (ID: {new_community.id})",
                                            "INFO",
                                            "auto_creation"
                                        )
                                    except Exception as e2:
                                        self.log(
                                            f"Failed to create even minimal community: {str(e2)}",
                                            "ERROR",
                                            "auto_creation"
                                        )
                                        logger.error(f"Failed to create minimal community: {e2}")
                                        community_id = None
                            else:
                                self.log(
                                    f"Builder confidence {confidence:.2%} < 75%, skipping auto-community-creation for {community_name}",
                                    "INFO",
                                    "auto_creation"
                                )

        # ===== FALLBACK TO JOB METADATA =====
        # If community lookup failed, try using job.parent_entity_id as before
        if not community_id and self.job.parent_entity_type == "community" and self.job.parent_entity_id:
            community_id = self.job.parent_entity_id
            self.log(
                f"Using community ID from job metadata: {community_id}",
                "INFO",
                "matching"
            )

        # Add community_id if found and update community_name to match actual community
        if community_id:
            entity_data["community_id"] = community_id

            # Get the actual community name from the database to ensure consistency
            from model.profiles.community import Community
            if isinstance(community_id, int):
                actual_community = self.db.query(Community).filter(Community.id == community_id).first()
            else:
                actual_community = self.db.query(Community).filter(Community.community_id == community_id).first()

            if actual_community:
                # Override the community_name from Claude with the actual community name from DB
                entity_data["community_name"] = actual_community.name
                self.log(f"Linking builder to community: {actual_community.name} (ID: {community_id})", "INFO", "matching")
            else:
                self.log(f"Linking builder to community ID: {community_id}", "INFO", "matching")

        self.log(f"Recording new builder entity: {builder_name}", "INFO", "matching",
                {"builder_name": builder_name, "confidence": confidence})

        self.record_change(
            entity_type="builder",
            entity_id=None,
            change_type="added",
            is_new_entity=True,
            proposed_entity_data=entity_data,
            confidence=confidence,
            source_url=source_url
        )

        self.record_entity_match(
            discovered_entity_type="builder",
            discovered_name=builder_name,
            discovered_data=collected_data,
            matched_entity_id=None,
            match_confidence=None,
            match_method="no_match_found"
        )

    def _process_awards(self, awards: list, source_url: Optional[str]):
        """Process builder awards."""
        if not self.builder:
            return

        existing_awards = {
            (a.title, a.year): a
            for a in self.builder.awards
        } if self.builder.awards else {}

        for award_data in awards:
            title = award_data.get("title")
            year = award_data.get("year")
            awarded_by = award_data.get("awarded_by")

            if not title:
                continue

            # Check if award already exists
            if (title, year) not in existing_awards:
                # Record as new award
                entity_data = {
                    "builder_id": self.builder.id,
                    "title": title,
                    "awarded_by": awarded_by,
                    "year": year
                }

                self.record_change(
                    entity_type="award",
                    entity_id=None,
                    change_type="added",
                    is_new_entity=True,
                    proposed_entity_data=entity_data,
                    confidence=0.8,
                    source_url=source_url
                )

    def _process_certifications(self, certifications: list, source_url: Optional[str]):
        """Process builder certifications."""
        if not self.builder:
            return

        existing_certs = {
            c.credential_name: c
            for c in self.builder.credentials
        } if self.builder.credentials else {}

        for cert_name in certifications:
            if cert_name not in existing_certs:
                # Record as new certification
                entity_data = {
                    "builder_id": self.builder.id,
                    "credential_name": cert_name,
                    "credential_type": "certification"
                }

                self.record_change(
                    entity_type="credential",
                    entity_id=None,
                    change_type="added",
                    is_new_entity=True,
                    proposed_entity_data=entity_data,
                    confidence=0.8,
                    source_url=source_url
                )

    def _create_cascade_jobs(self, collected_data: Dict[str, Any]):
        """Create cascade jobs for sales reps and properties."""
        if not self.builder and self.job.job_type != "update":
            self.log("Skipping cascade jobs (new builder not yet approved)", "INFO", "saving")
            logger.info("Skipping cascade jobs for new builder (not yet approved)")
            return

        filters = self.job.search_filters or {}
        community_id = filters.get("community_id")
        community_name = filters.get("community_name")
        location = filters.get("location")

        jobs_created = []

        # Create sales rep collection job
        self.log("Creating sales rep discovery job", "INFO", "saving")
        sales_rep_job = CollectionJob(
            entity_type="sales_rep",
            entity_id=None,
            job_type="discovery",
            parent_entity_type="builder",
            parent_entity_id=self.builder.id if self.builder else None,
            status="pending",
            priority=5,
            search_query=self.builder.name if self.builder else self.job.search_query,
            search_filters={
                "builder_id": self.builder.id if self.builder else None,
                "builder_name": self.builder.name if self.builder else self.job.search_query,
                "community_id": community_id,
                "community_name": community_name,
                "location": location
            },
            initiated_by=self.job.initiated_by
        )
        self.db.add(sales_rep_job)
        jobs_created.append("sales_rep")

        # Create property collection job if we have community context
        if community_id or community_name:
            self.log("Creating property inventory job", "INFO", "saving")
            property_job = CollectionJob(
                entity_type="property",
                entity_id=None,
                job_type="inventory",
                parent_entity_type="builder",
                parent_entity_id=self.builder.id if self.builder else None,
                status="pending",
                priority=3,
                search_query=f"{self.builder.name if self.builder else self.job.search_query} properties",
                search_filters={
                    "builder_id": self.builder.id if self.builder else None,
                    "builder_name": self.builder.name if self.builder else self.job.search_query,
                    "community_id": community_id,
                    "community_name": community_name,
                    "location": location
                },
                initiated_by=self.job.initiated_by
            )
            self.db.add(property_job)
            jobs_created.append("property")

        self.db.commit()
        self.log(f"Created {len(jobs_created)} cascade jobs: {', '.join(jobs_created)}", "SUCCESS", "saving",
                {"jobs_created": jobs_created})
        logger.info("Created cascade jobs for sales reps and properties")
