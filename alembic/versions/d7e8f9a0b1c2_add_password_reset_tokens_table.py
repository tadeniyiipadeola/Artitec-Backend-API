"""add_password_reset_tokens_table

Revision ID: d7e8f9a0b1c2
Revises: bc3b0a6a067f
Create Date: 2024-11-12 15:30:00.000000

Add password_reset_tokens table for forgot password functionality.
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'bc3b0a6a067f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create password_reset_tokens table."""
    print("\n🔧 Creating password_reset_tokens table...")

    conn = op.get_bind()

    # Check if table already exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'password_reset_tokens'
    """))

    table_exists = result.scalar() > 0

    if not table_exists:
        # Create password_reset_tokens table
        op.create_table(
            'password_reset_tokens',
            sa.Column('id', mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.String(50), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
            sa.Column('token', sa.String(255), nullable=False, unique=True),
            sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
            sa.Column('expires_at', sa.DateTime, nullable=False),
            sa.Column('used_at', sa.DateTime, nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            mysql_engine='InnoDB',
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci'
        )
        print("   ✓ Created password_reset_tokens table")

        # Create indexes
        op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
        print("   ✓ Added index on user_id")

        op.create_index('ix_password_reset_tokens_token', 'password_reset_tokens', ['token'])
        print("   ✓ Added index on token")

        op.create_index('ix_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])
        print("   ✓ Added index on expires_at")

        print("\n✅ Migration completed successfully")
        print("   Table: password_reset_tokens")
        print("   Columns:")
        print("     - id (BIGINT UNSIGNED, PK)")
        print("     - user_id (VARCHAR(50), FK to users.user_id)")
        print("     - token (VARCHAR(255), UNIQUE) - For URL")
        print("     - token_hash (VARCHAR(255), UNIQUE) - Hashed for security")
        print("     - expires_at (DATETIME) - Token expiration")
        print("     - used_at (DATETIME, NULLABLE) - When token was used")
        print("     - created_at (DATETIME) - Token creation time")
    else:
        print("   ℹ Table already exists, skipping creation")


def downgrade() -> None:
    """Drop password_reset_tokens table."""
    print("\n⚠️  Dropping password_reset_tokens table...")

    # Drop indexes
    op.drop_index('ix_password_reset_tokens_expires_at', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')

    # Drop table
    op.drop_table('password_reset_tokens')

    print("✅ Removed password_reset_tokens table")
