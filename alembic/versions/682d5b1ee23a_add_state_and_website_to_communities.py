"""add state and website to communities

Revision ID: 682d5b1ee23a
Revises: ce3f638a0c53
Create Date: 2025-11-11 18:06:58

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '682d5b1ee23a'
down_revision = 'ce3f638a0c53'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Check if state column exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'state'
    """))
    if result.scalar() == 0:
        op.add_column('communities', sa.Column('state', sa.String(length=64), nullable=True))

    # Check if community_website_url column exists
    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'community_website_url'
    """))
    if result.scalar() == 0:
        op.add_column('communities', sa.Column('community_website_url', sa.String(length=1024), nullable=True))


def downgrade():
    # Remove the added columns (check if they exist first)
    conn = op.get_bind()

    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'community_website_url'
    """))
    if result.scalar() > 0:
        op.drop_column('communities', 'community_website_url')

    result = conn.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'communities'
        AND COLUMN_NAME = 'state'
    """))
    if result.scalar() > 0:
        op.drop_column('communities', 'state')
