"""create_enterprise_tables

Revision ID: c6fcbdad0549
Revises: ac5a8543bc9a
Create Date: 2025-11-17 23:31:00.876100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'c6fcbdad0549'
down_revision: Union[str, Sequence[str], None] = 'ac5a8543bc9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create enterprise_invitations and builder_team_members tables."""

    # Create enterprise_invitations table
    op.create_table(
        'enterprise_invitations',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, primary_key=True),
        sa.Column('invitation_code', sa.String(64), nullable=False),
        sa.Column('builder_id', sa.String(50), nullable=False),
        sa.Column('invited_email', sa.String(255), nullable=False),
        sa.Column('invited_role', sa.Enum('builder', 'salesrep', 'manager', 'viewer', name='invited_role_enum'), nullable=False, server_default='builder'),
        sa.Column('invited_first_name', sa.String(120)),
        sa.Column('invited_last_name', sa.String(120)),
        sa.Column('created_by_user_id', sa.String(50)),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP()),
        sa.Column('used_by_user_id', sa.String(50)),
        sa.Column('status', sa.Enum('pending', 'used', 'expired', 'revoked', name='invitation_status_enum'), nullable=False, server_default='pending'),
        sa.Column('custom_message', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(['builder_id'], ['builder_profiles.builder_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['used_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.UniqueConstraint('invitation_code')
    )

    # Create indexes for enterprise_invitations
    op.create_index('ix_enterprise_invitations_invitation_code', 'enterprise_invitations', ['invitation_code'])
    op.create_index('ix_enterprise_invitations_builder_id', 'enterprise_invitations', ['builder_id'])
    op.create_index('ix_enterprise_invitations_invited_email', 'enterprise_invitations', ['invited_email'])
    op.create_index('ix_enterprise_invitations_status', 'enterprise_invitations', ['status'])
    op.create_index('ix_enterprise_invitations_builder_status', 'enterprise_invitations', ['builder_id', 'status'])
    op.create_index('ix_enterprise_invitations_email', 'enterprise_invitations', ['invited_email'])

    # Create builder_team_members table
    op.create_table(
        'builder_team_members',
        sa.Column('id', mysql.BIGINT(unsigned=True), autoincrement=True, primary_key=True),
        sa.Column('builder_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('role', sa.Enum('admin', 'sales_rep', 'manager', 'viewer', name='builder_team_role_enum'), nullable=False, server_default='sales_rep'),
        sa.Column('permissions', sa.JSON()),
        sa.Column('communities_assigned', sa.JSON()),
        sa.Column('added_by_user_id', sa.String(50)),
        sa.Column('is_active', sa.Enum('active', 'inactive', name='team_member_status'), server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), nullable=False),
        sa.ForeignKeyConstraint(['builder_id'], ['builder_profiles.builder_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by_user_id'], ['users.user_id'], ondelete='SET NULL')
    )

    # Create indexes for builder_team_members
    op.create_index('ix_builder_team_members_builder_id', 'builder_team_members', ['builder_id'])
    op.create_index('ix_builder_team_members_user_id', 'builder_team_members', ['user_id'])
    op.create_index('uq_builder_team_member', 'builder_team_members', ['builder_id', 'user_id'], unique=True)

    print("✓ Created enterprise_invitations table")
    print("✓ Created builder_team_members table")


def downgrade() -> None:
    """Drop enterprise_invitations and builder_team_members tables."""
    op.drop_table('builder_team_members')
    op.drop_table('enterprise_invitations')
    print("✓ Dropped enterprise tables")
