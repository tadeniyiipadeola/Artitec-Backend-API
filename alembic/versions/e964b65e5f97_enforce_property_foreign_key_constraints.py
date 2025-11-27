"""enforce_property_foreign_key_constraints

Revision ID: e964b65e5f97
Revises: a2b3c4d5e6f7
Create Date: 2025-11-26 16:11:01.290021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e964b65e5f97'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enforce property foreign key constraints.

    Changes:
    1. Convert builder_id from BIGINT to INTEGER (to match builder_profiles.id)
    2. Convert community_id from BIGINT to INTEGER (to match communities.id)
    3. Make both columns NOT NULL
    4. Add foreign keys with RESTRICT ondelete

    This ensures that all properties MUST have valid builder and community associations,
    and prevents accidental deletion of builders/communities that have properties.
    """
    from sqlalchemy.dialects import mysql

    # Step 1: Convert builder_id from BIGINT to INTEGER and make NOT NULL
    # This will fail if there are any NULL values or values > 2147483647
    # Database is clean (0 properties currently)
    op.alter_column('properties', 'builder_id',
                    existing_type=mysql.BIGINT(unsigned=True),
                    type_=sa.Integer(),
                    nullable=False)

    # Step 2: Convert community_id from BIGINT to INTEGER and make NOT NULL
    op.alter_column('properties', 'community_id',
                    existing_type=mysql.BIGINT(unsigned=True),
                    type_=sa.Integer(),
                    nullable=False)

    # Step 3: Create foreign keys with RESTRICT
    op.create_foreign_key(
        'fk_properties_builder',
        'properties', 'builder_profiles',
        ['builder_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_properties_community',
        'properties', 'communities',
        ['community_id'], ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """
    Revert property foreign key constraints.

    Warning: This will allow properties without builder/community associations again.
    """
    from sqlalchemy.dialects import mysql

    # Step 1: Drop RESTRICT foreign keys
    op.drop_constraint('fk_properties_builder', 'properties', type_='foreignkey')
    op.drop_constraint('fk_properties_community', 'properties', type_='foreignkey')

    # Step 2: Convert columns back to BIGINT and make nullable
    op.alter_column('properties', 'builder_id',
                    existing_type=sa.Integer(),
                    type_=mysql.BIGINT(unsigned=True),
                    nullable=True)
    op.alter_column('properties', 'community_id',
                    existing_type=sa.Integer(),
                    type_=mysql.BIGINT(unsigned=True),
                    nullable=True)
