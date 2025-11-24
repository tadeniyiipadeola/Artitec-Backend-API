"""add_collection_tracking_columns

Revision ID: 3509492dffbd
Revises: cf81233f4514
Create Date: 2025-11-24 11:32:57.129147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3509492dffbd'
down_revision: Union[str, Sequence[str], None] = 'cf81233f4514'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tracking columns to sales_reps
    op.add_column('sales_reps', sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False, comment='Is this sales rep currently active?'))
    op.add_column('sales_reps', sa.Column('last_seen_at', sa.TIMESTAMP(), nullable=True, comment='Last time rep was seen in data collection'))
    op.add_column('sales_reps', sa.Column('inactivated_at', sa.TIMESTAMP(), nullable=True, comment='When rep was marked inactive'))
    op.add_column('sales_reps', sa.Column('inactivation_reason', sa.String(255), nullable=True, comment='Why rep was inactivated'))
    op.add_column('sales_reps', sa.Column('data_source', sa.String(50), server_default='manual', nullable=False, comment='Source of data: manual, collected, imported'))
    op.add_column('sales_reps', sa.Column('last_data_sync', sa.TIMESTAMP(), nullable=True, comment='Last successful data collection'))

    # Add tracking columns to builder_profiles
    op.add_column('builder_profiles', sa.Column('founded_year', sa.Integer(), nullable=True, comment='Year builder was founded'))
    op.add_column('builder_profiles', sa.Column('employee_count', sa.Integer(), nullable=True, comment='Number of employees'))
    op.add_column('builder_profiles', sa.Column('service_areas', sa.JSON(), nullable=True, comment='JSON array of service areas'))
    op.add_column('builder_profiles', sa.Column('review_count', sa.Integer(), server_default='0', nullable=False, comment='Total number of reviews'))
    op.add_column('builder_profiles', sa.Column('last_data_sync', sa.TIMESTAMP(), nullable=True, comment='Last successful data collection'))
    op.add_column('builder_profiles', sa.Column('data_source', sa.String(50), server_default='manual', nullable=False, comment='Source of data'))
    op.add_column('builder_profiles', sa.Column('data_confidence', sa.Float(), server_default='1.0', nullable=False, comment='Confidence score for collected data'))

    # Add tracking columns to communities
    op.add_column('communities', sa.Column('school_district', sa.String(255), nullable=True, comment='School district name'))
    op.add_column('communities', sa.Column('hoa_management_company', sa.String(255), nullable=True, comment='HOA management company'))
    op.add_column('communities', sa.Column('hoa_contact_phone', sa.String(20), nullable=True, comment='HOA contact phone'))
    op.add_column('communities', sa.Column('hoa_contact_email', sa.String(255), nullable=True, comment='HOA contact email'))
    op.add_column('communities', sa.Column('last_data_sync', sa.TIMESTAMP(), nullable=True, comment='Last successful data collection'))
    op.add_column('communities', sa.Column('data_source', sa.String(50), server_default='manual', nullable=False, comment='Source of data'))
    op.add_column('communities', sa.Column('data_confidence', sa.Float(), server_default='1.0', nullable=False, comment='Confidence score'))

    # Add Phase 1 property columns (20 fields from ENHANCED_PROPERTY_SCHEMA.md)
    op.add_column('properties', sa.Column('property_type', sa.String(50), nullable=True, comment='single_family, townhome, condo, etc.'))
    op.add_column('properties', sa.Column('stories', sa.Integer(), nullable=True, comment='Number of stories'))
    op.add_column('properties', sa.Column('garage_spaces', sa.Integer(), nullable=True, comment='Number of garage spaces'))
    op.add_column('properties', sa.Column('corner_lot', sa.Boolean(), server_default='0', nullable=False, comment='Is this a corner lot?'))
    op.add_column('properties', sa.Column('cul_de_sac', sa.Boolean(), server_default='0', nullable=False, comment='Is this on a cul-de-sac?'))
    op.add_column('properties', sa.Column('lot_backing', sa.String(100), nullable=True, comment='What lot backs to: greenbelt, pond, street, etc.'))
    op.add_column('properties', sa.Column('school_district', sa.String(255), nullable=True, comment='School district'))
    op.add_column('properties', sa.Column('elementary_school', sa.String(255), nullable=True, comment='Elementary school name'))
    op.add_column('properties', sa.Column('middle_school', sa.String(255), nullable=True, comment='Middle school name'))
    op.add_column('properties', sa.Column('high_school', sa.String(255), nullable=True, comment='High school name'))
    op.add_column('properties', sa.Column('school_ratings', sa.JSON(), nullable=True, comment='JSON object with school ratings'))
    op.add_column('properties', sa.Column('price_per_sqft', sa.Float(), nullable=True, comment='Price per square foot'))
    op.add_column('properties', sa.Column('days_on_market', sa.Integer(), nullable=True, comment='Number of days listed'))
    op.add_column('properties', sa.Column('model_home', sa.Boolean(), server_default='0', nullable=False, comment='Is this a model home?'))
    op.add_column('properties', sa.Column('quick_move_in', sa.Boolean(), server_default='0', nullable=False, comment='Quick move-in ready?'))
    op.add_column('properties', sa.Column('construction_stage', sa.String(50), nullable=True, comment='pre_construction, under_construction, completed'))
    op.add_column('properties', sa.Column('estimated_completion', sa.Date(), nullable=True, comment='Estimated completion date'))
    op.add_column('properties', sa.Column('builder_incentives', sa.Text(), nullable=True, comment='Current builder incentives'))
    op.add_column('properties', sa.Column('upgrades_included', sa.Text(), nullable=True, comment='Included upgrades description'))
    op.add_column('properties', sa.Column('upgrades_value', sa.Float(), nullable=True, comment='Estimated value of upgrades'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove property columns (in reverse order)
    op.drop_column('properties', 'upgrades_value')
    op.drop_column('properties', 'upgrades_included')
    op.drop_column('properties', 'builder_incentives')
    op.drop_column('properties', 'estimated_completion')
    op.drop_column('properties', 'construction_stage')
    op.drop_column('properties', 'quick_move_in')
    op.drop_column('properties', 'model_home')
    op.drop_column('properties', 'days_on_market')
    op.drop_column('properties', 'price_per_sqft')
    op.drop_column('properties', 'school_ratings')
    op.drop_column('properties', 'high_school')
    op.drop_column('properties', 'middle_school')
    op.drop_column('properties', 'elementary_school')
    op.drop_column('properties', 'school_district')
    op.drop_column('properties', 'lot_backing')
    op.drop_column('properties', 'cul_de_sac')
    op.drop_column('properties', 'corner_lot')
    op.drop_column('properties', 'garage_spaces')
    op.drop_column('properties', 'stories')
    op.drop_column('properties', 'property_type')

    # Remove community columns
    op.drop_column('communities', 'data_confidence')
    op.drop_column('communities', 'data_source')
    op.drop_column('communities', 'last_data_sync')
    op.drop_column('communities', 'hoa_contact_email')
    op.drop_column('communities', 'hoa_contact_phone')
    op.drop_column('communities', 'hoa_management_company')
    op.drop_column('communities', 'school_district')

    # Remove builder_profiles columns
    op.drop_column('builder_profiles', 'data_confidence')
    op.drop_column('builder_profiles', 'data_source')
    op.drop_column('builder_profiles', 'last_data_sync')
    op.drop_column('builder_profiles', 'review_count')
    op.drop_column('builder_profiles', 'service_areas')
    op.drop_column('builder_profiles', 'employee_count')
    op.drop_column('builder_profiles', 'founded_year')

    # Remove sales_reps columns
    op.drop_column('sales_reps', 'last_data_sync')
    op.drop_column('sales_reps', 'data_source')
    op.drop_column('sales_reps', 'inactivation_reason')
    op.drop_column('sales_reps', 'inactivated_at')
    op.drop_column('sales_reps', 'last_seen_at')
    op.drop_column('sales_reps', 'is_active')
