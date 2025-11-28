"""add approval metadata to properties table

Revision ID: 27692efbbd06
Revises: 83f5218a2ce1
Create Date: 2025-11-27 13:38:17.885207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27692efbbd06'
down_revision: Union[str, Sequence[str], None] = '83f5218a2ce1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add approval metadata fields to properties table
    op.add_column('properties', sa.Column('approved_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('properties', sa.Column('approved_by_user_id', sa.Integer(), nullable=True))

    # Add foreign key constraint for approved_by_user_id
    op.create_foreign_key(
        'fk_properties_approved_by_user_id',
        'properties',
        'users',
        ['approved_by_user_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint first
    op.drop_constraint('fk_properties_approved_by_user_id', 'properties', type_='foreignkey')

    # Drop columns
    op.drop_column('properties', 'approved_by_user_id')
    op.drop_column('properties', 'approved_at')
