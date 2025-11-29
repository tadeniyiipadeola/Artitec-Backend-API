"""Add auto-apply tracking fields to collection_changes

Revision ID: b60420daff97
Revises: 92d10784beb7
Create Date: 2025-11-29 02:33:04.192887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b60420daff97'
down_revision: Union[str, Sequence[str], None] = '92d10784beb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add auto-apply tracking fields to collection_changes table."""
    # Add auto_applied column
    op.add_column('collection_changes',
        sa.Column('auto_applied', sa.Boolean(), nullable=False, server_default='0',
                  comment='Was this change automatically applied?')
    )

    # Add auto_apply_reason column
    op.add_column('collection_changes',
        sa.Column('auto_apply_reason', sa.String(length=255), nullable=True,
                  comment='Reason for auto-apply: filling_empty_field, data_quality_improvement, etc.')
    )

    # Add reverted_at column
    op.add_column('collection_changes',
        sa.Column('reverted_at', sa.TIMESTAMP(), nullable=True,
                  comment='When this auto-applied change was reverted (if ever)')
    )

    # Add reverted_by column
    op.add_column('collection_changes',
        sa.Column('reverted_by', sa.String(length=50), nullable=True,
                  comment='User ID who reverted this change')
    )


def downgrade() -> None:
    """Downgrade schema - Remove auto-apply tracking fields."""
    op.drop_column('collection_changes', 'reverted_by')
    op.drop_column('collection_changes', 'reverted_at')
    op.drop_column('collection_changes', 'auto_apply_reason')
    op.drop_column('collection_changes', 'auto_applied')
