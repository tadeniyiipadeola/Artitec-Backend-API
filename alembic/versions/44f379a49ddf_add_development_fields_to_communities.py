"""add development fields to communities

Revision ID: 44f379a49ddf
Revises: 682d5b1ee23a
Create Date: 2025-11-11 19:50:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '44f379a49ddf'
down_revision = '682d5b1ee23a'
branch_labels = None
depends_on = None


def upgrade():
    # Add development_stage column to communities table
    op.add_column('communities', sa.Column('development_stage', sa.String(length=64), nullable=True))

    # Add enterprise_number_hoa column to communities table
    op.add_column('communities', sa.Column('enterprise_number_hoa', sa.String(length=255), nullable=True))


def downgrade():
    # Remove the added columns
    op.drop_column('communities', 'enterprise_number_hoa')
    op.drop_column('communities', 'development_stage')
