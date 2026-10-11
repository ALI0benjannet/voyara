"""add numeric role to users

Revision ID: c7e9a1b2d304
Revises: b4a7d8e9f012
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e9a1b2d304"
down_revision: Union[str, Sequence[str], None] = "b4a7d8e9f012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_user_role_enum = sa.Enum("tourist", "admin", name="userrole")
new_user_role_enum = sa.Enum("1", "2", name="userrole")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "role" in columns:
        op.execute("ALTER TYPE userrole RENAME TO userrole_old")
        new_user_role_enum.create(bind, checkfirst=False)
        op.execute(
            "ALTER TABLE users ALTER COLUMN role TYPE userrole "
            "USING CASE role::text WHEN 'admin' THEN '1'::userrole "
            "ELSE '2'::userrole END"
        )
        op.execute("DROP TYPE userrole_old")
        op.alter_column("users", "role", nullable=False, server_default="2")
        return

    new_user_role_enum.create(bind, checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", new_user_role_enum, nullable=True, server_default="2"),
    )
    op.execute(sa.text("UPDATE users SET role = '2' WHERE role IS NULL"))
    op.alter_column("users", "role", nullable=False, server_default="2")


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("ALTER TYPE userrole RENAME TO userrole_numeric")
    old_user_role_enum.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text WHEN '1' THEN 'admin'::userrole "
        "ELSE 'tourist'::userrole END"
    )
    op.execute("DROP TYPE userrole_numeric")
