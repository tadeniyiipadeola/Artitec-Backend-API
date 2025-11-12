"""add location fields to builder_profiles

Revision ID: 922b25005b74
Revises: 44f379a49ddf
Create Date: 2025-11-11 20:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '922b25005b74'
down_revision = '44f379a49ddf'
branch_labels = None
depends_on = None


def upgrade():
    # Add city column to builder_profiles table
    op.add_column('builder_profiles', sa.Column('city', sa.String(length=255), nullable=True))

    # Add state column to builder_profiles table
    op.add_column('builder_profiles', sa.Column('state', sa.String(length=64), nullable=True))

    # Add postal_code column to builder_profiles table
    op.add_column('builder_profiles', sa.Column('postal_code', sa.String(length=20), nullable=True))


def downgrade():
    # Remove the added columns
    op.drop_column('builder_profiles', 'postal_code')
    op.drop_column('builder_profiles', 'state')
    op.drop_column('builder_profiles', 'city')
