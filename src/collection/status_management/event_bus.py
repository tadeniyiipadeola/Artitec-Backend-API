"""
Status Event System

Provides event-driven architecture for status changes.
Allows decoupled notification, logging, and cascading updates.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class StatusChangeEvent:
    """
    Event fired when an entity's status changes.

    This event is published to all subscribers after a status change.
    """
    # Entity identification
    entity_type: str  # builder, community, property, sales_rep
    entity_id: int

    # Status change details
    status_field: str  # business_status, listing_status, etc.
    old_status: Optional[str]
    new_status: str

    # Context
    reason: str
    changed_by: str  # user_id or 'system'
    change_source: str  # manual, auto, collection

    # Timestamp
    timestamp: datetime

    # Additional context
    metadata: Dict[str, Any]

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'status_field': self.status_field,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'reason': self.reason,
            'changed_by': self.changed_by,
            'change_source': self.change_source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class StatusEventBus:
    """
    Event bus for status change events.

    Allows components to subscribe to status changes and react accordingly.
    Enables decoupled architecture.

    Example subscribers:
    - Notification service (send emails)
    - Analytics service (track metrics)
    - Cascade service (update related entities)
    - Webhook service (notify external systems)
    """

    def __init__(self):
        self._subscribers: List[Callable[[StatusChangeEvent], None]] = []

    def subscribe(self, handler: Callable[[StatusChangeEvent], None]) -> None:
        """
        Subscribe to status change events.

        Args:
            handler: Function that takes StatusChangeEvent and returns None
        """
        if handler not in self._subscribers:
            self._subscribers.append(handler)
            logger.info(f"Subscribed handler: {handler.__name__}")

    def unsubscribe(self, handler: Callable[[StatusChangeEvent], None]) -> None:
        """
        Unsubscribe from status change events.

        Args:
            handler: Previously subscribed handler
        """
        if handler in self._subscribers:
            self._subscribers.remove(handler)
            logger.info(f"Unsubscribed handler: {handler.__name__}")

    def publish(self, event: StatusChangeEvent) -> None:
        """
        Publish status change event to all subscribers.

        Args:
            event: StatusChangeEvent to publish
        """
        logger.info(
            f"Publishing event: {event.entity_type}#{event.entity_id} "
            f"{event.old_status} -> {event.new_status}"
        )

        for handler in self._subscribers:
            try:
                handler(event)
            except Exception as e:
                # Don't let subscriber errors break the event loop
                logger.error(
                    f"Event handler {handler.__name__} failed: {str(e)}",
                    exc_info=True
                )

    def clear_subscribers(self) -> None:
        """Clear all subscribers (useful for testing)."""
        self._subscribers.clear()
        logger.info("Cleared all event subscribers")


# Global event bus instance
status_event_bus = StatusEventBus()


# ===================================================================
# Built-in Event Handlers
# ===================================================================

def log_status_change_handler(event: StatusChangeEvent) -> None:
    """
    Default handler that logs all status changes.

    This provides structured logging for status changes.
    """
    logger.info(
        f"Status change: {event.entity_type}#{event.entity_id} "
        f"[{event.status_field}] {event.old_status} → {event.new_status} | "
        f"Reason: {event.reason} | Source: {event.change_source}",
        extra=event.to_dict()
    )


# Register default handlers
status_event_bus.subscribe(log_status_change_handler)
