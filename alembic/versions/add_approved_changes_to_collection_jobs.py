"""add approved_changes to collection_jobs

Revision ID: add_approved_changes
Revises: 
Create Date: 2025-01-30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_approved_changes'
down_revision = '37dbfba1585a'
branch_labels = None
depends_on = None


def upgrade():
    # Add approved_changes column to collection_jobs table
    op.add_column('collection_jobs', 
        sa.Column('approved_changes', sa.Integer(), nullable=True, default=0, comment='Number of changes that have been approved')
    )
    
    # Set default value for existing rows
    op.execute('UPDATE collection_jobs SET approved_changes = 0 WHERE approved_changes IS NULL')
    
    # Make column non-nullable after setting defaults
    op.alter_column('collection_jobs', 'approved_changes',
        existing_type=sa.Integer(),
        nullable=False,
        server_default='0'
    )


def downgrade():
    op.drop_column('collection_jobs', 'approved_changes')
