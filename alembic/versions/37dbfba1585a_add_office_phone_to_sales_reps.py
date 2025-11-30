"""add_office_phone_to_sales_reps

Revision ID: 37dbfba1585a
Revises: 856b7e419241
Create Date: 2025-11-30 00:33:49.116269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37dbfba1585a'
down_revision: Union[str, Sequence[str], None] = '856b7e419241'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add office_phone column to sales_reps table
    op.add_column('sales_reps', sa.Column('office_phone', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove office_phone column from sales_reps table
    op.drop_column('sales_reps', 'office_phone')
