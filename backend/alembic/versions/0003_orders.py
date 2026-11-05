"""Relational business-owned order projection, preserving historical snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = '0003_orders'
down_revision = '0002_configuration'
branch_labels = depends_on = None


def upgrade():
    op.create_table('orders',
        sa.Column('business_id', sa.String(80), primary_key=True),
        sa.Column('conversation_id', sa.String(80), primary_key=True),
        sa.Column('requested_spec', JSONB(), nullable=False),
        sa.Column('accepted_commitment', JSONB()), sa.Column('production_snapshot', JSONB()),
        sa.ForeignKeyConstraint(['business_id','conversation_id'], ['conversations.business_id','conversations.id'], ondelete='CASCADE'))
    op.execute("INSERT INTO orders SELECT business_id, id, state->'requested_spec', state->'accepted_commitment', state->'production_snapshot' FROM conversations")


def downgrade():
    op.drop_table('orders')
