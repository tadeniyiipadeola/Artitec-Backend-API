"""add_password_columns_to_users

Revision ID: 6259c90a0e16
Revises: 8f4f0cbc28a2
Create Date: 2025-11-17 23:14:04.333768

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '6259c90a0e16'
down_revision: Union[str, Sequence[str], None] = '8f4f0cbc28a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password columns to users table."""
    # Add password_hash column
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))

    # Add password_algo column
    op.add_column('users', sa.Column('password_algo',
        sa.Enum('bcrypt', name='password_algo'),
        nullable=True,
        server_default='bcrypt'
    ))

    # Add last_password_change column
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(), nullable=True))

    print("✓ Added password columns to users table")


def downgrade() -> None:
    """Remove password columns from users table."""
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'password_algo')
    op.drop_column('users', 'password_hash')

    print("✓ Removed password columns from users table")
