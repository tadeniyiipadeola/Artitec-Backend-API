"""add_phase_lot_management_tables

Revision ID: 0191c4bc21e0
Revises: acb68f5c5a7e
Create Date: 2025-12-20 18:49:12.000000

Adds comprehensive lot management support to community phases:
- Extends community_phases with phase map image metadata
- Creates lots table for detailed lot tracking
- Creates lot_status_history for audit trail
- Integrates with phase map digitizer features
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import BIGINT, DECIMAL, ENUM


# revision identifiers, used by Alembic.
revision: str = '0191c4bc21e0'
down_revision: Union[str, Sequence[str], None] = 'acb68f5c5a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support phase map digitization and lot management."""

    # ========== EXTEND COMMUNITY_PHASES TABLE ==========
    # Add phase map image metadata fields
    op.add_column('community_phases',
                  sa.Column('description', sa.Text(), nullable=True, comment='Phase description'))

    op.add_column('community_phases',
                  sa.Column('status',
                           ENUM('planning', 'active', 'completed', 'on_hold', name='phase_status_enum'),
                           nullable=True,
                           server_default='planning',
                           comment='Current phase status'))

    op.add_column('community_phases',
                  sa.Column('site_plan_image_url', sa.String(1024), nullable=True,
                           comment='URL to site plan image in MinIO'))

    op.add_column('community_phases',
                  sa.Column('original_file_path', sa.String(1024), nullable=True,
                           comment='Original uploaded file path in storage'))

    op.add_column('community_phases',
                  sa.Column('processed_image_path', sa.String(1024), nullable=True,
                           comment='Processed image path (AI-enhanced)'))

    op.add_column('community_phases',
                  sa.Column('file_type', sa.String(10), nullable=True,
                           comment='File type (jpg, png, pdf, etc.)'))

    op.add_column('community_phases',
                  sa.Column('image_width', sa.Integer(), nullable=True,
                           comment='Image width in pixels'))

    op.add_column('community_phases',
                  sa.Column('image_height', sa.Integer(), nullable=True,
                           comment='Image height in pixels'))

    op.add_column('community_phases',
                  sa.Column('start_date', sa.Date(), nullable=True,
                           comment='Phase start date'))

    op.add_column('community_phases',
                  sa.Column('target_completion_date', sa.Date(), nullable=True,
                           comment='Target completion date'))

    op.add_column('community_phases',
                  sa.Column('actual_completion_date', sa.Date(), nullable=True,
                           comment='Actual completion date'))

    op.add_column('community_phases',
                  sa.Column('total_lots', sa.Integer(), nullable=True, server_default='0',
                           comment='Total number of lots in phase'))

    # ========== CREATE LOTS TABLE ==========
    op.create_table(
        'lots',

        # Primary Key
        sa.Column('id', BIGINT(unsigned=True), primary_key=True, autoincrement=True),

        # Foreign Keys
        sa.Column('phase_id', BIGINT(unsigned=True), nullable=False, index=True,
                 comment='References community_phases.id'),
        sa.Column('community_id', sa.String(64), nullable=False, index=True,
                 comment='References communities.community_id (CMY-xxx)'),
        sa.Column('builder_id', sa.String(64), nullable=True, index=True,
                 comment='References builder_profiles.builder_id (BLD-xxx)'),
        sa.Column('property_id', BIGINT(unsigned=True), nullable=True, index=True,
                 comment='References properties.id if lot has property'),

        # Lot Identification
        sa.Column('lot_number', sa.String(50), nullable=False,
                 comment='Lot number (e.g., "101", "A-5")'),

        # Status & Availability
        sa.Column('status',
                 ENUM('available', 'reserved', 'sold', 'unavailable', 'on_hold', name='lot_status_enum'),
                 nullable=False,
                 server_default='available',
                 comment='Current lot status'),

        # Geometry & Location
        sa.Column('boundary_coordinates', sa.JSON(), nullable=True,
                 comment='Polygon boundary as array of {x, y} coordinates'),

        # Property Details
        sa.Column('square_footage', sa.Integer(), nullable=True,
                 comment='Lot size in square feet'),
        sa.Column('price', DECIMAL(12, 2), nullable=True,
                 comment='Lot price or estimated home price'),
        sa.Column('bedrooms', sa.Integer(), nullable=True,
                 comment='Number of bedrooms'),
        sa.Column('bathrooms', DECIMAL(3, 1), nullable=True,
                 comment='Number of bathrooms (e.g., 2.5)'),
        sa.Column('stories', sa.Integer(), nullable=True,
                 comment='Number of stories'),
        sa.Column('garage_spaces', sa.Integer(), nullable=True,
                 comment='Number of garage spaces'),
        sa.Column('model', sa.String(100), nullable=True,
                 comment='Home model name'),

        # Reservation & Sales Info
        sa.Column('reserved_by', sa.String(255), nullable=True,
                 comment='Name of person who reserved lot'),
        sa.Column('reserved_at', sa.TIMESTAMP(), nullable=True,
                 comment='When lot was reserved'),
        sa.Column('sold_to', sa.String(255), nullable=True,
                 comment='Name of buyer'),
        sa.Column('sold_at', sa.TIMESTAMP(), nullable=True,
                 comment='When lot was sold'),
        sa.Column('move_in_date', sa.Date(), nullable=True,
                 comment='Expected move-in date'),

        # Notes & Metadata
        sa.Column('notes', sa.Text(), nullable=True,
                 comment='Additional notes about the lot'),
        sa.Column('detection_method', sa.String(50), nullable=True,
                 comment='How lot was detected: manual, yolo, line_detection'),
        sa.Column('detection_confidence', DECIMAL(5, 4), nullable=True,
                 comment='AI detection confidence score (0.0-1.0)'),

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.current_timestamp(),
                 nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(),
                 server_default=sa.func.current_timestamp(),
                 onupdate=sa.func.current_timestamp(),
                 nullable=False),

        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['phase_id'], ['community_phases.id'],
                               name='fk_lots_phase_id',
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['community_id'], ['communities.community_id'],
                               name='fk_lots_community_id',
                               ondelete='CASCADE'),

        # Unique Constraints
        sa.UniqueConstraint('phase_id', 'lot_number', name='uq_phase_lot_number'),

        # Indexes
        sa.Index('idx_lots_status', 'status'),
        sa.Index('idx_lots_builder', 'builder_id'),
        sa.Index('idx_lots_price', 'price'),
    )

    # ========== CREATE LOT_STATUS_HISTORY TABLE ==========
    op.create_table(
        'lot_status_history',

        # Primary Key
        sa.Column('id', BIGINT(unsigned=True), primary_key=True, autoincrement=True),

        # Foreign Keys
        sa.Column('lot_id', BIGINT(unsigned=True), nullable=False, index=True,
                 comment='References lots.id'),

        # Status Change Info
        sa.Column('old_status',
                 ENUM('available', 'reserved', 'sold', 'unavailable', 'on_hold', name='lot_status_enum'),
                 nullable=True,
                 comment='Previous status'),
        sa.Column('new_status',
                 ENUM('available', 'reserved', 'sold', 'unavailable', 'on_hold', name='lot_status_enum'),
                 nullable=False,
                 comment='New status'),

        # Metadata
        sa.Column('changed_by', sa.String(255), nullable=True,
                 comment='User who made the change'),
        sa.Column('change_reason', sa.Text(), nullable=True,
                 comment='Reason for status change'),
        sa.Column('changed_at', sa.TIMESTAMP(),
                 server_default=sa.func.current_timestamp(),
                 nullable=False,
                 comment='When status changed'),

        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['lot_id'], ['lots.id'],
                               name='fk_lot_status_history_lot_id',
                               ondelete='CASCADE'),

        # Indexes
        sa.Index('idx_lot_status_history_lot_id', 'lot_id'),
        sa.Index('idx_lot_status_history_changed_at', 'changed_at'),
    )


def downgrade() -> None:
    """Downgrade schema - remove lot management support."""

    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('lot_status_history')
    op.drop_table('lots')

    # Drop ENUMs
    op.execute("DROP TYPE IF EXISTS lot_status_enum")
    op.execute("DROP TYPE IF EXISTS phase_status_enum")

    # Remove columns from community_phases
    op.drop_column('community_phases', 'total_lots')
    op.drop_column('community_phases', 'actual_completion_date')
    op.drop_column('community_phases', 'target_completion_date')
    op.drop_column('community_phases', 'start_date')
    op.drop_column('community_phases', 'image_height')
    op.drop_column('community_phases', 'image_width')
    op.drop_column('community_phases', 'file_type')
    op.drop_column('community_phases', 'processed_image_path')
    op.drop_column('community_phases', 'original_file_path')
    op.drop_column('community_phases', 'site_plan_image_url')
    op.drop_column('community_phases', 'status')
    op.drop_column('community_phases', 'description')
