"""add_platform_admin_user

Revision ID: ac5a8543bc9a
Revises: 2c102111fe4b
Create Date: 2025-11-17 23:12:03.157476

"""
from typing import Sequence, Union
import time
import secrets

from alembic import op
import sqlalchemy as sa
import bcrypt


# revision identifiers, used by Alembic.
revision: str = 'ac5a8543bc9a'
down_revision: Union[str, Sequence[str], None] = '6259c90a0e16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_user_id():
    """Generate user ID: USR-TIMESTAMP-RANDOM"""
    timestamp = int(time.time())
    random_bytes = secrets.token_urlsafe(6)
    random_part = random_bytes.replace('-', '').replace('_', '')[:6].upper()
    return f"USR-{timestamp}-{random_part}"


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def upgrade() -> None:
    """Create platform admin user."""
    # Check if user already exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": "supportteam@artitecplatform.com"}
    ).fetchone()

    if result:
        print("✓ Admin user already exists, skipping creation")
        return

    # Create the admin user
    user_id = generate_user_id()
    password_hash = hash_password("Password!")

    conn.execute(
        sa.text("""
            INSERT INTO users (
                user_id, email, first_name, last_name,
                password_hash, password_algo,
                role, is_email_verified, onboarding_completed,
                plan_tier, status, created_at
            ) VALUES (
                :user_id, :email, :first_name, :last_name,
                :password_hash, :password_algo,
                :role, :is_email_verified, :onboarding_completed,
                :plan_tier, :status, NOW()
            )
        """),
        {
            "user_id": user_id,
            "email": "supportteam@artitecplatform.com",
            "first_name": "Artitec",
            "last_name": "Admin",
            "password_hash": password_hash,
            "password_algo": "bcrypt",
            "role": "admin",
            "is_email_verified": True,
            "onboarding_completed": True,
            "plan_tier": "enterprise",
            "status": "active"
        }
    )

    # Get the auto-incremented ID of the created user
    user_result = conn.execute(
        sa.text("SELECT id FROM users WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()

    if user_result:
        user_db_id = user_result[0]

        # Create credential record in user_credentials table
        conn.execute(
            sa.text("""
                INSERT INTO user_credentials (
                    user_id, password_hash, last_password_change
                ) VALUES (
                    :user_id, :password_hash, NOW()
                )
            """),
            {
                "user_id": user_db_id,
                "password_hash": password_hash
            }
        )
        print(f"✓ Created user credential record")

    print(f"✓ Created platform admin user: {user_id}")
    print(f"  Email: supportteam@artitecplatform.com")
    print(f"  Password: Password!")


def downgrade() -> None:
    """Remove platform admin user."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": "supportteam@artitecplatform.com"}
    )
    print("✓ Removed platform admin user")
