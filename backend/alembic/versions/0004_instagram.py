"""Durable account-scoped Instagram inbox and held reply drafts. No tokens."""
from alembic import op
from app.database import instagram_accounts,instagram_inbox,instagram_outbox,instagram_replays
revision='0004_instagram'
down_revision='0003_orders'
branch_labels=depends_on=None


def upgrade():
    for table in (instagram_accounts,instagram_inbox,instagram_outbox,instagram_replays):
        table.create(op.get_bind())


def downgrade():
    for table in (instagram_replays,instagram_outbox,instagram_inbox,instagram_accounts):
        table.drop(op.get_bind())
