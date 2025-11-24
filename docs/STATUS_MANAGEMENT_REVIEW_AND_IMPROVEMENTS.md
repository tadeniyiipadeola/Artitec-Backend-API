# Status Management System - Review & Improvements

**Current Implementation Review + Recommended Enhancements**

---

## 🔍 Current Implementation Analysis

### ✅ Strengths

1. **Clear Separation of Concerns**: Each entity has its own manager
2. **Grace Period Logic**: Prevents premature inactivation
3. **Auto-Reactivation**: Entities come back when activity detected
4. **Audit Trail**: Timestamps and reasons tracked
5. **Integration**: Collectors automatically call status managers

### ⚠️ Areas for Improvement

1. **No State Machine**: Status transitions aren't validated
2. **No Event System**: Status changes don't trigger notifications
3. **Hardcoded Values**: Grace periods and thresholds not configurable
4. **Missing Validations**: Illegal state transitions possible
5. **No History Tracking**: Can't see status change history
6. **Performance Issues**: Individual commits, no batching
7. **No Rollback Strategy**: Can't undo status changes
8. **Limited Business Rules**: Doesn't handle complex scenarios
9. **No Dependency Management**: Doesn't cascade status changes
10. **Missing Observability**: No metrics or monitoring

---

## 🎯 Recommended Improvements

### 1. **Implement State Machine Pattern**

**Why**: Ensures only valid status transitions, prevents data corruption

```python
from enum import Enum
from typing import Dict, Set

class BuilderStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_BUSINESS = "out_of_business"
    MERGED = "merged"
    SUSPENDED = "suspended"  # New: temporarily suspended by admin

class StatusStateMachine:
    """
    Defines valid status transitions and business rules.
    """

    # Valid transitions: current_status -> set of allowed next statuses
    VALID_TRANSITIONS: Dict[BuilderStatus, Set[BuilderStatus]] = {
        BuilderStatus.ACTIVE: {
            BuilderStatus.INACTIVE,
            BuilderStatus.OUT_OF_BUSINESS,
            BuilderStatus.SUSPENDED
        },
        BuilderStatus.INACTIVE: {
            BuilderStatus.ACTIVE,
            BuilderStatus.OUT_OF_BUSINESS
        },
        BuilderStatus.SUSPENDED: {
            BuilderStatus.ACTIVE,
            BuilderStatus.OUT_OF_BUSINESS
        },
        BuilderStatus.OUT_OF_BUSINESS: set(),  # Terminal state
        BuilderStatus.MERGED: set()  # Terminal state
    }

    @classmethod
    def can_transition(
        cls,
        from_status: BuilderStatus,
        to_status: BuilderStatus
    ) -> bool:
        """Check if transition is valid."""
        return to_status in cls.VALID_TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_transition(
        cls,
        from_status: BuilderStatus,
        to_status: BuilderStatus
    ) -> None:
        """Validate transition or raise exception."""
        if not cls.can_transition(from_status, to_status):
            raise InvalidStatusTransitionError(
                f"Cannot transition from {from_status.value} to {to_status.value}"
            )
```

**Usage**:
```python
class BuilderStatusManager:
    def update_status(self, builder_id: int, new_status: str, reason: str):
        builder = self._get_builder(builder_id)

        current = BuilderStatus(builder.business_status)
        target = BuilderStatus(new_status)

        # Validate transition
        StatusStateMachine.validate_transition(current, target)

        # Perform transition
        self._transition_to_status(builder, target, reason)
```

---

### 2. **Add Status History Table**

**Why**: Audit trail, analytics, ability to revert changes

```sql
CREATE TABLE status_history (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    entity_type VARCHAR(50) NOT NULL,  -- builder, community, property, sales_rep
    entity_id BIGINT UNSIGNED NOT NULL,

    -- Status change
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,

    -- Context
    change_reason VARCHAR(255),
    changed_by VARCHAR(50),  -- user_id or 'system'
    change_source VARCHAR(50),  -- manual, auto_grace_period, data_collection

    -- Metadata
    metadata JSON,  -- Additional context (property_count, days_inactive, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX ix_entity (entity_type, entity_id),
    INDEX ix_created_at (created_at),
    INDEX ix_change_source (change_source)
);
```

