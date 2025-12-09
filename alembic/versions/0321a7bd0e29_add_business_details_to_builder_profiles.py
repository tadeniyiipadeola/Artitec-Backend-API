"""add_business_details_to_builder_profiles

Revision ID: 0321a7bd0e29
Revises: add_approved_changes
Create Date: 2025-12-08 14:28:52.467413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0321a7bd0e29'
down_revision: Union[str, Sequence[str], None] = 'add_approved_changes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add mission column to builder_profiles table.

    Note: All other business detail columns already exist in the database:
    - founded_year, employee_count, service_areas (added in migration 3509492dffbd)
    - headquarters_address, sales_office_address (existing)
    - price_range_min, price_range_max (existing)

    Only adding: mission
    """
    # Add mission statement column
    op.add_column('builder_profiles', sa.Column('mission', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove mission column from builder_profiles table."""
    op.drop_column('builder_profiles', 'mission')
