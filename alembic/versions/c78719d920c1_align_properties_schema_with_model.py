"""align_properties_schema_with_model

Revision ID: c78719d920c1
Revises: 3c7d55e40d0f
Create Date: 2025-11-17 23:41:13.341280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c78719d920c1'
down_revision: Union[str, Sequence[str], None] = '3c7d55e40d0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Align properties table schema with Property model."""

    # Rename columns to match model (MySQL requires existing type)
    op.alter_column('properties', 'address', new_column_name='address1', existing_type=sa.String(255))
    op.alter_column('properties', 'zip_code', new_column_name='postal_code', existing_type=sa.String(20))
    op.alter_column('properties', 'square_feet', new_column_name='sqft', existing_type=sa.Integer())
    op.alter_column('properties', 'lot_size', new_column_name='lot_sqft', existing_type=sa.Integer())

    # Add missing columns
    op.add_column('properties', sa.Column('address2', sa.String(255), nullable=True))
    op.add_column('properties', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('properties', sa.Column('has_pool', sa.Boolean(), default=False, server_default='0'))
    op.add_column('properties', sa.Column('media_urls', sa.JSON(), nullable=True))
    op.add_column('properties', sa.Column('listed_at', sa.TIMESTAMP(), nullable=True))

    print("✓ Aligned properties table schema with Property model")


def downgrade() -> None:
    """Revert properties table schema changes."""

    # Drop added columns
    op.drop_column('properties', 'listed_at')
    op.drop_column('properties', 'media_urls')
    op.drop_column('properties', 'has_pool')
    op.drop_column('properties', 'longitude')
    op.drop_column('properties', 'latitude')
    op.drop_column('properties', 'address2')

    # Rename columns back (MySQL requires existing type)
    op.alter_column('properties', 'lot_sqft', new_column_name='lot_size', existing_type=sa.Integer())
    op.alter_column('properties', 'sqft', new_column_name='square_feet', existing_type=sa.Integer())
    op.alter_column('properties', 'postal_code', new_column_name='zip_code', existing_type=sa.String(20))
    op.alter_column('properties', 'address1', new_column_name='address', existing_type=sa.String(255))

    print("✓ Reverted properties table schema changes")
