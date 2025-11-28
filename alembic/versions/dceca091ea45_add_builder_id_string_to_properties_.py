"""add builder_id_string to properties table

Revision ID: dceca091ea45
Revises: 9aa798ff004b
Create Date: 2025-11-27 13:24:39.809701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dceca091ea45'
down_revision: Union[str, Sequence[str], None] = '9aa798ff004b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('properties', sa.Column('builder_id_string', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('properties', 'builder_id_string')
