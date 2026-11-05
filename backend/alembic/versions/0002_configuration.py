"""Seller drafts, immutable published versions and isolated lab runs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = '0002_configuration'
down_revision = '0001_postgres'
branch_labels = depends_on = None


def upgrade():
    op.add_column('businesses', sa.Column('active_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('businesses', sa.Column('paused', sa.Boolean(), nullable=False, server_default='false'))
    op.create_table('configuration_versions',
        sa.Column('business_id', sa.String(80), sa.ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('version', sa.Integer(), primary_key=True), sa.Column('config', JSONB(), nullable=False))
    op.execute('INSERT INTO configuration_versions (business_id, version, config) SELECT id, 1, config FROM businesses')
    op.create_table('configuration_drafts',
        sa.Column('business_id', sa.String(80), sa.ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('revision', sa.Integer(), nullable=False), sa.Column('config', JSONB(), nullable=False),
        sa.Column('questions', JSONB(), nullable=False), sa.Column('history', JSONB(), nullable=False))
    op.create_table('scenario_runs',
        sa.Column('business_id', sa.String(80), sa.ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('id', sa.String(80), primary_key=True),
        sa.Column('lab_business_id', sa.String(80), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('result', JSONB(), nullable=False))


def downgrade():
    for table in ('scenario_runs','configuration_drafts','configuration_versions'):
        op.drop_table(table)
    op.drop_column('businesses','paused')
    op.drop_column('businesses','active_version')