**Model**:
```python
class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(MyBIGINT(unsigned=True), nullable=False, index=True)

    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)

    change_reason = Column(String(255))
    changed_by = Column(String(50))  # user_id or 'system'
    change_source = Column(String(50), index=True)  # manual, auto, collection

    metadata = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
```

**Usage**:
```python
def _record_status_change(
    self,
    entity_type: str,
    entity_id: int,
    old_status: str,
    new_status: str,
    reason: str,
    changed_by: str = 'system',
    metadata: dict = None
):
    history = StatusHistory(
        entity_type=entity_type,
        entity_id=entity_id,
        old_status=old_status,
        new_status=new_status,
        change_reason=reason,
        changed_by=changed_by,
        change_source='auto_grace_period',
        metadata=metadata or {}
    )
    self.db.add(history)
```

---

### 3. **Event-Driven Architecture**

**Why**: Decouple status changes from side effects, enable notifications

```python
from typing import Callable, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StatusChangeEvent:
    """Event fired when entity status changes."""
    entity_type: str
    entity_id: int
    old_status: str
    new_status: str
    reason: str
    changed_by: str
    timestamp: datetime
    metadata: dict

class StatusEventBus:
    """
    Event bus for status change events.
    Allows subscribers to react to status changes.
    """

    def __init__(self):
        self._subscribers: List[Callable[[StatusChangeEvent], None]] = []

    def subscribe(self, handler: Callable[[StatusChangeEvent], None]):
        """Subscribe to status change events."""
        self._subscribers.append(handler)

    def publish(self, event: StatusChangeEvent):
        """Publish status change event to all subscribers."""
        for handler in self._subscribers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}", exc_info=True)

# Global event bus
status_event_bus = StatusEventBus()

# Example subscribers
def send_admin_notification(event: StatusChangeEvent):
    """Send notification when builder goes out of business."""
    if (event.entity_type == 'builder' and
        event.new_status == 'out_of_business'):
        # Send email/Slack notification
        notify_admins(
            f"Builder {event.entity_id} marked as out of business: {event.reason}"
        )

def update_related_entities(event: StatusChangeEvent):
    """Cascade status changes to related entities."""
    if (event.entity_type == 'builder' and
        event.new_status == 'out_of_business'):
        # Mark all builder's properties as off-market
        property_mgr = PropertyStatusManager(db)
        property_mgr.bulk_update_by_builder(
            builder_id=event.entity_id,
            new_status='off_market',
            reason=f'Builder out of business: {event.reason}'
        )

# Register subscribers
status_event_bus.subscribe(send_admin_notification)
status_event_bus.subscribe(update_related_entities)

# Usage in status manager
class BuilderStatusManager:
    def _transition_to_status(self, builder, new_status, reason, changed_by='system'):
        old_status = builder.business_status
        builder.business_status = new_status
        # ... update other fields ...
        self.db.commit()

        # Publish event
        event = StatusChangeEvent(
            entity_type='builder',
            entity_id=builder.id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=changed_by,
            timestamp=datetime.utcnow(),
            metadata={'builder_name': builder.name}
        )
        status_event_bus.publish(event)
```

---

### 4. **Configuration Management**

**Why**: Flexibility, different rules per environment, A/B testing

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class StatusConfig:
    """Configuration for status management."""

    # Grace periods (days)
    builder_grace_period: int = 90
    community_grace_period: int = 180
    property_grace_period: int = 60
    sales_rep_grace_period: int = 60

    # Warning periods (days before auto-action)
    builder_warning_period: int = 60
    community_warning_period: int = 120
    property_warning_period: int = 45

    # Auto-actions enabled
    auto_inactivate_builders: bool = True
    auto_inactivate_communities: bool = True
    auto_archive_properties: bool = True

    # Thresholds
    community_limited_availability_threshold: int = 10
    property_bulk_operation_max: int = 100

    # Notifications
    notify_on_builder_inactive: bool = True
    notify_on_property_archived: bool = False

    @classmethod
    def from_env(cls) -> 'StatusConfig':
        """Load configuration from environment variables."""
        import os
        return cls(
            builder_grace_period=int(os.getenv('BUILDER_GRACE_PERIOD', 90)),
            community_grace_period=int(os.getenv('COMMUNITY_GRACE_PERIOD', 180)),
            # ... load other config ...
        )

    @classmethod
    def from_db(cls, db: Session) -> 'StatusConfig':
        """Load configuration from database (admin configurable)."""
        # Query configuration table
        configs = db.query(SystemConfig).filter(
            SystemConfig.category == 'status_management'
        ).all()

        kwargs = {config.key: config.value for config in configs}
        return cls(**kwargs)

