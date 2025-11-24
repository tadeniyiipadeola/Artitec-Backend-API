"""add_status_history_table

Revision ID: 931c766ea143
Revises: 40631958258f
Create Date: 2025-11-24 12:12:25.656663

Adds status_history table for audit trail and rollback capability.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '931c766ea143'
down_revision: Union[str, Sequence[str], None] = '40631958258f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'status_history',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False, comment='builder, community, property, sales_rep'),
        sa.Column('entity_id', mysql.BIGINT(unsigned=True), nullable=False, comment='ID of the entity'),
        sa.Column('status_field', sa.String(50), nullable=False, comment='Which status field changed'),
        sa.Column('old_status', sa.String(50), nullable=True, comment='Previous status value'),
        sa.Column('new_status', sa.String(50), nullable=False, comment='New status value'),
        sa.Column('change_reason', sa.String(255), nullable=True, comment='Reason for status change'),
        sa.Column('changed_by', sa.String(50), nullable=True, comment='User ID or "system"'),
        sa.Column('change_source', sa.String(50), nullable=True, comment='manual, auto, collection'),
        sa.Column('metadata', sa.JSON(), nullable=True, comment='Additional context'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    op.create_index('ix_status_history_entity', 'status_history', ['entity_type', 'entity_id'])
    op.create_index('ix_status_history_created_at', 'status_history', ['created_at'])
    op.create_index('ix_status_history_change_source', 'status_history', ['change_source'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_status_history_change_source', table_name='status_history')
    op.drop_index('ix_status_history_created_at', table_name='status_history')
    op.drop_index('ix_status_history_entity', table_name='status_history')
    op.drop_table('status_history')
