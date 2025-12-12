"""add_price_range_to_communities

Revision ID: acb68f5c5a7e
Revises: b2ff23c923a8
Create Date: 2025-12-10 23:26:47.040409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acb68f5c5a7e'
down_revision: Union[str, Sequence[str], None] = 'b2ff23c923a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add price_range_min column
    op.add_column('communities',
                  sa.Column('price_range_min', sa.Integer(), nullable=True, comment='Minimum home price in community'))

    # Add price_range_max column
    op.add_column('communities',
                  sa.Column('price_range_max', sa.Integer(), nullable=True, comment='Maximum home price in community'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove price range columns
    op.drop_column('communities', 'price_range_max')
    op.drop_column('communities', 'price_range_min')
