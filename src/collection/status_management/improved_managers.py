"""
Improved Status Managers - Phase 1

Enhanced status managers with:
- State machine validation
- Status history tracking
- Event publishing
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from model.property.property import Property
from .enums import BuilderStatus, PropertyListingStatus
from .state_machine import StatusStateMachine, InvalidStatusTransitionError
from .event_bus import status_event_bus, StatusChangeEvent
from .history import StatusHistory

logger = logging.getLogger(__name__)

# Grace period configurations (move to config later)
BUILDER_INACTIVATION_GRACE_PERIOD_DAYS = 90
PROPERTY_ARCHIVE_GRACE_PERIOD_DAYS = 60


class ImprovedBuilderStatusManager:
    """
    Enhanced Builder Status Manager with Phase 1 improvements.

    Features:
    - State machine validation
    - Full audit trail via status_history
    - Event publishing for notifications
    """

    def __init__(self, db: Session):
        self.db = db

    def update_builder_activity(
        self,
        builder_id: int,
        changed_by: str = 'system'
    ):
        """
        Update builder's last activity timestamp.

        Automatically reactivates inactive builders.
        """
        builder = self._get_builder(builder_id)
        if not builder:
            return

        builder.last_activity_at = datetime.utcnow()

        # If builder was inactive, reactivate
        if not builder.is_active or builder.business_status != BuilderStatus.ACTIVE.value:
            old_status = builder.business_status

            # Validate transition
            try:
                StatusStateMachine.validate_builder_transition(
                    BuilderStatus(old_status),
                    BuilderStatus.ACTIVE
                )
            except InvalidStatusTransitionError as e:
                logger.warning(f"Cannot reactivate builder {builder_id}: {e}")
                self.db.commit()
                return

            # Update status
            builder.is_active = True
            builder.business_status = BuilderStatus.ACTIVE.value
            builder.inactivated_at = None
            builder.inactivation_reason = None

            # Record history
            self._record_history(
                entity_type='builder',
                entity_id=builder_id,
                status_field='business_status',
                old_status=old_status,
                new_status=BuilderStatus.ACTIVE.value,
                reason='Activity detected - automatic reactivation',
                changed_by=changed_by,
                change_source='auto'
            )

            # Publish event
            self._publish_event(
                entity_type='builder',
                entity_id=builder_id,
                status_field='business_status',
                old_status=old_status,
                new_status=BuilderStatus.ACTIVE.value,
                reason='Activity detected',
                changed_by=changed_by,
                change_source='auto',
                metadata={'builder_name': builder.name}
            )

            logger.info(f"Builder {builder.name} reactivated due to activity")

        self.db.commit()

    def update_builder_status(
        self,
        builder_id: int,
        new_status: BuilderStatus,
        reason: str,
        changed_by: str = 'system'
    ):
        """
        Update builder status with full validation and tracking.

        Args:
            builder_id: Builder ID
            new_status: New BuilderStatus enum value
            reason: Reason for status change
            changed_by: User ID or 'system'

        Raises:
            InvalidStatusTransitionError: If transition is not allowed
        """
        builder = self._get_builder(builder_id)
        if not builder:
            raise ValueError(f"Builder {builder_id} not found")

        old_status = BuilderStatus(builder.business_status)

        # Validate transition
        StatusStateMachine.validate_builder_transition(old_status, new_status)

        # Update entity
        builder.business_status = new_status.value

        if new_status in [BuilderStatus.INACTIVE, BuilderStatus.OUT_OF_BUSINESS]:
            builder.is_active = False
            builder.inactivated_at = datetime.utcnow()
            builder.inactivation_reason = reason
        elif new_status == BuilderStatus.ACTIVE:
            builder.is_active = True
            builder.inactivated_at = None
            builder.inactivation_reason = None

        # Record history
        self._record_history(
            entity_type='builder',
            entity_id=builder_id,
            status_field='business_status',
            old_status=old_status.value,
            new_status=new_status.value,
            reason=reason,
            changed_by=changed_by,
            change_source='manual'
        )

        # Publish event
        self._publish_event(
            entity_type='builder',
            entity_id=builder_id,
            status_field='business_status',
            old_status=old_status.value,
            new_status=new_status.value,
            reason=reason,
            changed_by=changed_by,
            change_source='manual',
            metadata={'builder_name': builder.name}
        )

        self.db.commit()
        logger.info(f"Builder {builder.name} status: {old_status.value} → {new_status.value}")

    def check_inactive_builders(self) -> List[BuilderProfile]:
        """Check for builders that should be marked inactive."""
        grace_period_cutoff = datetime.utcnow() - timedelta(
            days=BUILDER_INACTIVATION_GRACE_PERIOD_DAYS
        )

        inactive_builders = self.db.query(BuilderProfile).filter(
            and_(
                BuilderProfile.is_active == True,
                BuilderProfile.business_status == BuilderStatus.ACTIVE.value,
                BuilderProfile.last_activity_at < grace_period_cutoff
            )
        ).all()

        for builder in inactive_builders:
            try:
                self.update_builder_status(
                    builder_id=builder.id,
                    new_status=BuilderStatus.INACTIVE,
                    reason=f"No activity for {BUILDER_INACTIVATION_GRACE_PERIOD_DAYS} days",
                    changed_by='system'
                )
            except Exception as e:
                logger.error(f"Failed to inactivate builder {builder.id}: {e}")

        return inactive_builders

    def get_status_history(
        self,
        builder_id: int,
        limit: int = 10
    ) -> List[StatusHistory]:
        """Get status change history for builder."""
        return self.db.query(StatusHistory).filter(
            StatusHistory.entity_type == 'builder',
            StatusHistory.entity_id == builder_id
        ).order_by(StatusHistory.created_at.desc()).limit(limit).all()

    def _get_builder(self, builder_id: int) -> Optional[BuilderProfile]:
        """Get builder by ID."""
        return self.db.query(BuilderProfile).filter(
            BuilderProfile.id == builder_id
        ).first()

    def _record_history(
        self,
        entity_type: str,
        entity_id: int,
        status_field: str,
        old_status: Optional[str],
        new_status: str,
        reason: str,
        changed_by: str,
        change_source: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record status change in history table."""
        history = StatusHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            status_field=status_field,
            old_status=old_status,
            new_status=new_status,
            change_reason=reason,
            changed_by=changed_by,
            change_source=change_source,
            change_metadata=metadata or {}
        )
        self.db.add(history)

    def _publish_event(
        self,
        entity_type: str,
        entity_id: int,
        status_field: str,
        old_status: Optional[str],
        new_status: str,
        reason: str,
        changed_by: str,
        change_source: str,
        metadata: Dict[str, Any]
    ):
        """Publish status change event."""
        event = StatusChangeEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            status_field=status_field,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=changed_by,
            change_source=change_source,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        status_event_bus.publish(event)


