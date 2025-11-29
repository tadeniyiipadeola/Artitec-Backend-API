"""add_community_contact_schools_hoa_fields

Revision ID: 92d10784beb7
Revises: 27692efbbd06
Create Date: 2025-11-28 18:03:23.222871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92d10784beb7'
down_revision: Union[str, Sequence[str], None] = '27692efbbd06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add contact, schools, and developer fields that are missing."""
    # Contact information (phone and email for community, not admin)
    op.add_column('communities', sa.Column('phone', sa.String(32), nullable=True))
    op.add_column('communities', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('communities', sa.Column('sales_office_address', sa.String(512), nullable=True))

    # School information (elementary, middle, high - district already exists)
    op.add_column('communities', sa.Column('elementary_school', sa.String(255), nullable=True))
    op.add_column('communities', sa.Column('middle_school', sa.String(255), nullable=True))
    op.add_column('communities', sa.Column('high_school', sa.String(255), nullable=True))

    # Developer information
    op.add_column('communities', sa.Column('developer_name', sa.String(255), nullable=True))

    # Review/rating information
    op.add_column('communities', sa.Column('rating', sa.DECIMAL(3, 2), nullable=True))
    op.add_column('communities', sa.Column('review_count', sa.Integer, nullable=True, server_default='0'))


def downgrade() -> None:
    """Downgrade schema - Remove the added fields."""
    op.drop_column('communities', 'review_count')
    op.drop_column('communities', 'rating')
    op.drop_column('communities', 'developer_name')
    op.drop_column('communities', 'high_school')
    op.drop_column('communities', 'middle_school')
    op.drop_column('communities', 'elementary_school')
    op.drop_column('communities', 'sales_office_address')
    op.drop_column('communities', 'email')
    op.drop_column('communities', 'phone')
