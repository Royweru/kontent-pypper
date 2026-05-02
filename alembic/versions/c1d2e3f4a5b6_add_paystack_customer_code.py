"""add paystack customer code

Revision ID: c1d2e3f4a5b6
Revises: b9f2c1d4e7a0
Create Date: 2026-05-01 11:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b9f2c1d4e7a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("paystack_customer_code", sa.String(), nullable=True))
    op.create_index(
        "ix_users_paystack_customer_code",
        "users",
        ["paystack_customer_code"],
        unique=False,
    )
    # Backfill from legacy stripe_customer_id column when present.
    op.execute(
        """
        UPDATE users
        SET paystack_customer_code = stripe_customer_id
        WHERE paystack_customer_code IS NULL
          AND stripe_customer_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_paystack_customer_code", table_name="users")
    op.drop_column("users", "paystack_customer_code")

