# model/collection.py
"""
SQLAlchemy models for Data Collection system.

Tracks collection jobs, detected changes, entity matches, and data sources.
"""
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean,
    TIMESTAMP, JSON, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.mysql import BIGINT as MyBIGINT
from sqlalchemy.sql import func
from model.base import Base
import uuid
import time


# ===================================================================
# Helper Functions
# ===================================================================

def generate_job_id() -> str:
    """Generate unique job ID: JOB-1732473600-ABC123"""
    timestamp = int(time.time())
    random_suffix = uuid.uuid4().hex[:6].upper()
    return f"JOB-{timestamp}-{random_suffix}"


def generate_source_id() -> str:
    """Generate unique source ID: SRC-1732473600-XYZ789"""
    timestamp = int(time.time())
    random_suffix = uuid.uuid4().hex[:6].upper()
    return f"SRC-{timestamp}-{random_suffix}"


# ===================================================================
# CollectionJobLog Model
# ===================================================================

class CollectionJobLog(Base):
    """
    Stores detailed execution logs for collection jobs.

    Each log entry represents a single event during job execution.
    Logs are displayed in the admin UI for debugging and monitoring.
    """
    __tablename__ = "collection_job_logs"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey('collection_jobs.job_id', ondelete='CASCADE'),
                    nullable=False, index=True)

    # Log entry details
    timestamp = Column(TIMESTAMP, nullable=False, default=func.now(), index=True)
    level = Column(
        String(20), nullable=False, default='INFO',
        comment="DEBUG, INFO, SUCCESS, WARNING, ERROR"
    )
    message = Column(Text, nullable=False, comment="Log message")

    # Optional structured data
    log_data = Column(JSON, nullable=True, comment="Additional structured data (counts, URLs, etc.)")

    # For tracking progress through stages
    stage = Column(
        String(50), nullable=True,
        comment="Collection stage: searching, parsing, matching, saving, etc."
    )


# ===================================================================
# CollectionJob Model
# ===================================================================

class CollectionJob(Base):
    """
    Tracks data collection operations.

    Each job represents a single collection run for an entity (builder, community, property).
    Jobs can cascade: Community job → creates Builder jobs → creates Property jobs.
    """
    __tablename__ = "collection_jobs"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True, default=generate_job_id)

    # Target entity
    entity_type = Column(
        String(50), nullable=False, index=True,
        comment="builder, community, property, sales_rep"
    )
    entity_id = Column(
        MyBIGINT(unsigned=True), nullable=True, index=True,
        comment="ID of target entity (null for discovery jobs)"
    )
    job_type = Column(
        String(50), nullable=False, index=True,
        comment="update, discovery, inventory"
    )

    # For cascading jobs (e.g., Builder → Property discovery)
    parent_entity_type = Column(
        String(50), nullable=True,
        comment="Parent entity type (e.g., 'builder' when discovering properties)"
    )
    parent_entity_id = Column(
        MyBIGINT(unsigned=True), nullable=True,
        comment="Parent entity ID"
    )

    # Status
    status = Column(
        String(50), nullable=False, default='pending', index=True,
        comment="pending, running, completed, failed"
    )
    priority = Column(
        Integer, default=0,
        comment="Higher = more urgent"
    )

    # Search parameters
    search_query = Column(
        Text, nullable=True,
        comment="The query used for collection (e.g., 'Perry Homes Houston')"
    )
    target_url = Column(
        String(1024), nullable=True,
        comment="Specific URL to scrape (optional)"
    )
    search_filters = Column(
        JSON, nullable=True,
        comment="JSON search filters: {location: 'Houston, TX', price_max: 500000}"
    )

    # Results
    items_found = Column(
        Integer, default=0,
        comment="Number of items discovered"
    )
    changes_detected = Column(
        Integer, default=0,
        comment="Number of changes detected"
    )
    new_entities_found = Column(
        Integer, default=0,
        comment="Number of new entities discovered (for discovery jobs)"
    )
    error_message = Column(
        Text, nullable=True,
        comment="Error details if job failed"
    )

    # Metadata
    initiated_by = Column(
        String(50), nullable=True,
        comment="user_id who started the job"
    )
    started_at = Column(
        TIMESTAMP, nullable=True,
        comment="When job execution began"
    )
    completed_at = Column(
        TIMESTAMP, nullable=True,
        comment="When job finished (success or failure)"
    )

    # Audit
    created_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    def __repr__(self):
        return f"<CollectionJob(job_id='{self.job_id}', entity_type='{self.entity_type}', status='{self.status}')>"


