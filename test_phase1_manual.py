"""
Manual Test for Phase 1 Status Management Implementation

Run this script to verify Phase 1 is working correctly.
"""
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test imports
try:
    from src.collection.status_management import (
        BuilderStatus,
        PropertyListingStatus,
        CommunityDevelopmentStatus,
        CommunityAvailabilityStatus,
        PropertyVisibilityStatus,
        StatusStateMachine,
        status_event_bus,
        StatusHistory,
        ImprovedBuilderStatusManager,
        ImprovedCommunityStatusManager,
        ImprovedPropertyStatusManager
    )
    from src.collection.status_management.state_machine import InvalidStatusTransitionError
    logger.info("✓ All imports successful")
except ImportError as e:
    logger.error(f"✗ Import failed: {e}")
    sys.exit(1)


def test_enums():
    """Test that enums are properly defined."""
    logger.info("\n=== Testing Enums ===")

    # Builder statuses
    assert BuilderStatus.ACTIVE == "active"
    assert BuilderStatus.INACTIVE == "inactive"
    assert BuilderStatus.OUT_OF_BUSINESS == "out_of_business"
    logger.info("✓ Builder status enums working")

    # Property statuses
    assert PropertyListingStatus.AVAILABLE == "available"
    assert PropertyListingStatus.SOLD == "sold"
    assert PropertyListingStatus.PENDING == "pending"
    logger.info("✓ Property status enums working")

    # Community statuses
    assert CommunityDevelopmentStatus.PLANNED == "planned"
    assert CommunityAvailabilityStatus.AVAILABLE == "available"
    logger.info("✓ Community status enums working")


def test_state_machine():
    """Test state machine validation."""
    logger.info("\n=== Testing State Machine ===")

    # Valid transitions
    assert StatusStateMachine.can_transition_builder(
        BuilderStatus.ACTIVE,
        BuilderStatus.INACTIVE
    )
    logger.info("✓ Valid builder transition allowed")

    # Invalid transitions
    assert not StatusStateMachine.can_transition_builder(
        BuilderStatus.OUT_OF_BUSINESS,
        BuilderStatus.ACTIVE
    )
    logger.info("✓ Invalid builder transition rejected")

    # Validation should raise error
    try:
        StatusStateMachine.validate_builder_transition(
            BuilderStatus.OUT_OF_BUSINESS,
            BuilderStatus.ACTIVE
        )
        logger.error("✗ Should have raised InvalidStatusTransitionError")
        return False
    except InvalidStatusTransitionError:
        logger.info("✓ State machine validation raises errors correctly")

    # Property transitions (AVAILABLE → PENDING is valid)
    assert StatusStateMachine.can_transition_property_listing(
        PropertyListingStatus.AVAILABLE,
        PropertyListingStatus.PENDING
    )
    logger.info("✓ Valid property transition allowed (AVAILABLE → PENDING)")

    assert not StatusStateMachine.can_transition_property_listing(
        PropertyListingStatus.SOLD,
        PropertyListingStatus.AVAILABLE
    )
    logger.info("✓ Invalid property transition rejected (sold → available)")

    return True


def test_event_system():
    """Test event publishing system."""
    logger.info("\n=== Testing Event System ===")

    from src.collection.status_management.event_bus import StatusChangeEvent

    events_received = []

    def test_handler(event):
        events_received.append(event)
        logger.info(f"  Event received: {event.entity_type} #{event.entity_id} → {event.new_status}")

    # Subscribe
    status_event_bus.subscribe(test_handler)
    logger.info("✓ Event handler subscribed")

    # Publish test event
    test_event = StatusChangeEvent(
        entity_type='builder',
        entity_id=999,
        status_field='business_status',
        old_status='active',
        new_status='inactive',
        reason='Test event',
        changed_by='test',
        change_source='manual',
        timestamp=datetime.utcnow(),
        metadata={'test': True}
    )

    status_event_bus.publish(test_event)

    # Check event was received
    if len(events_received) > 0:
        logger.info("✓ Event published and received")
    else:
        logger.error("✗ Event not received")
        return False

    # Unsubscribe
    status_event_bus.unsubscribe(test_handler)
    logger.info("✓ Event handler unsubscribed")

    return True