class ImprovedCommunityStatusManager:
    """
    Enhanced Community Status Manager with Phase 1 improvements.
    """

    def __init__(self, db: Session):
        self.db = db

    def update_community_activity(
        self,
        community_id: int,
        changed_by: str = 'system'
    ):
        """Update community's last activity timestamp."""
        community = self._get_community(community_id)
        if not community:
            return

        community.last_activity_at = datetime.utcnow()
        self.db.commit()

    def update_availability_from_inventory(
        self,
        community_id: int,
        changed_by: str = 'system'
    ):
        """Update community availability based on property inventory."""
        community = self._get_community(community_id)
        if not community:
            return

        # Count available properties
        available_count = self.db.query(Property).filter(
            and_(
                Property.community_id == community_id,
                Property.listing_status.in_([
                    PropertyListingStatus.AVAILABLE.value,
                    PropertyListingStatus.PENDING.value,
                    PropertyListingStatus.RESERVED.value
                ])
            )
        ).count()

        old_status = community.availability_status

        # Determine new status
        if available_count == 0:
            new_availability = 'sold_out'
        elif available_count < 5:
            new_availability = 'limited'
        else:
            new_availability = 'available'

        # Only update if changed
        if old_status != new_availability:
            community.availability_status = new_availability
            community.status_changed_at = datetime.utcnow()

            # Record history
            self._record_history(
                entity_type='community',
                entity_id=community_id,
                status_field='availability_status',
                old_status=old_status,
                new_status=new_availability,
                reason=f'Inventory-based update: {available_count} available properties',
                changed_by=changed_by,
                change_source='auto'
            )

            # Publish event
            self._publish_event(
                entity_type='community',
                entity_id=community_id,
                status_field='availability_status',
                old_status=old_status,
                new_status=new_availability,
                reason=f'Inventory update: {available_count} available',
                changed_by=changed_by,
                change_source='auto',
                metadata={
                    'community_name': community.name,
                    'available_count': available_count
                }
            )

            logger.info(
                f"Community {community.name} availability: {old_status} → {new_availability} "
                f"({available_count} available)"
            )

        self.db.commit()

    def update_development_status(
        self,
        community_id: int,
        new_status: str,
        reason: str,
        changed_by: str = 'system'
    ):
        """Update community development status."""
        community = self._get_community(community_id)
        if not community:
            raise ValueError(f"Community {community_id} not found")

        old_status = community.development_status

        # Update entity
        community.development_status = new_status
        community.status_changed_at = datetime.utcnow()
        community.status_change_reason = reason

        # Record history
        self._record_history(
            entity_type='community',
            entity_id=community_id,
            status_field='development_status',
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=changed_by,
            change_source='manual'
        )

        # Publish event
        self._publish_event(
            entity_type='community',
            entity_id=community_id,
            status_field='development_status',
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=changed_by,
            change_source='manual',
            metadata={'community_name': community.name}
        )

        self.db.commit()
        logger.info(f"Community {community.name} development status: {old_status} → {new_status}")

    def _get_community(self, community_id: int) -> Optional[Community]:
        """Get community by ID."""
        return self.db.query(Community).filter(
            Community.id == community_id
        ).first()

    def _record_history(self, *args, **kwargs):
        """Record status change in history table."""
        history = StatusHistory(
            entity_type=kwargs['entity_type'],
            entity_id=kwargs['entity_id'],
            status_field=kwargs['status_field'],
            old_status=kwargs['old_status'],
            new_status=kwargs['new_status'],
            change_reason=kwargs['reason'],
            changed_by=kwargs['changed_by'],
            change_source=kwargs['change_source'],
            change_metadata=kwargs.get('metadata', {})
        )
        self.db.add(history)

    def _publish_event(self, **kwargs):
        """Publish status change event."""
        event = StatusChangeEvent(
            entity_type=kwargs['entity_type'],
            entity_id=kwargs['entity_id'],
            status_field=kwargs['status_field'],
            old_status=kwargs['old_status'],
            new_status=kwargs['new_status'],
            reason=kwargs['reason'],
            changed_by=kwargs['changed_by'],
            change_source=kwargs['change_source'],
            timestamp=datetime.utcnow(),
            metadata=kwargs['metadata']
        )
        status_event_bus.publish(event)


