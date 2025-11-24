"""
Sales Rep Manager Service

Manages sales representative data collection and status tracking.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from model.profiles.sales_rep import SalesRep
from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from model.collection import CollectionJob
from .base_collector import BaseCollector
from .prompts import generate_sales_rep_collection_prompt

logger = logging.getLogger(__name__)

# Grace period before marking rep as inactive (60 days)
INACTIVATION_GRACE_PERIOD_DAYS = 60


class SalesRepManager(BaseCollector):
    """
    Manages sales representative data.

    Features:
    - Discovers new sales reps
    - Updates existing rep contact info
    - Tracks rep activity status (is_active)
    - Implements 60-day grace period before inactivation
    - Validates builder-community relationships
    """

    def __init__(self, db: Session, job_id: str):
        super().__init__(db, job_id)
        self.builder = None
        self.community = None
        self._load_context()

    def _load_context(self):
        """Load builder and community context from job."""
        filters = self.job.search_filters or {}

        # Load builder
        builder_id = filters.get("builder_id")
        if builder_id:
            self.builder = self.db.query(BuilderProfile).filter(
                BuilderProfile.id == builder_id
            ).first()

        # Load community
        community_id = filters.get("community_id")
        if community_id:
            self.community = self.db.query(Community).filter(
                Community.id == community_id
            ).first()

    def run(self):
        """Execute sales rep data collection."""
        try:
            self.update_job_status("running")
            logger.info(f"Starting sales rep collection job {self.job_id}")

            if not self.builder:
                raise ValueError("Builder context required for sales rep collection")

            # Build context for Claude prompt
            builder_name = self.builder.name
            community_name = self.community.name if self.community else None
            filters = self.job.search_filters or {}
            location = filters.get("location")

            # Call Claude to collect sales rep data
            logger.info(
                f"Collecting sales reps for {builder_name}"
                + (f" at {community_name}" if community_name else "")
            )
            prompt = generate_sales_rep_collection_prompt(
                builder_name,
                community_name,
                location
            )
            collected_data = self.call_claude(prompt)

            # Process collected sales reps
            sales_reps = collected_data.get("sales_reps", [])
            new_reps = self._process_sales_reps(sales_reps, collected_data)

            # Mark missing reps as inactive (with grace period)
            inactive_count = self._check_inactive_reps(sales_reps)

            # Update job results
            self.update_job_status(
                "completed",
                items_found=len(sales_reps),
                new_entities_found=new_reps
            )

            logger.info(
                f"Sales rep collection completed. "
                f"Found {len(sales_reps)} reps, {new_reps} new, {inactive_count} inactive"
            )

        except Exception as e:
            logger.error(f"Sales rep collection failed: {str(e)}", exc_info=True)
            self.update_job_status(
                "failed",
                error_message=str(e)
            )
            raise

    def _process_sales_reps(
        self,
        sales_reps: List[Dict[str, Any]],
        collected_data: Dict[str, Any]
    ) -> int:
        """
        Process collected sales rep data.

        Returns:
            Number of new reps discovered
        """
        new_rep_count = 0
        sources = collected_data.get("sources", [])
        source_url = sources[0] if sources else None

        for rep_data in sales_reps:
            rep_name = rep_data.get("name")
            if not rep_name:
                continue

            # Validate builder-community relationship exists if community is specified
            if self.community:
                if not self._validate_builder_community_relationship():
                    logger.warning(
                        f"Skipping rep for {self.builder.name} at {self.community.name} - "
                        "no builder-community relationship exists"
                    )
                    continue

            # Try to find existing rep
            existing_rep = self._find_existing_rep(rep_name, rep_data)

            if existing_rep:
                # Update existing rep
                self._update_existing_rep(existing_rep, rep_data, source_url)
            else:
                # Create new rep
                self._create_new_rep(rep_data, source_url)
                new_rep_count += 1

        return new_rep_count

    def _find_existing_rep(
        self,
        name: str,
        rep_data: Dict[str, Any]
    ) -> Optional[SalesRep]:
        """
        Find existing sales rep by name, phone, or email.
        """
        # Try exact name match first
        query = self.db.query(SalesRep).filter(
            SalesRep.builder_id == self.builder.id
        )

        if self.community:
            query = query.filter(SalesRep.community_id == self.community.id)

        rep = query.filter(SalesRep.name.ilike(name)).first()
        if rep:
            return rep

        # Try phone match
        phone = rep_data.get("phone")
        if phone:
            rep = query.filter(SalesRep.phone.ilike(phone)).first()
            if rep:
                return rep

        # Try email match
        email = rep_data.get("email")
        if email:
            rep = query.filter(SalesRep.email.ilike(email)).first()
            if rep:
                return rep

        return None

    def _update_existing_rep(
        self,
        rep: SalesRep,
        rep_data: Dict[str, Any],
        source_url: Optional[str]
    ):
        """Update existing sales rep."""
        field_mapping = {
            "name": "name",
            "title": "title",
            "phone": "phone",
            "email": "email",
            "photo_url": "photo_url",
            "bio": "bio"
        }

        for collected_field, db_field in field_mapping.items():
            if collected_field in rep_data:
                new_value = rep_data[collected_field]
                old_value = getattr(rep, db_field, None)

                if new_value != old_value and new_value is not None:
                    self.record_change(
                        entity_type="sales_rep",
                        entity_id=rep.id,
                        change_type="modified",
                        field_name=db_field,
                        old_value=old_value,
                        new_value=new_value,
                        confidence=0.8,
                        source_url=source_url
                    )

        # Update last_seen_at
        self.record_change(
            entity_type="sales_rep",
            entity_id=rep.id,
            change_type="modified",
            field_name="last_seen_at",
            old_value=rep.last_seen_at.isoformat() if rep.last_seen_at else None,
            new_value=datetime.utcnow().isoformat(),
            confidence=1.0,
            source_url=source_url
        )

        # If rep was inactive, propose reactivation
        if not rep.is_active:
            self.record_change(
                entity_type="sales_rep",
                entity_id=rep.id,
                change_type="modified",
                field_name="is_active",
                old_value=False,
                new_value=True,
                confidence=0.9,
                source_url=source_url
            )

        # Update data_source
        if rep.data_source != "collected":
            self.record_change(
                entity_type="sales_rep",
                entity_id=rep.id,
                change_type="modified",
                field_name="data_source",
                old_value=rep.data_source,
                new_value="collected",
                confidence=1.0,
                source_url=source_url
            )

    def _create_new_rep(self, rep_data: Dict[str, Any], source_url: Optional[str]):
        """Create new sales rep."""
        entity_data = {
            "builder_id": self.builder.id,
            "community_id": self.community.id if self.community else None,
            "name": rep_data.get("name"),
            "title": rep_data.get("title"),
            "phone": rep_data.get("phone"),
            "email": rep_data.get("email"),
            "photo_url": rep_data.get("photo_url"),
            "bio": rep_data.get("bio"),
            "is_active": True,
            "last_seen_at": datetime.utcnow().isoformat(),
            "data_source": "collected"
        }

        self.record_change(
            entity_type="sales_rep",
            entity_id=None,
            change_type="added",
            is_new_entity=True,
            proposed_entity_data=entity_data,
            confidence=0.8,
            source_url=source_url
        )

    def _validate_builder_community_relationship(self) -> bool:
        """
        Validate that builder-community relationship exists.

        Returns:
            True if relationship exists, False otherwise
        """
        if not self.builder or not self.community:
            return True  # No validation needed

        # Check if builder is associated with this community
        # via the builder_communities association table
        from model.profiles.builder import builder_communities

        result = self.db.query(builder_communities).filter(
            and_(
                builder_communities.c.builder_id == self.builder.id,
                builder_communities.c.community_id == self.community.id
            )
        ).first()

        return result is not None

    def _check_inactive_reps(self, found_reps: List[Dict[str, Any]]) -> int:
        """
        Check for reps that should be marked inactive.

        Implements 60-day grace period:
        - If rep not found in collection
        - AND last_seen_at is older than 60 days
        - THEN mark as inactive

        Returns:
            Number of reps marked as inactive
        """
        # Get all active reps for this builder/community
        query = self.db.query(SalesRep).filter(
            SalesRep.builder_id == self.builder.id,
            SalesRep.is_active == True
        )

        if self.community:
            query = query.filter(SalesRep.community_id == self.community.id)

        active_reps = query.all()

        # Get names of reps found in collection
        found_rep_names = {rep.get("name", "").lower() for rep in found_reps if rep.get("name")}

        inactive_count = 0
        grace_period_cutoff = datetime.utcnow() - timedelta(days=INACTIVATION_GRACE_PERIOD_DAYS)

        for rep in active_reps:
            rep_name_lower = rep.name.lower() if rep.name else ""

            # Check if rep was found in collection
            if rep_name_lower in found_rep_names:
                continue

            # Check if rep has exceeded grace period
            if rep.last_seen_at and rep.last_seen_at > grace_period_cutoff:
                # Still in grace period
                logger.info(
                    f"Rep {rep.name} not found but still in grace period "
                    f"(last seen: {rep.last_seen_at})"
                )
                continue

            # Mark rep as inactive
            self.record_change(
                entity_type="sales_rep",
                entity_id=rep.id,
                change_type="modified",
                field_name="is_active",
                old_value=True,
                new_value=False,
                confidence=0.9,
                source_url=None
            )

            self.record_change(
                entity_type="sales_rep",
                entity_id=rep.id,
                change_type="modified",
                field_name="inactivation_reason",
                old_value=rep.inactivation_reason,
                new_value=f"Not found in data collection after {INACTIVATION_GRACE_PERIOD_DAYS}-day grace period",
                confidence=1.0,
                source_url=None
            )

            inactive_count += 1
            logger.info(f"Marked rep {rep.name} as inactive (exceeded grace period)")

        return inactive_count
