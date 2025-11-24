"""add_data_collection_tables

Revision ID: cf81233f4514
Revises: d607582ebeda
Create Date: 2025-11-24 11:31:01.179108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'cf81233f4514'
down_revision: Union[str, Sequence[str], None] = 'd607582ebeda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create collection_jobs table
    op.create_table(
        'collection_jobs',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False, comment='builder, community, property, sales_rep'),
        sa.Column('entity_id', mysql.BIGINT(unsigned=True), nullable=True, comment='ID of target entity (null for discovery jobs)'),
        sa.Column('job_type', sa.String(50), nullable=False, comment='update, discovery, inventory'),
        sa.Column('parent_entity_type', sa.String(50), nullable=True, comment="Parent entity type (e.g., 'builder' when discovering properties)"),
        sa.Column('parent_entity_id', mysql.BIGINT(unsigned=True), nullable=True, comment='Parent entity ID'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending', comment='pending, running, completed, failed'),
        sa.Column('priority', sa.Integer(), server_default='0', comment='Higher = more urgent'),
        sa.Column('search_query', sa.Text(), nullable=True, comment="The query used for collection (e.g., 'Perry Homes Houston')"),
        sa.Column('target_url', sa.String(1024), nullable=True, comment='Specific URL to scrape (optional)'),
        sa.Column('search_filters', sa.JSON(), nullable=True, comment="JSON search filters: {location: 'Houston, TX', price_max: 500000}"),
        sa.Column('items_found', sa.Integer(), server_default='0', comment='Number of items discovered'),
        sa.Column('changes_detected', sa.Integer(), server_default='0', comment='Number of changes detected'),
        sa.Column('new_entities_found', sa.Integer(), server_default='0', comment='Number of new entities discovered (for discovery jobs)'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error details if job failed'),
        sa.Column('initiated_by', sa.String(50), nullable=True, comment='user_id who started the job'),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True, comment='When job execution began'),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True, comment='When job finished (success or failure)'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_collection_jobs_job_id', 'collection_jobs', ['job_id'], unique=True)
    op.create_index('ix_collection_jobs_entity_type', 'collection_jobs', ['entity_type'])
    op.create_index('ix_collection_jobs_entity_id', 'collection_jobs', ['entity_id'])
    op.create_index('ix_collection_jobs_job_type', 'collection_jobs', ['job_type'])
    op.create_index('ix_collection_jobs_status', 'collection_jobs', ['status'])

    # Create collection_sources table
    op.create_table(
        'collection_sources',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False, comment="Human-readable name (e.g., 'Perry Homes Official Website')"),
        sa.Column('source_url', sa.String(1024), nullable=False, comment='Base URL'),
        sa.Column('source_type', sa.String(50), nullable=False, comment='official_website, directory, mls, review_site'),
        sa.Column('entity_types', sa.JSON(), nullable=True, comment="JSON array: ['builder', 'property']"),
        sa.Column('reliability_score', sa.Float(), server_default='0.5', nullable=False, comment='0.0-1.0 (updated based on accuracy)'),
        sa.Column('total_collections', sa.Integer(), server_default='0', nullable=False, comment='Total number of collection attempts'),
        sa.Column('successful_collections', sa.Integer(), server_default='0', nullable=False, comment='Number of successful collections'),
        sa.Column('failed_collections', sa.Integer(), server_default='0', nullable=False, comment='Number of failed collections'),
        sa.Column('last_accessed', sa.TIMESTAMP(), nullable=True, comment='Last time this source was accessed'),
        sa.Column('access_count_today', sa.Integer(), server_default='0', nullable=False, comment='Number of accesses today (resets daily)'),
        sa.Column('rate_limit_per_day', sa.Integer(), server_default='100', nullable=False, comment='Maximum accesses allowed per day'),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False, comment='Can this source be used?'),
        sa.Column('blocked_until', sa.TIMESTAMP(), nullable=True, comment='Temporarily blocked until this time'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_collection_sources_source_id', 'collection_sources', ['source_id'], unique=True)
    op.create_index('ix_collection_sources_source_type', 'collection_sources', ['source_type'])
    op.create_index('ix_collection_sources_reliability_score', 'collection_sources', ['reliability_score'])

    # Create collection_changes table
    op.create_table(
        'collection_changes',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False, comment='builder, community, property, sales_rep, award, credential'),
        sa.Column('entity_id', mysql.BIGINT(unsigned=True), nullable=True, comment='ID of entity to update (null for new entities)'),
        sa.Column('is_new_entity', sa.Boolean(), server_default='0', nullable=False, comment='TRUE if this is a new entity creation'),
        sa.Column('proposed_entity_data', sa.JSON(), nullable=True, comment='Full entity data for new records (JSON)'),
        sa.Column('field_name', sa.String(100), nullable=True, comment="Field being updated (e.g., 'phone', 'rating')"),
        sa.Column('old_value', sa.Text(), nullable=True, comment='Current value in DB (JSON if complex)'),
        sa.Column('new_value', sa.Text(), nullable=True, comment='Proposed new value (JSON if complex)'),
        sa.Column('change_type', sa.String(50), nullable=False, comment='added, modified, removed'),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False, comment='pending, approved, rejected, applied'),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False, comment='0.0-1.0 confidence score'),
        sa.Column('source_url', sa.String(1024), nullable=True, comment='URL where data was found'),
        sa.Column('reviewed_by', sa.String(50), nullable=True, comment='user_id who approved/rejected'),
        sa.Column('reviewed_at', sa.TIMESTAMP(), nullable=True, comment='When change was reviewed'),
        sa.Column('review_notes', sa.Text(), nullable=True, comment='Admin notes about the change'),
        sa.Column('applied_at', sa.TIMESTAMP(), nullable=True, comment='When change was applied to database'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['collection_jobs.job_id'], ondelete='CASCADE')
    )
    op.create_index('ix_collection_changes_job_id', 'collection_changes', ['job_id'])
    op.create_index('ix_collection_changes_entity_type', 'collection_changes', ['entity_type'])
    op.create_index('ix_collection_changes_entity_id', 'collection_changes', ['entity_id'])
    op.create_index('ix_collection_changes_is_new_entity', 'collection_changes', ['is_new_entity'])
    op.create_index('ix_collection_changes_status', 'collection_changes', ['status'])

    # Create entity_matches table
    op.create_table(
        'entity_matches',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('discovered_entity_type', sa.String(50), nullable=False, comment='builder, community, property'),
        sa.Column('discovered_name', sa.String(255), nullable=False, comment='Name found during collection'),
        sa.Column('discovered_location', sa.String(255), nullable=True, comment="Location context (e.g., 'Houston, TX')"),
        sa.Column('discovered_data', sa.JSON(), nullable=True, comment='Full collected data (JSON)'),
        sa.Column('matched_entity_type', sa.String(50), nullable=True, comment='Same as discovered_entity_type'),
        sa.Column('matched_entity_id', mysql.BIGINT(unsigned=True), nullable=True, comment='ID in respective table'),
        sa.Column('match_confidence', sa.Float(), nullable=True, comment='0.0-1.0 confidence score (1.0 = exact match)'),
        sa.Column('match_status', sa.String(50), server_default='pending', nullable=False, comment='pending, confirmed, rejected, merged'),
        sa.Column('matched_by', sa.String(50), nullable=True, comment="'auto' or user_id who confirmed match"),
        sa.Column('match_method', sa.String(50), nullable=True, comment='name_exact, name_fuzzy, website_match, manual'),
        sa.Column('match_notes', sa.Text(), nullable=True, comment='Notes about the match'),
        sa.Column('job_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['collection_jobs.job_id'], ondelete='SET NULL')
    )
    op.create_index('ix_entity_matches_discovered_entity_type', 'entity_matches', ['discovered_entity_type'])
    op.create_index('ix_entity_matches_discovered_name', 'entity_matches', ['discovered_name'])
    op.create_index('ix_entity_matches_matched_entity_id', 'entity_matches', ['matched_entity_id'])
    op.create_index('ix_entity_matches_match_status', 'entity_matches', ['match_status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_entity_matches_match_status', table_name='entity_matches')
    op.drop_index('ix_entity_matches_matched_entity_id', table_name='entity_matches')
    op.drop_index('ix_entity_matches_discovered_name', table_name='entity_matches')
    op.drop_index('ix_entity_matches_discovered_entity_type', table_name='entity_matches')
    op.drop_table('entity_matches')

    op.drop_index('ix_collection_changes_status', table_name='collection_changes')
    op.drop_index('ix_collection_changes_is_new_entity', table_name='collection_changes')
    op.drop_index('ix_collection_changes_entity_id', table_name='collection_changes')
    op.drop_index('ix_collection_changes_entity_type', table_name='collection_changes')
    op.drop_index('ix_collection_changes_job_id', table_name='collection_changes')
    op.drop_table('collection_changes')

    op.drop_index('ix_collection_sources_reliability_score', table_name='collection_sources')
    op.drop_index('ix_collection_sources_source_type', table_name='collection_sources')
    op.drop_index('ix_collection_sources_source_id', table_name='collection_sources')
    op.drop_table('collection_sources')

    op.drop_index('ix_collection_jobs_status', table_name='collection_jobs')
    op.drop_index('ix_collection_jobs_job_type', table_name='collection_jobs')
    op.drop_index('ix_collection_jobs_entity_id', table_name='collection_jobs')
    op.drop_index('ix_collection_jobs_entity_type', table_name='collection_jobs')
    op.drop_index('ix_collection_jobs_job_id', table_name='collection_jobs')
    op.drop_table('collection_jobs')
