"""add role_type_id to users and FK

Revision ID: adae36eef93b
Revises: 094ad21786c2
Create Date: 2025-10-20 16:41:51.166425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adae36eef93b'
down_revision: Union[str, Sequence[str], None] = '094ad21786c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # Use Integer/BigInteger and UNSIGNED to match MySQL schema if needed
    op.add_column("users", sa.Column("role_type_id", sa.Integer(), nullable=True))
    # If your role_types.id is UNSIGNED, use mysql_unsigned=True:
    # op.alter_column("users", "role_type_id", type_=sa.Integer(unsigned=True))

    # Optional backfill if you keep users.role (string)
    op.execute("""
        UPDATE users u
        JOIN role_types rt ON rt.name = u.role
        SET u.role_type_id = rt.id
        WHERE u.role IS NOT NULL AND u.role <> '';
    """)

    op.create_foreign_key(
        "fk_users_role_type",
        "users",
        "role_types",
        ["role_type_id"],
        ["id"],
        # If role_types is in another schema, set referent_schema="that_schema"
    )

def downgrade():
    op.drop_constraint("fk_users_role_type", "users", type_="foreignkey")
    op.drop_column("users", "role_type_id")