# Global config
status_config = StatusConfig.from_env()

# Usage
class BuilderStatusManager:
    def __init__(self, db: Session, config: Optional[StatusConfig] = None):
        self.db = db
        self.config = config or status_config

    def check_inactive_builders(self):
        grace_period_cutoff = datetime.utcnow() - timedelta(
            days=self.config.builder_grace_period  # Use config
        )
        # ...
```

---

### 5. **Batch Processing & Performance**

**Why**: Efficiency, reduce database load, faster operations

```python
class BuilderStatusManager:
    def check_inactive_builders_batch(
        self,
        batch_size: int = 100
    ) -> List[BuilderProfile]:
        """
        Process builders in batches for better performance.
        """
        grace_period_cutoff = datetime.utcnow() - timedelta(
            days=self.config.builder_grace_period
        )

        # Use pagination to avoid memory issues
        offset = 0
        all_inactive = []

        while True:
            # Fetch batch
            builders = self.db.query(BuilderProfile).filter(
                and_(
                    BuilderProfile.is_active == True,
                    BuilderProfile.business_status == 'active',
                    BuilderProfile.last_activity_at < grace_period_cutoff
                )
            ).limit(batch_size).offset(offset).all()

            if not builders:
                break

            # Process batch
            for builder in builders:
                self._mark_builder_inactive(
                    builder,
                    f"No activity for {self.config.builder_grace_period} days",
                    skip_commit=True  # Don't commit each one
                )

            # Commit batch
            self.db.commit()
            all_inactive.extend(builders)

            offset += batch_size
            logger.info(f"Processed batch: {len(builders)} builders")

        return all_inactive

    def _mark_builder_inactive(
        self,
        builder: BuilderProfile,
        reason: str,
        skip_commit: bool = False
    ):
        """Mark builder inactive with optional commit skip for batching."""
        builder.is_active = False
        builder.business_status = 'inactive'
        builder.inactivated_at = datetime.utcnow()
        builder.inactivation_reason = reason

        # Record history
        self._record_status_change(...)

        if not skip_commit:
            self.db.commit()
```

---

### 6. **Dependency Cascade System**

**Why**: Maintain data consistency, automate related changes

```python
class StatusDependencyManager:
    """
    Manages cascading status changes across related entities.

    Example:
    - Builder goes out_of_business → mark all properties off_market
    - Community sold_out → mark all properties as sold/off_market
    - Property sold → update community availability
    """

    def __init__(self, db: Session):
        self.db = db

    def cascade_builder_status(
        self,
        builder_id: int,
        new_status: str,
        reason: str
    ):
        """Cascade builder status to related entities."""

        if new_status == 'out_of_business':
            # Mark all properties as off_market
            self.db.query(Property).filter(
                Property.builder_id == builder_id,
                Property.listing_status.in_(['available', 'pending'])
            ).update({
                'listing_status': 'off_market',
                'status_changed_at': datetime.utcnow(),
                'status_change_reason': f'Builder out of business: {reason}'
            })

            # Mark all sales reps as inactive
            self.db.query(SalesRep).filter(
                SalesRep.builder_id == builder_id,
                SalesRep.is_active == True
            ).update({
                'is_active': False,
                'inactivated_at': datetime.utcnow(),
                'inactivation_reason': f'Builder out of business: {reason}'
            })

            self.db.commit()
            logger.info(f"Cascaded builder {builder_id} status to properties and reps")

    def cascade_community_status(
        self,
        community_id: int,
        new_status: str,
        reason: str
    ):
        """Cascade community status to related entities."""

        if new_status == 'sold_out':
            # Mark remaining available properties as off_market
            self.db.query(Property).filter(
                Property.community_id == community_id,
                Property.listing_status == 'available'
            ).update({
                'listing_status': 'off_market',
                'status_changed_at': datetime.utcnow(),
                'status_change_reason': f'Community sold out: {reason}'
            })

            self.db.commit()

