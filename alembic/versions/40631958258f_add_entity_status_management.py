"""add_entity_status_management

Revision ID: 40631958258f
Revises: 3509492dffbd
Create Date: 2025-11-24 12:00:00.000000

Adds status management columns to builder_profiles, communities, and properties
for tracking entity lifecycle and visibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40631958258f'
down_revision: Union[str, Sequence[str], None] = '3509492dffbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ===================================================================
    # BUILDER STATUS TRACKING
    # ===================================================================
    # Tracks builder business status (active, inactive, out_of_business)

    op.add_column('builder_profiles', sa.Column(
        'is_active',
        sa.Boolean(),
        server_default='1',
        nullable=False,
        comment='Is this builder currently active/in business?'
    ))

    op.add_column('builder_profiles', sa.Column(
        'business_status',
        sa.String(50),
        server_default='active',
        nullable=False,
        comment='active, inactive, out_of_business, merged'
    ))

    op.add_column('builder_profiles', sa.Column(
        'last_activity_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='Last time builder was seen in data collection or had active listings'
    ))

    op.add_column('builder_profiles', sa.Column(
        'inactivated_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='When builder was marked as inactive'
    ))

    op.add_column('builder_profiles', sa.Column(
        'inactivation_reason',
        sa.String(255),
        nullable=True,
        comment='Why builder was inactivated (no_listings, out_of_business, etc.)'
    ))

    # ===================================================================
    # COMMUNITY STATUS TRACKING
    # ===================================================================
    # Tracks community development status and availability

    op.add_column('communities', sa.Column(
        'is_active',
        sa.Boolean(),
        server_default='1',
        nullable=False,
        comment='Is this community currently active?'
    ))

    op.add_column('communities', sa.Column(
        'development_status',
        sa.String(50),
        server_default='active',
        nullable=False,
        comment='planned, under_development, active, sold_out, inactive'
    ))

    op.add_column('communities', sa.Column(
        'availability_status',
        sa.String(50),
        server_default='available',
        nullable=False,
        comment='available, limited_availability, sold_out, closed'
    ))

    op.add_column('communities', sa.Column(
        'last_activity_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='Last time community had activity (new listings, updates, etc.)'
    ))

    op.add_column('communities', sa.Column(
        'status_changed_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='When status last changed'
    ))

    op.add_column('communities', sa.Column(
        'status_change_reason',
        sa.String(255),
        nullable=True,
        comment='Reason for status change'
    ))

    # ===================================================================
    # PROPERTY STATUS TRACKING
    # ===================================================================
    # Tracks property listing status and construction stage

    op.add_column('properties', sa.Column(
        'listing_status',
        sa.String(50),
        server_default='available',
        nullable=False,
        comment='available, pending, reserved, under_contract, sold, off_market'
    ))

    op.add_column('properties', sa.Column(
        'visibility_status',
        sa.String(50),
        server_default='public',
        nullable=False,
        comment='public, private, hidden, archived'
    ))

    op.add_column('properties', sa.Column(
        'last_verified_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='Last time property listing was verified as accurate'
    ))

    op.add_column('properties', sa.Column(
        'status_changed_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='When listing status last changed'
    ))

    op.add_column('properties', sa.Column(
        'status_change_reason',
        sa.String(255),
        nullable=True,
        comment='Reason for status change (sold, price_change, etc.)'
    ))

    op.add_column('properties', sa.Column(
        'auto_archive_at',
        sa.TIMESTAMP(),
        nullable=True,
        comment='Automatic archival date for stale listings'
    ))

    # Add index for common queries
    op.create_index('ix_builder_profiles_business_status', 'builder_profiles', ['business_status'])
    op.create_index('ix_builder_profiles_is_active', 'builder_profiles', ['is_active'])
    op.create_index('ix_communities_development_status', 'communities', ['development_status'])
    op.create_index('ix_communities_availability_status', 'communities', ['availability_status'])
    op.create_index('ix_communities_is_active', 'communities', ['is_active'])
    op.create_index('ix_properties_listing_status', 'properties', ['listing_status'])
    op.create_index('ix_properties_visibility_status', 'properties', ['visibility_status'])


def downgrade() -> None:
    """Downgrade schema."""

    # Drop property status columns
    op.drop_index('ix_properties_visibility_status', table_name='properties')
    op.drop_index('ix_properties_listing_status', table_name='properties')
    op.drop_column('properties', 'auto_archive_at')
    op.drop_column('properties', 'status_change_reason')
    op.drop_column('properties', 'status_changed_at')
    op.drop_column('properties', 'last_verified_at')
    op.drop_column('properties', 'visibility_status')
    op.drop_column('properties', 'listing_status')

    # Drop community status columns
    op.drop_index('ix_communities_is_active', table_name='communities')
    op.drop_index('ix_communities_availability_status', table_name='communities')
    op.drop_index('ix_communities_development_status', table_name='communities')
    op.drop_column('communities', 'status_change_reason')
    op.drop_column('communities', 'status_changed_at')
    op.drop_column('communities', 'last_activity_at')
    op.drop_column('communities', 'availability_status')
    op.drop_column('communities', 'development_status')
    op.drop_column('communities', 'is_active')

    # Drop builder status columns
    op.drop_index('ix_builder_profiles_is_active', table_name='builder_profiles')
    op.drop_index('ix_builder_profiles_business_status', table_name='builder_profiles')
    op.drop_column('builder_profiles', 'inactivation_reason')
    op.drop_column('builder_profiles', 'inactivated_at')
    op.drop_column('builder_profiles', 'last_activity_at')
    op.drop_column('builder_profiles', 'business_status')
    op.drop_column('builder_profiles', 'is_active')
