"""add_owner_id_to_properties

Revision ID: 3c7d55e40d0f
Revises: c6fcbdad0549
Create Date: 2025-11-17 23:35:25.951213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '3c7d55e40d0f'
down_revision: Union[str, Sequence[str], None] = 'c6fcbdad0549'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add owner_id column to properties table."""
    op.add_column('properties', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_properties_owner_id', 'properties', 'users', ['owner_id'], ['id'], ondelete='SET NULL')
    print("✓ Added owner_id column to properties table")


def downgrade() -> None:
    """Remove owner_id column from properties table."""
    op.drop_constraint('fk_properties_owner_id', 'properties', type_='foreignkey')
    op.drop_column('properties', 'owner_id')
    print("✓ Removed owner_id column from properties table")
