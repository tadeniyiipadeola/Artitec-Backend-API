"""add buyer profile columns

Revision ID: e8f29b3c91de
Revises: d7d18e7a74ce
Create Date: 2025-11-05 20:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8f29b3c91de'
down_revision = 'd7d18e7a74ce'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to buyer_profiles table
    op.add_column('buyer_profiles', sa.Column('household_income_usd', sa.Integer(), nullable=True))
    op.add_column('buyer_profiles', sa.Column('budget_min_usd', sa.Integer(), nullable=True))

    # Fix foreign key constraint
    # First drop the existing constraint
    op.drop_constraint('buyer_profiles_ibfk_1', 'buyer_profiles', type_='foreignkey')

    # Recreate it with the correct reference
    op.create_foreign_key(
        'buyer_profiles_ibfk_1',
        'buyer_profiles',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Remove the added columns
    op.drop_column('buyer_profiles', 'budget_min_usd')
    op.drop_column('buyer_profiles', 'household_income_usd')

    # Revert foreign key back to original (incorrect) state
    op.drop_constraint('buyer_profiles_ibfk_1', 'buyer_profiles', type_='foreignkey')
    op.create_foreign_key(
        'buyer_profiles_ibfk_1',
        'buyer_profiles',
        'users',
        ['user_id'],
        ['public_id'],
        ondelete='CASCADE'
    )
