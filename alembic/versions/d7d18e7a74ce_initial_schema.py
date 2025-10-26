"""initial schema (full Artitec tables)

Revision ID: d7d18e7a74ce
Revises: 
Create Date: 2025-10-25 22:49:15.297917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7d18e7a74ce'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tbl_kwargs():
    return dict(mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci")

def upgrade() -> None:
    """Upgrade schema: create full Artitec tables with FKs."""
    created_ts = sa.text("CURRENT_TIMESTAMP")
    updated_ts = sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

    # =======================
    # Core / Auth
    # =======================
    op.create_table(
        "role_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        **_tbl_kwargs(),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(120)),
        sa.Column("last_name", sa.String(120)),
        sa.Column("phone_e164", sa.String(32)),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("role_types.id")),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("plan_tier", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ux_users_email", "users", ["email"], unique=True)
    op.create_index("ux_users_public_id", "users", ["public_id"], unique=True)

    op.create_table(
        "user_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default=sa.text("'password'")),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_user_credentials_user_id", "user_credentials", ["user_id"])
    op.create_index("ix_user_credentials_provider", "user_credentials", ["provider"])

    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_email_verifications_user_id", "email_verifications", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("access_token", sa.String(512), nullable=False, unique=True),
        sa.Column("refresh_token", sa.String(512), unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "onboarding_forms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selected_role", sa.String(32)),
        sa.Column("selected_plan", sa.String(64)),
        sa.Column("org_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_onboarding_forms_user_id", "onboarding_forms", ["user_id"])

    # Seed role types
    op.execute(
        "INSERT INTO role_types (name) VALUES "
        "('buyer'), ('builder'), ('community'), ('community_admin'), ('salesrep'), ('admin') "
        "ON DUPLICATE KEY UPDATE name = VALUES(name);"
    )

    # =======================
    # Builder Module
    # =======================
    op.create_table(
        "builder_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("display_name", sa.String(150), nullable=False),
        sa.Column("bio", sa.Text()),
        sa.Column("website_url", sa.String(255)),
        sa.Column("logo_url", sa.String(255)),
        sa.Column("service_area", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_builder_profiles_user_id", "builder_profiles", ["user_id"])

    # Sales reps linked to builders
    op.create_table(
        "sales_reps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(128)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column("avatar_url", sa.String(1024)),
        sa.Column("region", sa.String(128)),
        sa.Column("office_address", sa.String(255)),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_sales_reps_builder_id", "sales_reps", ["builder_id"])
    op.create_index("ix_sales_reps_community_id", "sales_reps", ["community_id"])

    op.create_table(
        "builder_awards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("awarded_by", sa.String(200)),
        sa.Column("year", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_builder_awards_builder_id", "builder_awards", ["builder_id"])

    op.create_table(
        "builder_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_builder_documents_builder_id", "builder_documents", ["builder_id"])

    # Junction: builders ↔ communities
    op.create_table(
        "builder_communities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),  # FK added after communities table created
        sa.Column("role", sa.String(64)),  # e.g., primary, partner
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ux_builder_communities", "builder_communities", ["builder_id", "community_id"], unique=True)

    # =======================
    # Community Module
    # =======================
    op.create_table(
        "communities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("city", sa.String(120)),
        sa.Column("state", sa.String(64)),
        sa.Column("zip_code", sa.String(16)),
        sa.Column("address", sa.String(255)),
        sa.Column("website_url", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_communities_name", "communities", ["name"])

    op.create_table(
        "community_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_community_documents_community_id", "community_documents", ["community_id"])

    op.create_table(
        "community_phases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phase_number", sa.Integer()),
        sa.Column("status", sa.String(64)),  # planned, active, sold_out
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_community_phases_comm_id", "community_phases", ["community_id"])

    op.create_table(
        "community_amenities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_community_amenities_comm_id", "community_amenities", ["community_id"])

    op.create_table(
        "community_admin_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ux_comm_admin_links", "community_admin_links", ["community_id", "user_id"], unique=True)

    # Backfill FK in builder_communities now that communities exists
    op.create_foreign_key(
        "fk_builder_communities_community",
        "builder_communities", "communities",
        ["community_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_sales_reps_community",
        "sales_reps", "communities",
        ["community_id"], ["id"],
        ondelete="SET NULL",
    )

    # =======================
    # Property Module
    # =======================
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column("zip_code", sa.String(16), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("bedrooms", sa.Integer()),
        sa.Column("bathrooms", sa.Numeric(4, 1)),
        sa.Column("square_feet", sa.Integer()),
        sa.Column("lot_size", sa.Numeric(10, 2)),
        sa.Column("year_built", sa.Integer()),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="SET NULL")),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_properties_city_state", "properties", ["city", "state"])
    op.create_index("ix_properties_community", "properties", ["community_id"])
    op.create_index("ix_properties_builder", "properties", ["builder_id"])

    op.create_table(
        "property_media",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False, server_default=sa.text("'image'")),  # image, video
        sa.Column("position", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_property_media_prop_id", "property_media", ["property_id"])

    op.create_table(
        "property_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("value", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_property_features_prop_id", "property_features", ["property_id"])

    op.create_table(
        "property_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_property_documents_prop_id", "property_documents", ["property_id"])

    # Builder Portfolio (explicit link property ↔ builder with extra fields)
    op.create_table(
        "builder_portfolio",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ux_builder_portfolio", "builder_portfolio", ["builder_id", "property_id"], unique=True)

    # =======================
    # Buyer Module
    # =======================
    op.create_table(
        "buyer_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("display_name", sa.String(150), nullable=False),
        sa.Column("first_name", sa.String(120)),
        sa.Column("last_name", sa.String(120)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("address", sa.String(255)),
        sa.Column("city", sa.String(120)),
        sa.Column("state", sa.String(64)),
        sa.Column("zip_code", sa.String(16)),
        sa.Column("bio", sa.Text()),
        sa.Column("website_url", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("sex", sa.String(16)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_buyer_profiles_user_id", "buyer_profiles", ["user_id"])

    op.create_table(
        "buyer_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("budget_min", sa.Numeric(12, 2)),
        sa.Column("budget_max", sa.Numeric(12, 2)),
        sa.Column("home_type", sa.String(64)),
        sa.Column("city", sa.String(120)),
        sa.Column("state", sa.String(64)),
        sa.Column("bedrooms_min", sa.Integer()),
        sa.Column("bathrooms_min", sa.Numeric(4, 1)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_buyer_preferences_buyer_id", "buyer_preferences", ["buyer_id"])

    op.create_table(
        "buyer_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_buyer_documents_buyer_id", "buyer_documents", ["buyer_id"])

    op.create_table(
        "buyer_tours",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32)),   # requested, scheduled, completed, canceled
        sa.Column("scheduled_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_buyer_tours_buyer_property", "buyer_tours", ["buyer_id", "property_id"])

    # Saved properties (buyer ↔ property)
    op.create_table(
        "saved_properties",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("buyer_id", sa.Integer(), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ux_saved_properties", "saved_properties", ["buyer_id", "property_id"], unique=True)

    # =======================
    # Social / Interaction
    # =======================
    op.create_table(
        "follows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("follower_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("target_builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_follows_follower", "follows", ["follower_user_id"])
    op.create_index("ix_follows_targets", "follows", ["target_user_id", "target_builder_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=updated_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_comments_author", "comments", ["author_user_id"])

    op.create_table(
        "likes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=True),
        sa.Column("builder_id", sa.Integer(), sa.ForeignKey("builder_profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_likes_user", "likes", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receiver_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_messages_participants", "messages", ["sender_user_id", "receiver_user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=created_ts),
        **_tbl_kwargs(),
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id"])


def downgrade() -> None:
    """Drop tables in FK-safe reverse order."""
    # Social
    op.drop_index("ix_notifications_user", table_name="notifications"); op.drop_table("notifications")
    op.drop_index("ix_messages_participants", table_name="messages"); op.drop_table("messages")
    op.drop_index("ix_likes_user", table_name="likes"); op.drop_table("likes")
    op.drop_index("ix_comments_author", table_name="comments"); op.drop_table("comments")
    op.drop_index("ix_follows_targets", table_name="follows"); op.drop_index("ix_follows_follower", table_name="follows"); op.drop_table("follows")

    # Buyer
    op.drop_index("ux_saved_properties", table_name="saved_properties"); op.drop_table("saved_properties")
    op.drop_index("ix_buyer_tours_buyer_property", table_name="buyer_tours"); op.drop_table("buyer_tours")
    op.drop_index("ix_buyer_documents_buyer_id", table_name="buyer_documents"); op.drop_table("buyer_documents")
    op.drop_index("ix_buyer_preferences_buyer_id", table_name="buyer_preferences"); op.drop_table("buyer_preferences")
    op.drop_index("ix_buyer_profiles_user_id", table_name="buyer_profiles"); op.drop_table("buyer_profiles")

    # Property
    op.drop_index("ux_builder_portfolio", table_name="builder_portfolio"); op.drop_table("builder_portfolio")
    op.drop_index("ix_property_documents_prop_id", table_name="property_documents"); op.drop_table("property_documents")
    op.drop_index("ix_property_features_prop_id", table_name="property_features"); op.drop_table("property_features")
    op.drop_index("ix_property_media_prop_id", table_name="property_media"); op.drop_table("property_media")
    op.drop_index("ix_properties_builder", table_name="properties"); op.drop_index("ix_properties_community", table_name="properties"); op.drop_index("ix_properties_city_state", table_name="properties"); op.drop_table("properties")

    # Community
    op.drop_constraint("fk_builder_communities_community", "builder_communities", type_="foreignkey"); 
    op.drop_index("ux_builder_communities", table_name="builder_communities"); op.drop_table("builder_communities")
    op.drop_index("ux_comm_admin_links", table_name="community_admin_links"); op.drop_table("community_admin_links")
    op.drop_index("ix_community_amenities_comm_id", table_name="community_amenities"); op.drop_table("community_amenities")
    op.drop_index("ix_community_phases_comm_id", table_name="community_phases"); op.drop_table("community_phases")
    op.drop_index("ix_community_documents_community_id", table_name="community_documents"); op.drop_table("community_documents")
    op.drop_index("ix_communities_name", table_name="communities"); op.drop_table("communities")

    # Builder
    op.drop_constraint("fk_sales_reps_community", "sales_reps", type_="foreignkey");
    op.drop_index("ix_sales_reps_community_id", table_name="sales_reps");
    op.drop_index("ix_sales_reps_builder_id", table_name="sales_reps"); op.drop_table("sales_reps")
    op.drop_index("ix_builder_documents_builder_id", table_name="builder_documents"); op.drop_table("builder_documents")
    op.drop_index("ix_builder_awards_builder_id", table_name="builder_awards"); op.drop_table("builder_awards")
    op.drop_index("ix_builder_profiles_user_id", table_name="builder_profiles"); op.drop_table("builder_profiles")

    # Core
    op.drop_index("ix_onboarding_forms_user_id", table_name="onboarding_forms"); op.drop_table("onboarding_forms")
    op.drop_index("ix_sessions_user_id", table_name="sessions"); op.drop_table("sessions")
    op.drop_index("ix_email_verifications_user_id", table_name="email_verifications"); op.drop_table("email_verifications")
    op.drop_index("ix_user_credentials_provider", table_name="user_credentials"); op.drop_index("ix_user_credentials_user_id", table_name="user_credentials"); op.drop_table("user_credentials")
    op.drop_index("ux_users_public_id", table_name="users"); op.drop_index("ux_users_email", table_name="users"); op.drop_table("users")
    op.drop_table("role_types")
