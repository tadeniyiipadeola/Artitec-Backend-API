"""merge_heads

Revision ID: d607582ebeda
Revises: 2c102111fe4b, c78719d920c1
Create Date: 2025-11-24 11:23:55.451079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd607582ebeda'
down_revision: Union[str, Sequence[str], None] = ('2c102111fe4b', 'c78719d920c1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
