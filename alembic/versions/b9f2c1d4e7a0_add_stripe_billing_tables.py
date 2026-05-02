"""add stripe billing tables

Revision ID: b9f2c1d4e7a0
Revises: cb56b020daea
Create Date: 2026-04-30 20:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9f2c1d4e7a0"
down_revision: Union[str, Sequence[str], None] = "cb56b020daea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=False)

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_webhook_events_id", "payment_webhook_events", ["id"], unique=False)
    op.create_index("ix_payment_webhook_events_provider", "payment_webhook_events", ["provider"], unique=False)
    op.create_index(
        "ix_payment_webhook_events_provider_event_id",
        "payment_webhook_events",
        ["provider_event_id"],
        unique=True,
    )
    op.create_index("ix_payment_webhook_events_event_type", "payment_webhook_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_event_type", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_provider_event_id", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_provider", table_name="payment_webhook_events")
    op.drop_index("ix_payment_webhook_events_id", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")

    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "stripe_customer_id")