class ImprovedPropertyStatusManager:
    """
    Enhanced Property Status Manager with Phase 1 improvements.
    """

    def __init__(self, db: Session):
        self.db = db

    def update_property_status(
        self,
        property_id: int,
        new_status: PropertyListingStatus,
        reason: str,
        changed_by: str = 'system'
    ):
        """Update property listing status with validation."""
        prop = self._get_property(property_id)
        if not prop:
            raise ValueError(f"Property {property_id} not found")

        old_status = PropertyListingStatus(prop.listing_status)

        # Validate transition
        StatusStateMachine.validate_property_listing_transition(old_status, new_status)

        # Update entity
        prop.listing_status = new_status.value
        prop.status_changed_at = datetime.utcnow()
        prop.status_change_reason = reason

        # Auto-archive if sold
        if new_status == PropertyListingStatus.SOLD:
            prop.visibility_status = 'archived'

        # Update last verified
        prop.last_verified_at = datetime.utcnow()

        # Record history
        self._record_history(
            entity_type='property',
            entity_id=property_id,
            status_field='listing_status',
            old_status=old_status.value,
            new_status=new_status.value,
            reason=reason,
            changed_by=changed_by,
            change_source='manual'
        )

        # Publish event
        self._publish_event(
            entity_type='property',
            entity_id=property_id,
            status_field='listing_status',
            old_status=old_status.value,
            new_status=new_status.value,
            reason=reason,
            changed_by=changed_by,
            change_source='manual',
            metadata={'property_title': prop.title}
        )

        self.db.commit()
        logger.info(f"Property {prop.title} status: {old_status.value} → {new_status.value}")

    def verify_property_listing(self, property_id: int, changed_by: str = 'system'):
        """Mark property as verified."""
        prop = self._get_property(property_id)
        if not prop:
            return

        prop.last_verified_at = datetime.utcnow()
        prop.auto_archive_at = None
        self.db.commit()

    def _get_property(self, property_id: int) -> Optional[Property]:
        """Get property by ID."""
        return self.db.query(Property).filter(
            Property.id == property_id
        ).first()

    def _record_history(self, *args, **kwargs):
        """Record status change in history table."""
        history = StatusHistory(
            entity_type=kwargs['entity_type'],
            entity_id=kwargs['entity_id'],
            status_field=kwargs['status_field'],
            old_status=kwargs['old_status'],
            new_status=kwargs['new_status'],
            change_reason=kwargs['reason'],
            changed_by=kwargs['changed_by'],
            change_source=kwargs['change_source'],
            change_metadata=kwargs.get('metadata', {})
        )
        self.db.add(history)

    def _publish_event(self, **kwargs):
        """Publish status change event."""
        event = StatusChangeEvent(
            entity_type=kwargs['entity_type'],
            entity_id=kwargs['entity_id'],
            status_field=kwargs['status_field'],
            old_status=kwargs['old_status'],
            new_status=kwargs['new_status'],
            reason=kwargs['reason'],
            changed_by=kwargs['changed_by'],
            change_source=kwargs['change_source'],
            timestamp=datetime.utcnow(),
            metadata=kwargs['metadata']
        )
        status_event_bus.publish(event)
