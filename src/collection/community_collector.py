"""
Community Collector Service

Collects data about residential communities.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from model.profiles.community import Community
from model.profiles.builder import BuilderProfile
from model.collection import CollectionJob
from .base_collector import BaseCollector
from .prompts import generate_community_collection_prompt
from .status_management import ImprovedCommunityStatusManager

logger = logging.getLogger(__name__)


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
            logger.info(f"Starting community collection job {self.job_id}")

            # Get community name and location from job
            if self.community:
                community_name = self.community.name
                location = f"{self.community.city}, {self.community.state}"
            else:
                # For discovery jobs, get from search_query
                community_name = self.job.search_query
                # Extract location from search_filters
                filters = self.job.search_filters or {}
                location = filters.get("location", "")

            # Call Claude to collect community data
            logger.info(f"Collecting data for community: {community_name} in {location}")
            prompt = generate_community_collection_prompt(community_name, location)
            collected_data = self.call_claude(prompt)

            # Process collected data
            if self.community:
                # Update existing community
                self._process_existing_community(collected_data)
            else:
                # Create new community
                self._process_new_community(collected_data)

            # Discover and create jobs for builders in this community
            builders_found = self._discover_builders(collected_data)

            # Update community activity status
            if self.community:
                self.status_manager.update_community_activity(self.community.id)
                self.status_manager.update_availability_from_inventory(self.community.id)

            # Update job results
            self.update_job_status(
                "completed",
                items_found=1,
                new_entities_found=0 if self.community else 1
            )

            logger.info(
                f"Community collection completed. "
                f"Found {builders_found} builders in community."
            )

        except Exception as e:
            logger.error(f"Community collection failed: {str(e)}", exc_info=True)
            self.update_job_status(
                "failed",
                error_message=str(e)
            )
            raise

    def _process_existing_community(self, collected_data: Dict[str, Any]):
        """
        Process collected data for existing community.

        Detect changes and create CollectionChange records.
        """
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
            "phone": "phone_number",
            "email": "email",
            "hoa_fee": "hoa_fee",
            "school_district": "school_district",
            "hoa_management_company": "hoa_management_company",
            "hoa_contact_phone": "hoa_contact_phone",
            "hoa_contact_email": "hoa_contact_email",
            "total_homes": "homes",
            "year_established": "year_established"
        }

        for collected_field, db_field in field_mapping.items():
            if collected_field in collected_data:
                new_value = collected_data[collected_field]
                old_value = getattr(self.community, db_field, None)

                # Check if value changed
                if new_value != old_value and new_value is not None:
                    self.record_change(
                        entity_type="community",
                        entity_id=self.community.id,
                        change_type="modified",
                        field_name=db_field,
                        old_value=old_value,
                        new_value=new_value,
                        confidence=confidence,
                        source_url=source_url
                    )

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

        # Update data_source and last_data_sync
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

    def _process_new_community(self, collected_data: Dict[str, Any]):
        """
        Process collected data for new community discovery.

        Create CollectionChange record for new entity creation.
        """
        if "raw_response" in collected_data:
            logger.warning("Claude returned non-JSON response")
            return

        confidence = collected_data.get("confidence", {}).get("overall", 0.8)
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None

        # Prepare entity data for new community
        entity_data = {
            "name": collected_data.get("name"),
            "description": collected_data.get("description"),
            "location": collected_data.get("location"),
            "city": collected_data.get("city"),
            "state": collected_data.get("state"),
            "zip_code": collected_data.get("zip_code"),
            "website": collected_data.get("website"),
            "phone_number": collected_data.get("phone"),
            "email": collected_data.get("email"),
            "hoa_fee": collected_data.get("hoa_fee"),
            "school_district": collected_data.get("school_district"),
            "hoa_management_company": collected_data.get("hoa_management_company"),
            "hoa_contact_phone": collected_data.get("hoa_contact_phone"),
            "hoa_contact_email": collected_data.get("hoa_contact_email"),
            "homes": collected_data.get("total_homes"),
            "year_established": collected_data.get("year_established"),
            "developer_name": collected_data.get("developer_name"),
            "amenities": collected_data.get("amenities", []),
            "data_source": "collected",
            "data_confidence": confidence
        }

        # Record as new entity
        self.record_change(
            entity_type="community",
            entity_id=None,
            change_type="added",
            is_new_entity=True,
            proposed_entity_data=entity_data,
            confidence=confidence,
            source_url=source_url
        )

        # Record entity match (no match found, new entity)
        self.record_entity_match(
            discovered_entity_type="community",
            discovered_name=collected_data.get("name", "Unknown"),
            discovered_data=collected_data,
            discovered_location=collected_data.get("location"),
            matched_entity_id=None,
            match_confidence=None,
            match_method="no_match_found"
        )

    def _discover_builders(self, collected_data: Dict[str, Any]) -> int:
        """
        Discover builders operating in this community.

        Create collection jobs for each discovered builder.

        Returns:
            Number of builders found
        """
        builders = collected_data.get("builders", [])

        if not builders:
            logger.info("No builders found in community data")
            return 0

        logger.info(f"Found {len(builders)} builders in community")

        for builder_data in builders:
            builder_name = builder_data.get("name")
            if not builder_name:
                continue

            # Check if builder already exists in database
            existing_builder = self.db.query(BuilderProfile).filter(
                BuilderProfile.name.ilike(f"%{builder_name}%")
            ).first()

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

        self.db.commit()
        return len(builders)
