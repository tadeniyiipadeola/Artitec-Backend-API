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
                location = None  # Can get from communities if needed
                self.log(f"Updating existing builder: {builder_name}", "INFO", "initialization",
                        {"builder_id": self.builder.id, "builder_name": builder_name})
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
            "phone": "phone",
            "email": "email",
            "headquarters_address": "headquarters_address",
            "founded_year": "founded_year",
            "employee_count": "employee_count",
            "service_areas": "service_areas",
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
        if "awards" in collected_data:
            awards_count = len(collected_data["awards"])
            self.log(f"Processing {awards_count} awards", "INFO", "matching")
            self._process_awards(collected_data["awards"], source_url)

        # Process certifications
        if "certifications" in collected_data:
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
        builder_name = collected_data.get("name", "Unknown")

        # Check for duplicate builder BEFORE processing
        self.log(f"Checking for duplicate builder: {builder_name}", "INFO", "matching")

        from .duplicate_detection import find_duplicate_builder

        duplicate_id, match_confidence, match_method = find_duplicate_builder(
            db=self.db,
            name=builder_name,
            city=collected_data.get("city"),
            state=collected_data.get("state"),
            website=collected_data.get("website"),
            phone=collected_data.get("phone"),
            email=collected_data.get("email")
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

        entity_data = {
            "name": builder_name,
            "description": collected_data.get("description"),
            "website": collected_data.get("website"),
            "phone": collected_data.get("phone"),
            "email": collected_data.get("email"),
            "headquarters_address": headquarters_address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "founded_year": collected_data.get("founded_year"),
            "employee_count": collected_data.get("employee_count"),
            "service_areas": collected_data.get("service_areas", []),
            "price_range_min": collected_data.get("price_range_min"),
            "price_range_max": collected_data.get("price_range_max"),
            "rating": collected_data.get("rating"),
            "review_count": collected_data.get("review_count"),
            "awards": collected_data.get("awards", []),
            "certifications": collected_data.get("certifications", []),
            "data_source": "collected",
            "data_confidence": confidence
        }

        # If this builder job was spawned from a community job, include the community_id
        if self.job.parent_entity_type == "community" and self.job.parent_entity_id:
            entity_data["community_id"] = self.job.parent_entity_id
            self.log(f"Linking builder to community ID: {self.job.parent_entity_id}", "INFO", "matching")

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