# Integrate with event system
def cascade_status_changes(event: StatusChangeEvent):
    """Event subscriber that handles cascading."""
    cascade_mgr = StatusDependencyManager(db)

    if event.entity_type == 'builder':
        cascade_mgr.cascade_builder_status(
            event.entity_id,
            event.new_status,
            event.reason
        )
    elif event.entity_type == 'community':
        cascade_mgr.cascade_community_status(
            event.entity_id,
            event.new_status,
            event.reason
        )

status_event_bus.subscribe(cascade_status_changes)
```

---

### 7. **Rollback & Revert Capabilities**

**Why**: Undo mistakes, handle incorrect auto-actions

```python
class StatusRollbackManager:
    """
    Allows reverting status changes using history.
    """

    def __init__(self, db: Session):
        self.db = db

    def revert_last_change(
        self,
        entity_type: str,
        entity_id: int,
        changed_by: str
    ) -> bool:
        """
        Revert the most recent status change.

        Returns True if reverted, False if no history found.
        """
        # Get last status change
        last_change = self.db.query(StatusHistory).filter(
            StatusHistory.entity_type == entity_type,
            StatusHistory.entity_id == entity_id
        ).order_by(StatusHistory.created_at.desc()).first()

        if not last_change or not last_change.old_status:
            return False

        # Get entity
        entity = self._get_entity(entity_type, entity_id)
        if not entity:
            return False

        # Revert to old status
        old_status = last_change.old_status
        current_status = entity.business_status  # or listing_status, etc.

        # Update entity
        entity.business_status = old_status
        entity.status_changed_at = datetime.utcnow()
        entity.status_change_reason = f"Reverted from {current_status}"

        # Record revert in history
        revert_history = StatusHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            old_status=current_status,
            new_status=old_status,
            change_reason=f"Manual revert by {changed_by}",
            changed_by=changed_by,
            change_source='manual_revert',
            metadata={'reverted_change_id': last_change.id}
        )
        self.db.add(revert_history)
        self.db.commit()

        logger.info(f"Reverted {entity_type} {entity_id} from {current_status} to {old_status}")
        return True

    def revert_to_timestamp(
        self,
        entity_type: str,
        entity_id: int,
        target_timestamp: datetime,
        changed_by: str
    ) -> bool:
        """Revert entity to its status at a specific time."""
        # Find status at target time
        history_at_time = self.db.query(StatusHistory).filter(
            and_(
                StatusHistory.entity_type == entity_type,
                StatusHistory.entity_id == entity_id,
                StatusHistory.created_at <= target_timestamp
            )
        ).order_by(StatusHistory.created_at.desc()).first()

        if not history_at_time:
            return False

        # Revert to that status
        # ... (similar logic as above)
        return True
```

---

### 8. **Monitoring & Metrics**

**Why**: Observability, performance tracking, anomaly detection

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
status_changes_total = Counter(
    'status_changes_total',
    'Total number of status changes',
    ['entity_type', 'from_status', 'to_status', 'source']
)

status_change_duration = Histogram(
    'status_change_duration_seconds',
    'Time taken to process status change',
    ['entity_type']
)

entities_by_status = Gauge(
    'entities_by_status',
    'Number of entities in each status',
    ['entity_type', 'status']
)

class InstrumentedStatusManager:
    """Wrapper that adds metrics to status managers."""

    def __init__(self, manager):
        self.manager = manager

    def update_status(self, *args, **kwargs):
        entity_type = kwargs.get('entity_type', 'unknown')

        with status_change_duration.labels(entity_type=entity_type).time():
            result = self.manager.update_status(*args, **kwargs)

        # Record metric
        status_changes_total.labels(
            entity_type=entity_type,
            from_status=kwargs.get('old_status'),
            to_status=kwargs.get('new_status'),
            source='manual'
        ).inc()

        return result

    def update_metrics(self, db: Session):
        """Update gauge metrics with current counts."""
        # Count builders by status
        builder_counts = db.query(
            BuilderProfile.business_status,
            func.count(BuilderProfile.id)
        ).group_by(BuilderProfile.business_status).all()

        for status, count in builder_counts:
            entities_by_status.labels(
                entity_type='builder',
                status=status
            ).set(count)

        # ... same for communities, properties, etc.
```