# ===================================================================
# CollectionChange Model
# ===================================================================

class CollectionChange(Base):
    """
    Stores detected changes before applying.

    Admin reviews and approves/rejects changes before they're applied to the database.
    Supports both updates to existing entities and creation of new entities.
    """
    __tablename__ = "collection_changes"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    job_id = Column(
        String(50),
        ForeignKey("collection_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Target entity
    entity_type = Column(
        String(50), nullable=False, index=True,
        comment="builder, community, property, sales_rep, award, credential"
    )
    entity_id = Column(
        MyBIGINT(unsigned=True), nullable=True, index=True,
        comment="ID of entity to update (null for new entities)"
    )

    # For new entities
    is_new_entity = Column(
        Boolean, default=False, nullable=False, index=True,
        comment="TRUE if this is a new entity creation"
    )
    proposed_entity_data = Column(
        JSON, nullable=True,
        comment="Full entity data for new records (JSON)"
    )

    # For updates to existing entities
    field_name = Column(
        String(100), nullable=True,
        comment="Field being updated (e.g., 'phone', 'rating')"
    )
    old_value = Column(
        Text, nullable=True,
        comment="Current value in DB (JSON if complex)"
    )
    new_value = Column(
        Text, nullable=True,
        comment="Proposed new value (JSON if complex)"
    )
    change_type = Column(
        String(50), nullable=False,
        comment="added, modified, removed"
    )

    # Review
    status = Column(
        String(50), nullable=False, default='pending', index=True,
        comment="pending, approved, rejected, applied"
    )
    confidence = Column(
        Float, default=1.0, nullable=False,
        comment="0.0-1.0 confidence score"
    )
    source_url = Column(
        String(1024), nullable=True,
        comment="URL where data was found"
    )
    reviewed_by = Column(
        String(50), nullable=True,
        comment="user_id who approved/rejected"
    )
    reviewed_at = Column(
        TIMESTAMP, nullable=True,
        comment="When change was reviewed"
    )
    review_notes = Column(
        Text, nullable=True,
        comment="Admin notes about the change"
    )

    # Auto-apply tracking
    auto_applied = Column(
        Boolean, default=False, nullable=False,
        comment="Was this change automatically applied?"
    )
    auto_apply_reason = Column(
        String(255), nullable=True,
        comment="Reason for auto-apply: filling_empty_field, data_quality_improvement, etc."
    )
    reverted_at = Column(
        TIMESTAMP, nullable=True,
        comment="When this auto-applied change was reverted (if ever)"
    )
    reverted_by = Column(
        String(50), nullable=True,
        comment="User ID who reverted this change"
    )

    # Application
    applied_at = Column(
        TIMESTAMP, nullable=True,
        comment="When change was applied to database"
    )

    # Audit
    created_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )

    def __repr__(self):
        if self.is_new_entity:
            return f"<CollectionChange(entity_type='{self.entity_type}', new_entity, status='{self.status}')>"
        return f"<CollectionChange(entity_type='{self.entity_type}', field='{self.field_name}', status='{self.status}')>"


# ===================================================================
# EntityMatch Model
# ===================================================================

class EntityMatch(Base):
    """
    Links discovered entities to existing database records.

    When collecting data, we need to match discovered entities (e.g., "Perry Homes")
    to existing database records. This table stores match proposals for admin review.
    """
    __tablename__ = "entity_matches"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)

    # Discovered entity (from collection)
    discovered_entity_type = Column(
        String(50), nullable=False, index=True,
        comment="builder, community, property"
    )
    discovered_name = Column(
        String(255), nullable=False, index=True,
        comment="Name found during collection"
    )
    discovered_location = Column(
        String(255), nullable=True,
        comment="Location context (e.g., 'Houston, TX')"
    )
    discovered_data = Column(
        JSON, nullable=True,
        comment="Full collected data (JSON)"
    )

    # Matched existing entity
    matched_entity_type = Column(
        String(50), nullable=True,
        comment="Same as discovered_entity_type"
    )
    matched_entity_id = Column(
        MyBIGINT(unsigned=True), nullable=True, index=True,
        comment="ID in respective table"
    )
    match_confidence = Column(
        Float, nullable=True,
        comment="0.0-1.0 confidence score (1.0 = exact match)"
    )
    match_status = Column(
        String(50), default='pending', nullable=False, index=True,
        comment="pending, confirmed, rejected, merged"
    )

    # Matching metadata
    matched_by = Column(
        String(50), nullable=True,
        comment="'auto' or user_id who confirmed match"
    )
    match_method = Column(
        String(50), nullable=True,
        comment="name_exact, name_fuzzy, website_match, manual"
    )
    match_notes = Column(
        Text, nullable=True,
        comment="Notes about the match"
    )

    # Job reference
    job_id = Column(
        String(50),
        ForeignKey("collection_jobs.job_id", ondelete="SET NULL"),
        nullable=True
    )

    # Audit
    created_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    def __repr__(self):
        return f"<EntityMatch(discovered='{self.discovered_name}', matched_id={self.matched_entity_id}, status='{self.match_status}')>"


