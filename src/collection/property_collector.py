"""
Property Collector Service

Collects property/inventory data from builders.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from model.property.property import Property
from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from .base_collector import BaseCollector
from .prompts import generate_property_collection_prompt
from .status_management import ImprovedPropertyStatusManager
from .auto_approval import AutoApprovalService

logger = logging.getLogger(__name__)


class PropertyCollector(BaseCollector):
    """
    Collects property/inventory data.

    Features:
    - Discovers available properties
    - Updates existing property details
    - Tracks all 45+ property fields from ENHANCED_PROPERTY_SCHEMA
    - Handles new property creation
    - Updates property status and availability
    """

    def __init__(self, db: Session, job_id: str):
        super().__init__(db, job_id)
        self.builder = None
        self.community = None
        self.status_manager = ImprovedPropertyStatusManager(db)
        self.auto_approval_service = AutoApprovalService(db)
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
        """Execute property data collection."""
        try:
            self.update_job_status("running")
            self.log("Starting property collection job", "INFO", "initialization")

            if not self.builder or not self.community:
                error_msg = "Both builder and community context required for property collection"
                self.log(error_msg, "ERROR", "initialization")
                raise ValueError(error_msg)

            builder_name = self.builder.name
            community_name = self.community.name
            filters = self.job.search_filters or {}
            location = filters.get("location", f"{self.community.city}, {self.community.state}")

            self.log(
                f"Collecting properties for {builder_name} in {community_name}",
                "INFO",
                "initialization",
                {
                    "builder_id": self.builder.id,
                    "builder_name": builder_name,
                    "community_id": self.community.id,
                    "community_name": community_name,
                    "location": location
                }
            )

            # Call Claude to collect property data
            self.log(f"Calling Claude API to search for properties", "INFO", "searching")
            prompt = generate_property_collection_prompt(
                builder_name,
                community_name,
                location
            )
            collected_data = self.call_claude(prompt)
            self.log("Claude API call completed successfully", "SUCCESS", "searching")

            # Process collected properties
            properties = collected_data.get("properties", [])
            self.log(
                f"Found {len(properties)} properties to process",
                "SUCCESS",
                "parsing",
                {"properties_count": len(properties)}
            )

            new_count = self._process_properties(properties, collected_data)

            # Update job results
            self.update_job_status(
                "completed",
                items_found=len(properties),
                new_entities_found=new_count
            )

            self.log(
                f"Property collection completed: {len(properties)} total, {new_count} new",
                "SUCCESS",
                "completed",
                {
                    "total_properties": len(properties),
                    "new_properties": new_count,
                    "changes_detected": self.job.changes_detected
                }
            )

        except Exception as e:
            error_msg = str(e)
            self.log(f"Property collection failed: {error_msg}", "ERROR", "failed",
                    {"error": error_msg, "error_type": type(e).__name__})
            logger.error(f"Property collection failed: {error_msg}", exc_info=True)
            self.update_job_status(
                "failed",
                error_message=error_msg
            )
            raise

    def _process_properties(
        self,
        properties: List[Dict[str, Any]],
        collected_data: Dict[str, Any]
    ) -> int:
        """
        Process collected property data.

        Returns:
            Number of new properties discovered
        """
        new_property_count = 0
        updated_count = 0
        sources = collected_data.get("sources", [])

        self.log(
            f"Processing {len(properties)} properties",
            "INFO",
            "matching",
            {"total_to_process": len(properties)}
        )

        for idx, prop_data in enumerate(properties, 1):
            # Generate address identifier (for new construction, may be lot number or plan name)
            address = prop_data.get("address")
            if not address:
                # Generate placeholder address for new construction
                lot_number = prop_data.get("lot_number", "")
                plan_name = prop_data.get("builder_plan_name", prop_data.get("title", ""))
                if lot_number:
                    address = f"Lot {lot_number}"
                elif plan_name:
                    address = f"{plan_name} (New Construction)"
                else:
                    address = "TBD (New Construction)"

                # Ensure we have required location fields from community
                if not prop_data.get("city"):
                    prop_data["city"] = self.community.city if self.community and self.community.city else "TBD"
                if not prop_data.get("state"):
                    prop_data["state"] = self.community.state if self.community and self.community.state else "TX"
                if not prop_data.get("zip_code"):
                    prop_data["zip_code"] = self.community.zip_code if self.community and self.community.zip_code else "00000"

                self.log(
                    f"Property without street address - using identifier: {address}",
                    "INFO",
                    "matching",
                    {"generated_address": address, "lot_number": lot_number, "plan_name": plan_name}
                )

            self.log(
                f"Processing property {idx}/{len(properties)}: {address}",
                "INFO",
                "matching",
                {"progress": f"{idx}/{len(properties)}", "address": address}
            )

            source_url = prop_data.get("source_url") or (sources[0] if sources else None)
            confidence = prop_data.get("confidence", 0.8)

            # Try to find existing property by address or other identifiers
            existing_property = self._find_existing_property(address, prop_data)

            if existing_property:
                # Update existing property
                self.log(
                    f"Found existing property match: {address}",
                    "INFO",
                    "matching",
                    {"property_id": existing_property.id, "address": address}
                )
                self._update_existing_property(existing_property, prop_data, source_url, confidence)
                # Verify listing is still active
                self.status_manager.verify_property_listing(existing_property.id)
                updated_count += 1
            else:
                # Create new property
                self.log(
                    f"New property discovered: {address}",
                    "INFO",
                    "matching",
                    {"address": address}
                )
                self._create_new_property(prop_data, source_url, confidence)
                new_property_count += 1

        self.log(
            f"Property processing complete: {new_property_count} new, {updated_count} updated",
            "SUCCESS",
            "saving",
            {"new_properties": new_property_count, "updated_properties": updated_count}
        )

        return new_property_count

    def _find_existing_property(
        self,
        address: str,
        prop_data: Dict[str, Any]
    ) -> Optional[Property]:
        """Find existing property by address."""
        # Try exact address match
        prop = self.db.query(Property).filter(
            Property.builder_id == self.builder.id,
            Property.address1.ilike(address)
        ).first()

        if prop:
            return prop

        # Try matching by address components
        city = prop_data.get("city")
        zip_code = prop_data.get("zip_code")

        if city and zip_code:
            # Try partial address match with city and zip
            prop = self.db.query(Property).filter(
                Property.builder_id == self.builder.id,
                Property.city.ilike(city),
                Property.postal_code == zip_code,
                Property.address1.ilike(f"%{address.split()[0]}%")  # Match street number
            ).first()

            if prop:
                return prop

        return None

    def _update_existing_property(
        self,
        prop: Property,
        prop_data: Dict[str, Any],
        source_url: Optional[str],
        confidence: float
    ):
        """Update existing property with collected data."""
        # All property fields to check for changes
        field_mapping = {
            # Basic info
            "title": "title",
            "description": "description",
            "property_type": "property_type",
            "status": "listing_status",
            # Specifications
            "price": "price",
            "beds": "bedrooms",
            "baths": "bathrooms",
            "sqft": "sqft",
            "lot_size": "lot_sqft",
            "year_built": "year_built",
            "stories": "stories",
            "garage_spaces": "garage_spaces",
            # Lot details
            "lot_number": "lot_number",
            "corner_lot": "corner_lot",
            "cul_de_sac": "cul_de_sac",
            "lot_backing": "lot_backing",
            # Schools
            "school_district": "school_district",
            "elementary_school": "elementary_school",
            "middle_school": "middle_school",
            "high_school": "high_school",
            "school_ratings": "school_ratings",
            # Builder-specific
            "model_home": "model_home",
            "quick_move_in": "quick_move_in",
            "construction_stage": "construction_stage",
            "estimated_completion": "estimated_completion",
            "builder_plan_name": "builder_plan_name",
            # Pricing & market
            "price_per_sqft": "price_per_sqft",
            "days_on_market": "days_on_market",
            "builder_incentives": "builder_incentives",
            "upgrades_included": "upgrades_included",
            "upgrades_value": "upgrades_value"
        }

        changes_found = 0
        for collected_field, db_field in field_mapping.items():
            if collected_field in prop_data:
                new_value = prop_data[collected_field]
                old_value = getattr(prop, db_field, None)

                # Skip if values are the same
                if new_value == old_value:
                    continue

                # Skip if new value is None
                if new_value is None:
                    continue

                # Record change
                self.record_change(
                    entity_type="property",
                    entity_id=prop.id,
                    change_type="modified",
                    field_name=db_field,
                    old_value=old_value,
                    new_value=new_value,
                    confidence=confidence,
                    source_url=source_url
                )
                changes_found += 1

        if changes_found > 0:
            self.log(
                f"Detected {changes_found} field changes for property",
                "INFO",
                "saving",
                {"property_id": prop.id, "changes_count": changes_found}
            )

    def _create_new_property(
        self,
        prop_data: Dict[str, Any],
        source_url: Optional[str],
        confidence: float
    ):
        """Create new property from collected data."""
        address = prop_data.get("address", "Unknown")
        price = prop_data.get("price")
        beds = prop_data.get("beds")
        baths = prop_data.get("baths")

        entity_data = {
            # IDs
            "builder_id": self.builder.id,
            "builder_id_string": self.builder.builder_id if self.builder else None,
            "community_id": self.community.id if self.community else None,
            "community_id_string": self.community.community_id if self.community else None,
            # Basic info
            "title": prop_data.get("title"),
            "address1": address,
            "city": prop_data.get("city"),
            "state": prop_data.get("state"),
            "postal_code": prop_data.get("zip_code"),
            "description": prop_data.get("description"),
            "property_type": prop_data.get("property_type"),
            "listing_status": prop_data.get("status", "available"),
            # Specifications
            "price": price,
            "bedrooms": beds,
            "bathrooms": baths,
            "sqft": prop_data.get("sqft"),
            "lot_sqft": prop_data.get("lot_size"),
            "year_built": prop_data.get("year_built"),
            "stories": prop_data.get("stories"),
            "garage_spaces": prop_data.get("garage_spaces"),
            # Lot details
            "lot_number": prop_data.get("lot_number"),
            "corner_lot": prop_data.get("corner_lot", False),
            "cul_de_sac": prop_data.get("cul_de_sac", False),
            "lot_backing": prop_data.get("lot_backing"),
            # Schools
            "school_district": prop_data.get("school_district"),
            "elementary_school": prop_data.get("elementary_school"),
            "middle_school": prop_data.get("middle_school"),
            "high_school": prop_data.get("high_school"),
            "school_ratings": prop_data.get("school_ratings"),
            # Builder-specific
            "model_home": prop_data.get("model_home", False),
            "quick_move_in": prop_data.get("quick_move_in", False),
            "construction_stage": prop_data.get("construction_stage"),
            "estimated_completion": prop_data.get("estimated_completion"),
            "builder_plan_name": prop_data.get("builder_plan_name"),
            # Pricing & market
            "price_per_sqft": prop_data.get("price_per_sqft"),
            "days_on_market": prop_data.get("days_on_market"),
            "builder_incentives": prop_data.get("builder_incentives"),
            "upgrades_included": prop_data.get("upgrades_included"),
            "upgrades_value": prop_data.get("upgrades_value"),
            # Media
            "virtual_tour_url": prop_data.get("virtual_tour_url"),
            "floor_plan_url": prop_data.get("floor_plan_url"),
            "media_urls": prop_data.get("images", [])
        }

        self.log(
            f"Recording new property: {address} (${price:,} | {beds}bed/{baths}bath)" if price else f"Recording new property: {address}",
            "INFO",
            "saving",
            {
                "address": address,
                "price": price,
                "beds": beds,
                "baths": baths,
                "confidence": confidence
            }
        )

        # Record the change
        change = self.record_change(
            entity_type="property",
            entity_id=None,
            change_type="added",
            is_new_entity=True,
            proposed_entity_data=entity_data,
            confidence=confidence,
            source_url=source_url
        )

        # Process through auto-approval logic
        try:
            approved_property = self.auto_approval_service.process_change(change)
            if approved_property:
                self.log(
                    f"Property AUTO-APPROVED: {address} (ID: {approved_property.id})",
                    "SUCCESS",
                    "saving",
                    {"property_id": approved_property.id, "auto_approved": True}
                )
        except Exception as e:
            self.log(
                f"Auto-approval failed for {address}: {str(e)}",
                "WARNING",
                "saving",
                {"error": str(e)}
            )

        self.record_entity_match(
            discovered_entity_type="property",
            discovered_name=prop_data.get("title") or prop_data.get("address") or "Unknown Property",
            discovered_data=prop_data,
            discovered_location=prop_data.get("address"),
            matched_entity_id=None,
            match_confidence=None,
            match_method="no_match_found"
        )