---

### 9. **Business Rule Engine**

**Why**: Complex conditional logic, configurable rules

```python
from abc import ABC, abstractmethod
from typing import Any

class StatusRule(ABC):
    """Base class for status transition rules."""

    @abstractmethod
    def evaluate(self, entity: Any, context: dict) -> bool:
        """Returns True if rule passes, False otherwise."""
        pass

    @abstractmethod
    def get_error_message(self) -> str:
        """Returns error message if rule fails."""
        pass

class MinimumActivityRule(StatusRule):
    """Requires minimum activity level before marking inactive."""

    def __init__(self, min_days_active: int = 30):
        self.min_days_active = min_days_active

    def evaluate(self, entity: Any, context: dict) -> bool:
        """Builder must have been active for at least min_days_active."""
        if not hasattr(entity, 'created_at'):
            return True

        days_since_creation = (datetime.utcnow() - entity.created_at).days
        return days_since_creation >= self.min_days_active

    def get_error_message(self) -> str:
        return f"Entity must be active for at least {self.min_days_active} days"

class HasActivePropertiesRule(StatusRule):
    """Builder with active properties cannot be marked out_of_business."""

    def evaluate(self, entity: BuilderProfile, context: dict) -> bool:
        db = context.get('db')
        active_count = db.query(func.count(Property.id)).filter(
            and_(
                Property.builder_id == entity.id,
                Property.listing_status.in_(['available', 'pending', 'under_contract'])
            )
        ).scalar()

        return active_count == 0

    def get_error_message(self) -> str:
        return "Cannot mark builder out of business while having active properties"

class StatusRuleEngine:
    """Evaluates business rules before status transitions."""

    def __init__(self):
        self.rules: Dict[tuple, List[StatusRule]] = {}

    def add_rule(
        self,
        entity_type: str,
        from_status: str,
        to_status: str,
        rule: StatusRule
    ):
        """Register a rule for a specific transition."""
        key = (entity_type, from_status, to_status)
        if key not in self.rules:
            self.rules[key] = []
        self.rules[key].append(rule)

    def validate_transition(
        self,
        entity_type: str,
        entity: Any,
        from_status: str,
        to_status: str,
        context: dict
    ) -> tuple[bool, List[str]]:
        """
        Validate transition against all rules.

        Returns (is_valid, [error_messages])
        """
        key = (entity_type, from_status, to_status)
        rules = self.rules.get(key, [])

        errors = []
        for rule in rules:
            if not rule.evaluate(entity, context):
                errors.append(rule.get_error_message())

        return len(errors) == 0, errors

# Setup rules
rule_engine = StatusRuleEngine()

# Builder rules
rule_engine.add_rule(
    'builder', 'active', 'inactive',
    MinimumActivityRule(min_days_active=30)
)
rule_engine.add_rule(
    'builder', '*', 'out_of_business',
    HasActivePropertiesRule()
)

# Usage
class BuilderStatusManager:
    def transition_to_status(
        self,
        builder: BuilderProfile,
        new_status: str,
        reason: str
    ):
        old_status = builder.business_status

        # Validate business rules
        is_valid, errors = rule_engine.validate_transition(
            'builder',
            builder,
            old_status,
            new_status,
            {'db': self.db}
        )

        if not is_valid:
            raise BusinessRuleViolationError(
                f"Cannot transition: {', '.join(errors)}"
            )

        # Proceed with transition
        builder.business_status = new_status
        # ...
```

