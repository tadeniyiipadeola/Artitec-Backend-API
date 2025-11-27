"""add_missing_property_columns_manual

Revision ID: e5bff7628465
Revises: e964b65e5f97
Create Date: 2025-11-26 16:51:22.940237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5bff7628465'
down_revision: Union[str, Sequence[str], None] = 'e964b65e5f97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ALL missing property columns needed for property inventory collection."""
    # Add missing columns - all columns from Property model that don't exist in DB
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS views VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS builder_plan_name VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS builder_series VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS elevation_options VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS flooring_types VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS countertop_materials VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS appliances VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS game_room BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS study_office BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS bonus_rooms VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS pool_type VARCHAR(64)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS covered_patio BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS outdoor_kitchen BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS landscaping VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS hoa_fee_monthly DECIMAL(10,2)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS pet_restrictions VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS lease_allowed BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS energy_rating VARCHAR(64)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS internet_providers VARCHAR(255)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS annual_property_tax DECIMAL(12,2)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS assumable_loan BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS virtual_tour_url VARCHAR(1024)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS floor_plan_url VARCHAR(1024)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS matterport_link VARCHAR(1024)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS move_in_date VARCHAR(64)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS showing_instructions TEXT")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS source_url VARCHAR(1024)")
    op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS data_confidence FLOAT")


def downgrade() -> None:
    """Remove added columns."""
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS data_confidence")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS source_url")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS builder_series")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS builder_plan_name")
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS views")
