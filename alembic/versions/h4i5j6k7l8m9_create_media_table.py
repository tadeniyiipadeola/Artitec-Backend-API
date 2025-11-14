"""create media table

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2025-11-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'h4i5j6k7l8m9'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'media',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('public_id', sa.String(length=20), nullable=False, unique=True, comment='Public-facing ID'),

        # File information
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('media_type', sa.Enum('image', 'video', name='media_type_enum'), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),

        # Dimensions (for images and videos)
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True, comment='Duration in seconds for videos'),

        # Storage URLs
        sa.Column('storage_path', sa.Text(), nullable=False, comment='Base storage path'),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('medium_url', sa.Text(), nullable=True),
        sa.Column('large_url', sa.Text(), nullable=True),
        sa.Column('video_processed_url', sa.Text(), nullable=True, comment='Processed/compressed video'),

        # Entity relationship (polymorphic)
        sa.Column('entity_type', sa.String(length=50), nullable=False, comment='property, community, user, post, amenity, etc.'),
        sa.Column('entity_id', sa.Integer(), nullable=False, comment='ID of the related entity'),
        sa.Column('entity_field', sa.String(length=50), nullable=True, comment='Specific field: avatar, gallery, cover, etc.'),

        # Metadata
        sa.Column('alt_text', sa.String(length=500), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True, default=0),

        # Ownership and timestamps
        sa.Column('uploaded_by', sa.String(length=20), nullable=False, comment='User public_id who uploaded'),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),

        # Indexes for performance
        sa.Index('idx_media_entity', 'entity_type', 'entity_id'),
        sa.Index('idx_media_uploaded_by', 'uploaded_by'),
        sa.Index('idx_media_created_at', 'created_at'),
        sa.Index('idx_media_public_id', 'public_id'),
    )


def downgrade() -> None:
    op.drop_table('media')
