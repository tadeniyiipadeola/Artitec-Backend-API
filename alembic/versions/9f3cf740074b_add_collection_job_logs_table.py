"""add_collection_job_logs_table

Revision ID: 9f3cf740074b
Revises: 931c766ea143
Create Date: 2025-11-25 18:40:09.405398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '9f3cf740074b'
down_revision: Union[str, Sequence[str], None] = '931c766ea143'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add collection_job_logs table."""
    op.create_table(
        'collection_job_logs',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('level', sa.String(20), nullable=False, server_default='INFO',
                  comment="DEBUG, INFO, SUCCESS, WARNING, ERROR"),
        sa.Column('message', sa.Text(), nullable=False, comment="Log message"),
        sa.Column('log_data', sa.JSON(), nullable=True,
                  comment="Additional structured data (counts, URLs, etc.)"),
        sa.Column('stage', sa.String(50), nullable=True,
                  comment="Collection stage: searching, parsing, matching, saving, etc."),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['collection_jobs.job_id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # Add indexes for efficient querying
    op.create_index('ix_collection_job_logs_job_id', 'collection_job_logs', ['job_id'])
    op.create_index('ix_collection_job_logs_timestamp', 'collection_job_logs', ['timestamp'])


def downgrade() -> None:
    """Downgrade schema - remove collection_job_logs table."""
    op.drop_index('ix_collection_job_logs_timestamp', table_name='collection_job_logs')
    op.drop_index('ix_collection_job_logs_job_id', table_name='collection_job_logs')
    op.drop_table('collection_job_logs')
