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
            logger.info(f"Starting builder collection job {self.job_id}")

            # Get builder name and location from job
            if self.builder:
                builder_name = self.builder.name
                location = None  # Can get from communities if needed
            else:
                builder_name = self.job.search_query
                filters = self.job.search_filters or {}
                location = filters.get("location")

            # Call Claude to collect builder data
            logger.info(f"Collecting data for builder: {builder_name}")
            prompt = generate_builder_collection_prompt(builder_name, location)
            collected_data = self.call_claude(prompt)

            # Process collected data
            if self.builder:
                self._process_existing_builder(collected_data)
            else:
                self._process_new_builder(collected_data)

            # Create cascade jobs for sales reps and properties
            self._create_cascade_jobs(collected_data)

            # Update builder activity status
            if self.builder:
                self.status_manager.update_builder_activity(self.builder.id)

            # Update job results
            self.update_job_status(
                "completed",
                items_found=1,
                new_entities_found=0 if self.builder else 1
            )

            logger.info("Builder collection completed")

        except Exception as e:
            logger.error(f"Builder collection failed: {str(e)}", exc_info=True)
            self.update_job_status(
                "failed",
                error_message=str(e)
            )
            raise

    def _process_existing_builder(self, collected_data: Dict[str, Any]):
        """Process collected data for existing builder."""
        if "raw_response" in collected_data:
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

        # Process awards
        if "awards" in collected_data:
            self._process_awards(collected_data["awards"], source_url)

        # Process certifications
        if "certifications" in collected_data:
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
            logger.warning("Claude returned non-JSON response")
            return

        confidence = collected_data.get("confidence", {}).get("overall", 0.8)
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None

        entity_data = {
            "name": collected_data.get("name"),
            "description": collected_data.get("description"),
            "website": collected_data.get("website"),
            "phone": collected_data.get("phone"),
            "email": collected_data.get("email"),
            "headquarters_address": collected_data.get("headquarters_address"),
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
            discovered_name=collected_data.get("name", "Unknown"),
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
            logger.info("Skipping cascade jobs for new builder (not yet approved)")
            return

        filters = self.job.search_filters or {}
        community_id = filters.get("community_id")
        community_name = filters.get("community_name")
        location = filters.get("location")

        # Create sales rep collection job
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

        # Create property collection job if we have community context
        if community_id or community_name:
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

        self.db.commit()
        logger.info("Created cascade jobs for sales reps and properties")
