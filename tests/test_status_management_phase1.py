"""
Test Phase 1 Status Management Implementation

Tests:
- State machine validation
- Status history recording
- Event publishing
- Improved managers
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model.base import Base
from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from model.property.property import Property
from src.collection.status_management import (
    BuilderStatus,
    PropertyListingStatus,
    StatusStateMachine,
    ImprovedBuilderStatusManager,
    ImprovedCommunityStatusManager,
    ImprovedPropertyStatusManager,
    status_event_bus,
    StatusHistory
)
from src.collection.status_management.state_machine import InvalidStatusTransitionError


# ===================================================================
# Test Fixtures
# ===================================================================

@pytest.fixture(scope='function')
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_builder(db_session):
    """Create a sample builder for testing."""
    builder = BuilderProfile(
        name="Test Builder Inc",
        business_status=BuilderStatus.ACTIVE.value,
        is_active=True,
        last_activity_at=datetime.utcnow()
    )
    db_session.add(builder)
    db_session.commit()
    return builder


@pytest.fixture
def sample_community(db_session):
    """Create a sample community for testing."""
    community = Community(
        name="Test Community",
        city="Austin",
        state="TX",
        development_status="planning",
        availability_status="available",
        is_active=True,
        last_activity_at=datetime.utcnow()
    )
    db_session.add(community)
    db_session.commit()
    return community


@pytest.fixture
def sample_property(db_session, sample_builder, sample_community):
    """Create a sample property for testing."""
    prop = Property(
        title="Test Property",
        builder_id=sample_builder.id,
        community_id=sample_community.id,
        listing_status=PropertyListingStatus.AVAILABLE.value,
        visibility_status="visible",
        last_verified_at=datetime.utcnow()
    )
    db_session.add(prop)
    db_session.commit()
    return prop


# ===================================================================
# State Machine Tests
# ===================================================================

class TestStateMachine:
    """Test state machine validation."""

    def test_valid_builder_transition(self):
        """Test that valid builder transitions are allowed."""
        assert StatusStateMachine.can_transition_builder(
            BuilderStatus.ACTIVE,
            BuilderStatus.INACTIVE
        )

    def test_invalid_builder_transition(self):
        """Test that invalid builder transitions are rejected."""
        assert not StatusStateMachine.can_transition_builder(
            BuilderStatus.OUT_OF_BUSINESS,
            BuilderStatus.ACTIVE
        )

    def test_validate_builder_transition_raises_error(self):
        """Test that validation raises error for invalid transitions."""
        with pytest.raises(InvalidStatusTransitionError):
            StatusStateMachine.validate_builder_transition(
                BuilderStatus.OUT_OF_BUSINESS,
                BuilderStatus.ACTIVE
            )

    def test_valid_property_transition(self):
        """Test that valid property transitions are allowed."""
        assert StatusStateMachine.can_transition_property_listing(
            PropertyListingStatus.AVAILABLE,
            PropertyListingStatus.PENDING
        )

    def test_invalid_property_transition(self):
        """Test that invalid property transitions are rejected."""
        assert not StatusStateMachine.can_transition_property_listing(
            PropertyListingStatus.SOLD,
            PropertyListingStatus.AVAILABLE
        )


# ===================================================================
# Builder Status Manager Tests
# ===================================================================

class TestImprovedBuilderStatusManager:
    """Test improved builder status manager."""

    def test_update_builder_activity(self, db_session, sample_builder):
        """Test updating builder activity."""
        manager = ImprovedBuilderStatusManager(db_session)

        # Mark builder as inactive first
        sample_builder.is_active = False
        sample_builder.business_status = BuilderStatus.INACTIVE.value
        db_session.commit()

        # Update activity should reactivate
        manager.update_builder_activity(sample_builder.id)

        db_session.refresh(sample_builder)
        assert sample_builder.is_active is True
        assert sample_builder.business_status == BuilderStatus.ACTIVE.value

    def test_update_builder_status_with_validation(self, db_session, sample_builder):
        """Test updating builder status with state machine validation."""
        manager = ImprovedBuilderStatusManager(db_session)

        # Valid transition
        manager.update_builder_status(
            sample_builder.id,
            BuilderStatus.INACTIVE,
            "Testing inactivation"
        )

        db_session.refresh(sample_builder)
        assert sample_builder.business_status == BuilderStatus.INACTIVE.value
        assert sample_builder.is_active is False

    def test_invalid_transition_raises_error(self, db_session, sample_builder):
        """Test that invalid transitions raise errors."""
        manager = ImprovedBuilderStatusManager(db_session)

        # First set to OUT_OF_BUSINESS
        sample_builder.business_status = BuilderStatus.OUT_OF_BUSINESS.value
        db_session.commit()

        # Try to transition back to ACTIVE (not allowed)
        with pytest.raises(InvalidStatusTransitionError):
            manager.update_builder_status(
                sample_builder.id,
                BuilderStatus.ACTIVE,
                "Trying invalid transition"
            )

    def test_status_history_recorded(self, db_session, sample_builder):
        """Test that status changes are recorded in history."""
        manager = ImprovedBuilderStatusManager(db_session)

        # Update status
        manager.update_builder_status(
            sample_builder.id,
            BuilderStatus.INACTIVE,
            "Testing history recording"
        )

        # Check history
        history = db_session.query(StatusHistory).filter(
            StatusHistory.entity_type == 'builder',
            StatusHistory.entity_id == sample_builder.id
        ).all()

        assert len(history) >= 1
        last_change = history[-1]
        assert last_change.old_status == BuilderStatus.ACTIVE.value
        assert last_change.new_status == BuilderStatus.INACTIVE.value
        assert last_change.change_reason == "Testing history recording"


# ===================================================================
# Property Status Manager Tests
# ===================================================================

class TestImprovedPropertyStatusManager:
    """Test improved property status manager."""

    def test_update_property_status(self, db_session, sample_property):
        """Test updating property listing status."""
        manager = ImprovedPropertyStatusManager(db_session)

        manager.update_property_status(
            sample_property.id,
            PropertyListingStatus.SOLD,
            "Property sold to buyer"
        )

        db_session.refresh(sample_property)
        assert sample_property.listing_status == PropertyListingStatus.SOLD.value
        assert sample_property.visibility_status == 'archived'  # Auto-archived

    def test_property_status_history(self, db_session, sample_property):
        """Test that property status changes are recorded."""
        manager = ImprovedPropertyStatusManager(db_session)

        manager.update_property_status(
            sample_property.id,
            PropertyListingStatus.PENDING,
            "Offer received"
        )

        history = db_session.query(StatusHistory).filter(
            StatusHistory.entity_type == 'property',
            StatusHistory.entity_id == sample_property.id
        ).all()

        assert len(history) >= 1
        assert history[-1].new_status == PropertyListingStatus.PENDING.value

    def test_verify_property_listing(self, db_session, sample_property):
        """Test verifying property listing."""
        manager = ImprovedPropertyStatusManager(db_session)

        old_verified = sample_property.last_verified_at
        manager.verify_property_listing(sample_property.id)

        db_session.refresh(sample_property)
        assert sample_property.last_verified_at > old_verified


# ===================================================================
# Event System Tests
# ===================================================================

class TestEventSystem:
    """Test event publishing system."""

    def test_event_published_on_status_change(self, db_session, sample_builder):
        """Test that events are published when status changes."""
        manager = ImprovedBuilderStatusManager(db_session)
        events_received = []

        def test_handler(event):
            events_received.append(event)

        # Subscribe to events
        status_event_bus.subscribe(test_handler)

        # Change status
        manager.update_builder_status(
            sample_builder.id,
            BuilderStatus.INACTIVE,
            "Testing event publishing"
        )

        # Check event was received
        assert len(events_received) >= 1
        event = events_received[-1]
        assert event.entity_type == 'builder'
        assert event.entity_id == sample_builder.id
        assert event.new_status == BuilderStatus.INACTIVE.value

        # Cleanup
        status_event_bus.unsubscribe(test_handler)

    def test_event_contains_metadata(self, db_session, sample_builder):
        """Test that events contain metadata."""
        manager = ImprovedBuilderStatusManager(db_session)
        events_received = []

        def test_handler(event):
            events_received.append(event)

        status_event_bus.subscribe(test_handler)

        manager.update_builder_status(
            sample_builder.id,
            BuilderStatus.INACTIVE,
            "Testing metadata"
        )

        event = events_received[-1]
        assert 'builder_name' in event.metadata
        assert event.metadata['builder_name'] == sample_builder.name

        status_event_bus.unsubscribe(test_handler)


# ===================================================================
# Integration Tests
# ===================================================================

class TestIntegration:
    """Test full integration of Phase 1 features."""

    def test_complete_workflow(self, db_session, sample_builder):
        """Test complete workflow: validation, history, events."""
        manager = ImprovedBuilderStatusManager(db_session)
        events_received = []

        def test_handler(event):
            events_received.append(event)

        status_event_bus.subscribe(test_handler)

        # 1. Change status (should validate, record history, publish event)
        manager.update_builder_status(
            sample_builder.id,
            BuilderStatus.SUSPENDED,
            "Testing complete workflow"
        )

        # 2. Verify state machine validated
        db_session.refresh(sample_builder)
        assert sample_builder.business_status == BuilderStatus.SUSPENDED.value

        # 3. Verify history recorded
        history = manager.get_status_history(sample_builder.id)
        assert len(history) >= 1
        assert history[0].new_status == BuilderStatus.SUSPENDED.value

        # 4. Verify event published
        assert len(events_received) >= 1
        assert events_received[-1].new_status == BuilderStatus.SUSPENDED.value

        status_event_bus.unsubscribe(test_handler)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