# ===================================================================
# CollectionSource Model
# ===================================================================

class CollectionSource(Base):
    """
    Tracks data sources and their reliability.

    Maintains a registry of websites/APIs we collect from, tracks success rates,
    and manages rate limiting.
    """
    __tablename__ = "collection_sources"

    id = Column(MyBIGINT(unsigned=True), primary_key=True, autoincrement=True)
    source_id = Column(
        String(50), unique=True, nullable=False, index=True, default=generate_source_id
    )

    # Source info
    source_name = Column(
        String(255), nullable=False,
        comment="Human-readable name (e.g., 'Perry Homes Official Website')"
    )
    source_url = Column(
        String(1024), nullable=False,
        comment="Base URL"
    )
    source_type = Column(
        String(50), nullable=False, index=True,
        comment="official_website, directory, mls, review_site"
    )

    # Applicable entities
    entity_types = Column(
        JSON, nullable=True,
        comment="JSON array: ['builder', 'property']"
    )

    # Reliability metrics
    reliability_score = Column(
        Float, default=0.5, nullable=False, index=True,
        comment="0.0-1.0 (updated based on accuracy)"
    )
    total_collections = Column(
        Integer, default=0, nullable=False,
        comment="Total number of collection attempts"
    )
    successful_collections = Column(
        Integer, default=0, nullable=False,
        comment="Number of successful collections"
    )
    failed_collections = Column(
        Integer, default=0, nullable=False,
        comment="Number of failed collections"
    )

    # Rate limiting
    last_accessed = Column(
        TIMESTAMP, nullable=True,
        comment="Last time this source was accessed"
    )
    access_count_today = Column(
        Integer, default=0, nullable=False,
        comment="Number of accesses today (resets daily)"
    )
    rate_limit_per_day = Column(
        Integer, default=100, nullable=False,
        comment="Maximum accesses allowed per day"
    )

    # Status
    is_active = Column(
        Boolean, default=True, nullable=False,
        comment="Can this source be used?"
    )
    blocked_until = Column(
        TIMESTAMP, nullable=True,
        comment="Temporarily blocked until this time"
    )

    # Audit
    created_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    updated_at = Column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

    def __repr__(self):
        return f"<CollectionSource(name='{self.source_name}', type='{self.source_type}', reliability={self.reliability_score})>"
