"""
Auto-Approval Service

Automatically approves or denies property changes based on data quality rules.
"""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from model.collection import CollectionChange
from model.property.property import Property
from .notification_service import get_notification_service

logger = logging.getLogger(__name__)


class AutoApprovalService:
    """
    Service for automatically approving or denying property changes.

    Auto-Approval Rules:
    - Properties with confidence > 90%, beds > 0, baths > 0 are AUTO-APPROVED
    - Properties with confidence < 75%, beds < 1, baths < 1 are AUTO-DENIED
    - All others require manual review
    """

    # Auto-approval thresholds
    AUTO_APPROVE_CONFIDENCE = 0.90
    AUTO_DENY_CONFIDENCE = 0.75

    def __init__(self, db: Session):
        self.db = db
        self.notification_service = get_notification_service(db)

    def should_auto_approve(self, change: CollectionChange) -> Optional[bool]:
        """
        Determine if a property change should be auto-approved or auto-denied.

        Returns:
            True: Auto-approve
            False: Auto-deny
            None: Requires manual review
        """
        # Only auto-process new property additions
        if change.entity_type != "property" or change.change_type != "added":
            return None

        # Get property data from proposed_entity_data
        data = change.proposed_entity_data or {}

        # Extract key fields
        confidence = data.get("data_confidence", 0.0)
        bedrooms = data.get("bedrooms", 0)
        bathrooms = data.get("bathrooms", 0)
        price = data.get("price", 0)

        logger.info(
            f"Evaluating change {change.id} for auto-approval: "
            f"confidence={confidence}, beds={bedrooms}, baths={bathrooms}, price={price}"
        )

        # Auto-APPROVE: High confidence + valid bed/bath
        if confidence > self.AUTO_APPROVE_CONFIDENCE and bedrooms > 0 and bathrooms > 0:
            logger.info(
                f"Change {change.id} qualifies for AUTO-APPROVAL "
                f"(confidence {confidence:.0%} > {self.AUTO_APPROVE_CONFIDENCE:.0%}, "
                f"beds {bedrooms} > 0, baths {bathrooms} > 0)"
            )
            return True

        # Auto-DENY: Low confidence OR missing bed/bath
        if confidence < self.AUTO_DENY_CONFIDENCE or bedrooms < 1 or bathrooms < 1:
            logger.info(
                f"Change {change.id} qualifies for AUTO-DENIAL "
                f"(confidence {confidence:.0%} < {self.AUTO_DENY_CONFIDENCE:.0%} "
                f"OR beds {bedrooms} < 1 OR baths {bathrooms} < 1)"
            )
            return False

        # Requires manual review
        logger.info(
            f"Change {change.id} requires MANUAL REVIEW "
            f"(confidence {confidence:.0%} between thresholds, beds/baths acceptable)"
        )
        return None

    def auto_approve_change(self, change: CollectionChange) -> Property:
        """
        Automatically approve a property change and create the property.

        Returns:
            The created Property instance
        """
        data = change.proposed_entity_data or {}

        # Validate required foreign keys
        builder_id = data.get("builder_id")
        community_id = data.get("community_id")

        if not builder_id or not community_id:
            raise ValueError(f"Missing required builder_id or community_id in change {change.id}")

        # Create the property
        property = Property(
            # REQUIRED foreign keys
            builder_id=builder_id,
            builder_id_string=data.get("builder_id_string"),
            community_id=community_id,
            community_id_string=data.get("community_id_string"),

            # Basic info
            title=data.get("title", "Untitled Property"),
            description=data.get("description"),

            # Address
            address1=data.get("address1") or "Address TBD",
            city=data.get("city", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),

            # Required fields with defaults
            price=data.get("price") or 0,
            bedrooms=data.get("bedrooms") or 0,
            bathrooms=data.get("bathrooms") or 0,

            # Specifications
            sqft=data.get("sqft"),
            lot_sqft=data.get("lot_sqft"),
            year_built=data.get("year_built"),
            property_type=data.get("property_type"),
            listing_status=data.get("listing_status", "available"),
            stories=data.get("stories"),
            garage_spaces=data.get("garage_spaces"),

            # Lot details
            lot_number=data.get("lot_number"),
            corner_lot=data.get("corner_lot", False),
            cul_de_sac=data.get("cul_de_sac", False),
            lot_backing=data.get("lot_backing"),

            # Schools
            school_district=data.get("school_district"),
            elementary_school=data.get("elementary_school"),
            middle_school=data.get("middle_school"),
            high_school=data.get("high_school"),
            school_ratings=data.get("school_ratings"),

            # Builder-specific
            model_home=data.get("model_home", False),
            quick_move_in=data.get("quick_move_in", False),
            construction_stage=data.get("construction_stage"),
            estimated_completion=data.get("estimated_completion"),
            builder_plan_name=data.get("builder_plan_name"),

            # Pricing
            price_per_sqft=data.get("price_per_sqft"),
            days_on_market=data.get("days_on_market"),
            builder_incentives=data.get("builder_incentives"),
            upgrades_included=data.get("upgrades_included"),
            upgrades_value=data.get("upgrades_value"),

            # Media
            virtual_tour_url=data.get("virtual_tour_url"),
            floor_plan_url=data.get("floor_plan_url"),
            media_urls=data.get("media_urls", []),

            # Collection metadata
            source_url=data.get("source_url"),
            data_confidence=data.get("data_confidence", 0.8),

            # Approval metadata - AUTO-APPROVED (no user ID for system auto-approval)
            approved_at=datetime.utcnow(),
            approved_by_user_id=None  # None indicates system auto-approval
        )

        self.db.add(property)
        self.db.flush()  # Get the property ID

        # Update the change record
        change.entity_id = property.id
        change.review_status = "approved"
        change.review_notes = f"AUTO-APPROVED: High confidence ({data.get('data_confidence', 0):.0%}), valid beds/baths"
        change.reviewed_at = datetime.utcnow()

        logger.info(
            f"Auto-approved change {change.id}, created property {property.id} "
            f"({property.address1}, {property.city})"
        )

        # Send auto-approval notifications
        try:
            confidence = data.get("data_confidence", 0.8)
            self.notification_service.notify_auto_approved(
                property=property,
                change=change,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Failed to send auto-approval notification: {e}")

        return property

    def auto_deny_change(self, change: CollectionChange):
        """
        Automatically deny a property change.
        """
        data = change.proposed_entity_data or {}
        confidence = data.get("data_confidence", 0)
        bedrooms = data.get("bedrooms", 0)
        bathrooms = data.get("bathrooms", 0)

        # Build denial reason
        reasons = []
        if confidence < self.AUTO_DENY_CONFIDENCE:
            reasons.append(f"low confidence ({confidence:.0%})")
        if bedrooms < 1:
            reasons.append(f"invalid bedrooms ({bedrooms})")
        if bathrooms < 1:
            reasons.append(f"invalid bathrooms ({bathrooms})")

        denial_reason = f"AUTO-DENIED: {', '.join(reasons)}"

        # Update the change record
        change.review_status = "rejected"
        change.review_notes = denial_reason
        change.reviewed_at = datetime.utcnow()

        logger.info(
            f"Auto-denied change {change.id}: {denial_reason} "
            f"(address: {data.get('address1', 'Unknown')})"
        )

        # Send auto-denial notifications
        try:
            self.notification_service.notify_auto_denied(
                change=change,
                property_data=data,
                confidence=confidence,
                denial_reason=denial_reason
            )
        except Exception as e:
            logger.error(f"Failed to send auto-denial notification: {e}")

    def process_change(self, change: CollectionChange) -> Optional[Property]:
        """
        Process a change through auto-approval logic.

        Returns:
            Property if auto-approved, None otherwise
        """
        decision = self.should_auto_approve(change)

        if decision is True:
            # Auto-approve
            return self.auto_approve_change(change)
        elif decision is False:
            # Auto-deny
            self.auto_deny_change(change)
            return None
        else:
            # Requires manual review
            logger.info(f"Change {change.id} flagged for manual review")

            # Send manual review notification
            try:
                data = change.proposed_entity_data or {}
                confidence = data.get("data_confidence", 0.0)
                reason = f"Confidence {confidence:.0%} is between thresholds ({self.AUTO_DENY_CONFIDENCE:.0%} - {self.AUTO_APPROVE_CONFIDENCE:.0%})"

                self.notification_service.notify_manual_review_required(
                    change=change,
                    property_data=data,
                    confidence=confidence,
                    reason=reason
                )
            except Exception as e:
                logger.error(f"Failed to send manual review notification: {e}")

            return None
