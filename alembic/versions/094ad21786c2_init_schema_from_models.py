"""init schema from models

Revision ID: 094ad21786c2
Revises: 
Create Date: 2025-10-15 23:00:38.994029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '094ad21786c2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # --- Lookups / enums are inline ENUMs on MySQL ---

    # user_types
    op.create_table(
        "user_types",
        sa.Column("id", sa.SmallInteger, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.CHAR(36), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("phone_e164", sa.String(32)),
        sa.Column("user_type_id", sa.SmallInteger, sa.ForeignKey("user_types.id"), nullable=False),
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.Enum("active", "suspended", "deleted", name="user_status"),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # user_credentials (1:1 users)
    op.create_table(
        "user_credentials",
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "password_algo",
            sa.Enum("bcrypt", name="password_algo"),
            nullable=False,
            server_default=sa.text("'bcrypt'"),
        ),
        sa.Column("last_password_change", sa.DateTime()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # email_verifications
    op.create_table(
        "email_verifications",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("ip_addr", sa.String(45)),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked_at", sa.DateTime),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        sa.Column("org_type", sa.Enum("builder", "community", name="org_type"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enterprise_number", sa.String(64), unique=True),
        sa.Column("address", sa.String(255)),
        sa.Column("city", sa.String(120)),
        sa.Column("state", sa.String(64)),
        sa.Column("active_tier", sa.Enum("free", "pro", "enterprise", name="org_tier")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_org_type_name", "organizations", ["org_type", "name"])

    # builder_profiles (1:1 org)
    op.create_table(
        "builder_profiles",
        sa.Column(
            "org_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("website_url", sa.String(512)),
        sa.Column("company_address", sa.String(255)),
        sa.Column("staff_size", sa.String(32)),
        sa.Column("years_in_business", sa.SmallInteger),
        sa.Column("rating_avg", sa.String(8)),
        sa.Column("rating_count", sa.Integer, server_default=sa.text("0")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # community_profiles (1:1 org)
    op.create_table(
        "community_profiles",
        sa.Column(
            "org_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("community_name", sa.String(255), nullable=False),
        sa.Column("community_address", sa.String(255)),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column(
            "stage",
            sa.Enum("pre_development", "first_phase", "second_stage", "completed", name="community_stage"),
        ),
        sa.Column("enterprise_number", sa.String(64)),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_community_city_state", "community_profiles", ["city", "state"])

    # community_admin_links (N:1 user to org)
    op.create_table(
        "community_admin_links",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", name="admin_verify_status"),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("requested_at", sa.TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("decided_at", sa.DateTime),
        sa.UniqueConstraint("user_id", "org_id", name="uq_admin_user_org"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_admin_status", "community_admin_links", ["status"])

    # sales_rep_profiles (1:1 user)
    op.create_table(
        "sales_rep_profiles",
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("address", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("sex", sa.Enum("female", "male", "non_binary", "prefer_not", name="sex")),
        sa.Column("dob", sa.Date),
        sa.Column("brokerage", sa.String(255)),
        sa.Column("license_id", sa.String(64)),
        sa.Column("years_at_company", sa.SmallInteger),
        sa.Column("company_account_number", sa.String(64)),
        sa.Column("office_location", sa.String(255)),
        sa.Column(
            "community_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # buyer_preferences (1:1 user)
    op.create_table(
        "buyer_preferences",
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sex", sa.Enum("female", "male", "non_binary", "prefer_not", name="sex_pref")),
        sa.Column("income_range", sa.String(64)),
        sa.Column("first_time", sa.Enum("yes", "no", "prefer_not", name="first_time_flag")),
        sa.Column("home_type", sa.Enum("single_home", "multiple_homes", name="home_type")),
        sa.Column("budget_min", sa.Integer),
        sa.Column("budget_max", sa.Integer),
        sa.Column("location_interest", sa.String(255)),
        sa.Column("builder_interest", sa.String(255)),
        sa.Column("meta", sa.JSON()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # onboarding_forms
    op.create_table(
        "onboarding_forms",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            mysql.BIGINT(unsigned=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("user", "builder", "community", "communityAdmin", "salesRep", "buyer", name="onboard_role"),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.Enum("preview", "committed", name="onboard_status"), nullable=False, server_default=sa.text("'preview'")),
        sa.Column("created_at", sa.TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    # Optional: seed user_types (safe for empty DB)
    op.execute(
        """
        INSERT INTO user_types (code, display_name) VALUES
        ('admin','Admin'),
        ('builder','Builder'),
        ('community','Community'),
        ('community_admin','Community Admin'),
        ('homeowner','Homeowner'),
        ('member','Member'),
        ('pending','Pending'),
        ('sales_rep','Sales Rep'),
        ('user','User')
        ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
        """
    )


def downgrade():
    # Drop in reverse dependency order
    op.drop_table("onboarding_forms")
    op.drop_table("buyer_preferences")
    op.drop_table("sales_rep_profiles")
    op.drop_index("ix_admin_status", table_name="community_admin_links")
    op.drop_table("community_admin_links")
    op.drop_index("ix_community_city_state", table_name="community_profiles")
    op.drop_table("community_profiles")
    op.drop_table("builder_profiles")
    op.drop_index("ix_org_type_name", table_name="organizations")
    op.drop_table("organizations")
    op.drop_table("sessions")
    op.drop_table("email_verifications")
    op.drop_table("user_credentials")
    op.drop_table("users")
    op.drop_table("user_types")
