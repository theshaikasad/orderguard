"""Business-scoped state, customers, append-only messages and events.

Revision ID: 0001_postgres
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_postgres'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('businesses', sa.Column('id', sa.String(80), primary_key=True),
                    sa.Column('config', postgresql.JSONB(), nullable=False))
    op.create_table('customers',
        sa.Column('business_id', sa.String(80), sa.ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('id', sa.String(80), primary_key=True), sa.Column('name', sa.String(200), nullable=False))
    op.create_table('conversations',
        sa.Column('business_id', sa.String(80), sa.ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('id', sa.String(80), primary_key=True), sa.Column('customer_id', sa.String(80)),
        sa.Column('state', postgresql.JSONB(), nullable=False), sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['business_id', 'customer_id'], ['customers.business_id', 'customers.id']),
        sa.CheckConstraint('version > 0', name='ck_conversation_version'))
    for name, unique in [('messages', 'uq_message_position'), ('events', 'uq_event_position')]:
        columns = [sa.Column('business_id', sa.String(80), primary_key=True),
                   sa.Column('conversation_id', sa.String(80), primary_key=True),
                   sa.Column('id', sa.String(100), primary_key=True),
                   sa.Column('position', sa.Integer(), nullable=False),
                   sa.Column('data', postgresql.JSONB(), nullable=False)]
        if name == 'messages':
            columns += [sa.Column('sender', sa.String(20), nullable=False),
                        sa.CheckConstraint("sender IN ('customer', 'baker', 'owner')", name='ck_message_sender')]
        op.create_table(name, *columns,
            sa.ForeignKeyConstraint(['business_id', 'conversation_id'], ['conversations.business_id', 'conversations.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('business_id', 'conversation_id', 'position', name=unique))


def downgrade():
    for name in ('events', 'messages', 'conversations', 'customers', 'businesses'):
        op.drop_table(name)
