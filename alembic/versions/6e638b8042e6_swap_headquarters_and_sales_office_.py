"""swap_headquarters_and_sales_office_address_columns

Revision ID: 6e638b8042e6
Revises: 278091178ff8
Create Date: 2025-11-29 23:04:22.791891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e638b8042e6'
down_revision: Union[str, Sequence[str], None] = '278091178ff8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Swap headquarters_address and sales_office_address columns
    # Step 1: Rename headquarters_address to temp column
    op.alter_column('builder_profiles', 'headquarters_address',
                    new_column_name='temp_headquarters_address',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)

    # Step 2: Rename sales_office_address to headquarters_address
    op.alter_column('builder_profiles', 'sales_office_address',
                    new_column_name='headquarters_address',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)

    # Step 3: Rename temp column to sales_office_address
    op.alter_column('builder_profiles', 'temp_headquarters_address',
                    new_column_name='sales_office_address',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the swap: swap back headquarters_address and sales_office_address
    # Step 1: Rename headquarters_address to temp column
    op.alter_column('builder_profiles', 'headquarters_address',
                    new_column_name='temp_headquarters_address',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)

    # Step 2: Rename sales_office_address to headquarters_address
    op.alter_column('builder_profiles', 'sales_office_address',
                    new_column_name='headquarters_address',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)

    # Step 3: Rename temp column to sales_office_address
    op.alter_column('builder_profiles', 'temp_headquarters_address',
                    new_column_name='sales_office_address',
                    existing_type=sa.String(length=255),
                    existing_nullable=True)