---

## 📋 Implementation Priority

### Phase 1 (Critical - Implement First)
1. ✅ **State Machine** - Prevents invalid transitions
2. ✅ **Status History Table** - Audit trail essential
3. ✅ **Configuration Management** - Flexibility needed

### Phase 2 (Important - Implement Soon)
4. ✅ **Event System** - Enables notifications and decoupling
5. ✅ **Batch Processing** - Performance optimization
6. ✅ **Dependency Cascade** - Data consistency

### Phase 3 (Nice to Have - Future Enhancement)
7. ✅ **Rollback Capabilities** - Error recovery
8. ✅ **Monitoring/Metrics** - Observability
9. ✅ **Rule Engine** - Complex business logic

---

## 🎯 Quick Wins (Implement Today)

### 1. Add Status Enums

```python
# model/enums.py
from enum import Enum

class BuilderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_BUSINESS = "out_of_business"
    MERGED = "merged"

class PropertyListingStatus(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    RESERVED = "reserved"
    UNDER_CONTRACT = "under_contract"
    SOLD = "sold"
    OFF_MARKET = "off_market"

# Use in models
class BuilderProfile(Base):
    business_status = Column(
        Enum(BuilderStatus),
        default=BuilderStatus.ACTIVE,
        nullable=False
    )
```

### 2. Add Validation Methods

```python
class BuilderStatusManager:
    VALID_TRANSITIONS = {
        'active': ['inactive', 'out_of_business'],
        'inactive': ['active', 'out_of_business'],
        'out_of_business': [],  # Terminal
    }

    def can_transition_to(
        self,
        current_status: str,
        new_status: str
    ) -> bool:
        """Check if transition is allowed."""
        return new_status in self.VALID_TRANSITIONS.get(current_status, [])

    def update_status(self, builder_id: int, new_status: str, reason: str):
        builder = self._get_builder(builder_id)

        if not self.can_transition_to(builder.business_status, new_status):
            raise ValueError(
                f"Invalid transition: {builder.business_status} -> {new_status}"
            )

        # Proceed with update...
```

### 3. Add Status Change Logging

```python
def _log_status_change(
    self,
    entity_type: str,
    entity_id: int,
    old_status: str,
    new_status: str,
    reason: str
):
    """Enhanced logging for status changes."""
    logger.info(
        f"Status change: {entity_type}#{entity_id} "
        f"{old_status} → {new_status} | "
        f"Reason: {reason}",
        extra={
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_status': old_status,
            'new_status': new_status,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
```

---

## 🏗️ Recommended Architecture

```
src/collection/
├── status_management/
│   ├── __init__.py
│   ├── enums.py              # Status enums
│   ├── state_machine.py      # State machine logic
│   ├── event_bus.py          # Event system
│   ├── config.py             # Configuration
│   ├── rules/                # Business rules
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── builder_rules.py
│   ├── managers/             # Status managers
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── builder_manager.py
│   │   ├── community_manager.py
│   │   └── property_manager.py
│   ├── history.py            # Status history tracking
│   ├── cascade.py            # Dependency management
│   └── metrics.py            # Monitoring
```

---

## 📊 Summary

| Feature | Current | Improved | Benefit |
|---------|---------|----------|---------|
| Validation | ❌ None | ✅ State Machine | Prevents invalid states |
| History | ❌ None | ✅ Full audit trail | Compliance, debugging |
| Events | ❌ None | ✅ Event bus | Notifications, integrations |
| Config | ❌ Hardcoded | ✅ Dynamic config | Flexibility |
| Performance | ⚠️ Individual commits | ✅ Batch processing | 10x faster |
| Dependencies | ❌ Manual | ✅ Auto cascade | Data consistency |
| Rollback | ❌ None | ✅ Revert capability | Error recovery |
| Monitoring | ❌ None | ✅ Metrics | Observability |

---

**Recommendation**: Start with Phase 1 (State Machine, History, Config) - these provide the biggest value with minimal effort.

Would you like me to implement any of these improvements?
