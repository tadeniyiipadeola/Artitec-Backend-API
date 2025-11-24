"""
Status Event Subscribers

Example event handlers that react to status changes.
These can be extended for your specific use cases.
"""
import logging
from typing import Dict, Any
from .event_bus import StatusChangeEvent, status_event_bus
from .enums import BuilderStatus, PropertyListingStatus

logger = logging.getLogger(__name__)


# ===================================================================
# Notification Subscribers
# ===================================================================

def builder_inactivation_notification_handler(event: StatusChangeEvent) -> None:
    """
    Send notifications when builders become inactive or go out of business.

    This is a placeholder - integrate with your notification service.
    """
    if event.entity_type != 'builder':
        return

    if event.new_status in [BuilderStatus.INACTIVE.value, BuilderStatus.OUT_OF_BUSINESS.value]:
        builder_name = event.metadata.get('builder_name', f'Builder #{event.entity_id}')

        logger.warning(
            f"NOTIFICATION: Builder '{builder_name}' is now {event.new_status}. "
            f"Reason: {event.reason}"
        )

        # TODO: Integrate with notification service
        # notification_service.send_email(
        #     to=admin_emails,
        #     subject=f"Builder Status Change: {builder_name}",
        #     body=f"Builder {builder_name} changed from {event.old_status} to {event.new_status}. "
        #          f"Reason: {event.reason}"
        # )


def property_sold_notification_handler(event: StatusChangeEvent) -> None:
    """
    Send notifications when properties are sold.

    This is a placeholder - integrate with your notification service.
    """
    if event.entity_type != 'property':
        return

    if event.new_status == PropertyListingStatus.SOLD.value:
        property_title = event.metadata.get('property_title', f'Property #{event.entity_id}')

        logger.info(
            f"NOTIFICATION: Property '{property_title}' has been sold!"
        )

        # TODO: Integrate with notification service
        # notification_service.send_email(
        #     to=sales_team_emails,
        #     subject=f"Property Sold: {property_title}",
        #     body=f"Congratulations! Property {property_title} has been sold."
        # )


# ===================================================================
# Analytics Subscribers
# ===================================================================

def status_analytics_handler(event: StatusChangeEvent) -> None:
    """
    Track status changes for analytics and reporting.

    This is a placeholder - integrate with your analytics service.
    """
    logger.info(
        f"ANALYTICS: {event.entity_type} #{event.entity_id} "
        f"status change tracked: {event.old_status} → {event.new_status}"
    )

    # TODO: Send to analytics service
    # analytics_service.track_event(
    #     event_name='status_change',
    #     properties={
    #         'entity_type': event.entity_type,
    #         'entity_id': event.entity_id,
    #         'status_field': event.status_field,
    #         'old_status': event.old_status,
    #         'new_status': event.new_status,
    #         'change_source': event.change_source,
    #         'timestamp': event.timestamp.isoformat()
    #     }
    # )


# ===================================================================
# Cascade Subscribers
# ===================================================================

def builder_status_cascade_handler(event: StatusChangeEvent) -> None:
    """
    Cascade builder status changes to related entities.

    When a builder goes out of business or is suspended:
    - Mark all their properties as off-market
    - Update communities if builder was primary

    This is a placeholder - implement based on your business logic.
    """
    if event.entity_type != 'builder':
        return

    if event.new_status in [BuilderStatus.OUT_OF_BUSINESS.value, BuilderStatus.SUSPENDED.value]:
        builder_name = event.metadata.get('builder_name', f'Builder #{event.entity_id}')

        logger.warning(
            f"CASCADE: Builder '{builder_name}' is {event.new_status}. "
            f"Related properties and communities should be updated."
        )

        # TODO: Implement cascade logic
        # 1. Query all properties for this builder
        # properties = db.query(Property).filter(Property.builder_id == event.entity_id).all()
        #
        # 2. Update each property to off-market
        # for prop in properties:
        #     property_status_manager.update_property_status(
        #         prop.id,
        #         PropertyListingStatus.OFF_MARKET,
        #         f"Builder {builder_name} is {event.new_status}",
        #         changed_by='system'
        #     )
        #
        # 3. Update communities where this builder is primary
        # communities = db.query(Community).filter(Community.primary_builder_id == event.entity_id).all()
        # for community in communities:
        #     community_status_manager.update_availability_from_inventory(community.id)


# ===================================================================
# Webhook Subscribers
# ===================================================================

def external_webhook_handler(event: StatusChangeEvent) -> None:
    """
    Send status change events to external systems via webhooks.

    This is a placeholder - integrate with your webhook service.
    """
    # Only send certain events to external systems
    if event.entity_type in ['builder', 'property']:
        logger.info(
            f"WEBHOOK: Sending status change event to external systems: "
            f"{event.entity_type} #{event.entity_id}"
        )

        # TODO: Send to webhook service
        # webhook_service.send(
        #     url=config.EXTERNAL_WEBHOOK_URL,
        #     payload=event.to_dict(),
        #     headers={'X-Event-Type': 'status_change'}
        # )


# ===================================================================
# Registration
# ===================================================================

def register_all_subscribers():
    """
    Register all event subscribers.

    Call this during application startup to activate all handlers.
    """
    # Notification handlers
    status_event_bus.subscribe(builder_inactivation_notification_handler)
    status_event_bus.subscribe(property_sold_notification_handler)

    # Analytics handlers
    status_event_bus.subscribe(status_analytics_handler)

    # Cascade handlers
    status_event_bus.subscribe(builder_status_cascade_handler)

    # Webhook handlers
    status_event_bus.subscribe(external_webhook_handler)

    logger.info("All status event subscribers registered")


def unregister_all_subscribers():
    """
    Unregister all event subscribers.

    Useful for testing or shutdown.
    """
    status_event_bus.unsubscribe(builder_inactivation_notification_handler)
    status_event_bus.unsubscribe(property_sold_notification_handler)
    status_event_bus.unsubscribe(status_analytics_handler)
    status_event_bus.unsubscribe(builder_status_cascade_handler)
    status_event_bus.unsubscribe(external_webhook_handler)

    logger.info("All status event subscribers unregistered")