def test_status_history_model():
    """Test StatusHistory model structure."""
    logger.info("\n=== Testing StatusHistory Model ===")

    # Check that model has required fields
    required_fields = [
        'entity_type', 'entity_id', 'status_field',
        'old_status', 'new_status', 'change_reason',
        'changed_by', 'change_source', 'metadata'
    ]

    for field in required_fields:
        if not hasattr(StatusHistory, field):
            logger.error(f"✗ StatusHistory missing field: {field}")
            return False

    logger.info("✓ StatusHistory model has all required fields")
    return True


def test_manager_imports():
    """Test that managers can be instantiated (without DB)."""
    logger.info("\n=== Testing Manager Classes ===")

    # Just check that classes exist and have required methods
    required_builder_methods = [
        'update_builder_activity',
        'update_builder_status',
        'check_inactive_builders',
        'get_status_history'
    ]

    for method in required_builder_methods:
        if not hasattr(ImprovedBuilderStatusManager, method):
            logger.error(f"✗ ImprovedBuilderStatusManager missing method: {method}")
            return False

    logger.info("✓ ImprovedBuilderStatusManager has all required methods")

    required_property_methods = [
        'update_property_status',
        'verify_property_listing'
    ]

    for method in required_property_methods:
        if not hasattr(ImprovedPropertyStatusManager, method):
            logger.error(f"✗ ImprovedPropertyStatusManager missing method: {method}")
            return False

    logger.info("✓ ImprovedPropertyStatusManager has all required methods")

    required_community_methods = [
        'update_community_activity',
        'update_availability_from_inventory',
        'update_development_status'
    ]

    for method in required_community_methods:
        if not hasattr(ImprovedCommunityStatusManager, method):
            logger.error(f"✗ ImprovedCommunityStatusManager missing method: {method}")
            return False

    logger.info("✓ ImprovedCommunityStatusManager has all required methods")

    return True


def test_transition_rules():
    """Test specific transition rules."""
    logger.info("\n=== Testing Transition Rules ===")

    # Builder: ACTIVE → INACTIVE (allowed)
    assert StatusStateMachine.can_transition_builder(
        BuilderStatus.ACTIVE, BuilderStatus.INACTIVE
    )
    logger.info("✓ ACTIVE → INACTIVE allowed")

    # Builder: INACTIVE → ACTIVE (allowed, reactivation)
    assert StatusStateMachine.can_transition_builder(
        BuilderStatus.INACTIVE, BuilderStatus.ACTIVE
    )
    logger.info("✓ INACTIVE → ACTIVE allowed (reactivation)")

    # Builder: OUT_OF_BUSINESS → ACTIVE (NOT allowed, terminal state)
    assert not StatusStateMachine.can_transition_builder(
        BuilderStatus.OUT_OF_BUSINESS, BuilderStatus.ACTIVE
    )
    logger.info("✓ OUT_OF_BUSINESS → ACTIVE rejected (terminal state)")

    # Property: UNDER_CONTRACT → SOLD (allowed, normal sales flow)
    assert StatusStateMachine.can_transition_property_listing(
        PropertyListingStatus.UNDER_CONTRACT, PropertyListingStatus.SOLD
    )
    logger.info("✓ UNDER_CONTRACT → SOLD allowed")

    # Property: SOLD → AVAILABLE (NOT allowed)
    assert not StatusStateMachine.can_transition_property_listing(
        PropertyListingStatus.SOLD, PropertyListingStatus.AVAILABLE
    )
    logger.info("✓ SOLD → AVAILABLE rejected")

    # Property: OFF_MARKET → AVAILABLE (allowed, relisting)
    assert StatusStateMachine.can_transition_property_listing(
        PropertyListingStatus.OFF_MARKET, PropertyListingStatus.AVAILABLE
    )
    logger.info("✓ OFF_MARKET → AVAILABLE allowed (relisting)")

    return True


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("PHASE 1 STATUS MANAGEMENT - MANUAL TEST")
    logger.info("=" * 60)

    tests = [
        ("Enums", test_enums),
        ("State Machine", test_state_machine),
        ("Event System", test_event_system),
        ("Status History Model", test_status_history_model),
        ("Manager Classes", test_manager_imports),
        ("Transition Rules", test_transition_rules)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            if result is None:
                result = True  # If no explicit return, assume success
            results.append((name, result))
        except Exception as e:
            import traceback
            logger.error(f"\n✗ Test '{name}' failed with exception: {e}")
            logger.error(traceback.format_exc())
            results.append((name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Phase 1 implementation is working correctly.")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
