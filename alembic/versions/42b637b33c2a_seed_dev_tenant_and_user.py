"""seed dev tenant and user

Revision ID: 42b637b33c2a
Revises: 45c9d2250490
Create Date: 2026-10-28 14:48:28.884098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '42b637b33c2a'
down_revision: Union[str, Sequence[str], None] = '45c9d2250490'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table("tenants", sa.column("id", UUID), sa.column("name", sa.String)),
        [{"id": "f4cd81dd-afd4-4f3b-a636-9560dfd9c554", "name": "Dev Tenant"}],
    )
    op.bulk_insert(
        sa.table("users",
            sa.column("id", UUID), sa.column("email", sa.String),
            sa.column("tenant_id", UUID), sa.column("hashed_password", sa.String), sa.column("role", sa.String)
        ),
        [{
            "id": "8afdeb37-a7e7-4521-b527-99f1d88f4b8e",
            "email": "dev@ahadiiq.local",
            "tenant_id": "f4cd81dd-afd4-4f3b-a636-9560dfd9c554",
            "hashed_password": "dev-placeholder",
            "role": "manager"
        }],
    )

def downgrade() -> None:
    op.execute("DELETE FROM users WHERE id = '8afdeb37-a7e7-4521-b527-99f1d88f4b8e'")
    op.execute("DELETE FROM tenants WHERE id = 'f4cd81dd-afd4-4f3b-a636-9560dfd9c554'")
