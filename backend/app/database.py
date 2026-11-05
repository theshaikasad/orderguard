"""PostgreSQL schema and connection configuration. No credentials are logged."""
import os
from functools import lru_cache
from sqlalchemy import (MetaData, Table, Column, String, Integer, ForeignKey,
                        ForeignKeyConstraint, UniqueConstraint, CheckConstraint, create_engine, Boolean, DateTime)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url

metadata = MetaData()
businesses = Table('businesses', metadata,
    Column('id', String(80), primary_key=True), Column('config', JSONB, nullable=False),
    Column('active_version', Integer, nullable=False, server_default='1'),
    Column('paused', Boolean, nullable=False, server_default='false'))
customers = Table('customers', metadata,
    Column('business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
    Column('id', String(80), primary_key=True), Column('name', String(200), nullable=False))
conversations = Table('conversations', metadata,
    Column('business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
    Column('id', String(80), primary_key=True), Column('customer_id', String(80)),
    Column('state', JSONB, nullable=False), Column('version', Integer, nullable=False),
    ForeignKeyConstraint(['business_id', 'customer_id'], ['customers.business_id', 'customers.id']),
    CheckConstraint('version > 0', name='ck_conversation_version'))
messages = Table('messages', metadata,
    Column('business_id', String(80), primary_key=True),
    Column('conversation_id', String(80), primary_key=True),
    Column('id', String(100), primary_key=True), Column('position', Integer, nullable=False),
    Column('sender', String(20), nullable=False), Column('data', JSONB, nullable=False),
    ForeignKeyConstraint(['business_id', 'conversation_id'], ['conversations.business_id', 'conversations.id'], ondelete='CASCADE'),
    UniqueConstraint('business_id', 'conversation_id', 'position', name='uq_message_position'),
    CheckConstraint("sender IN ('customer', 'baker', 'owner')", name='ck_message_sender'))
events = Table('events', metadata,
    Column('business_id', String(80), primary_key=True),
    Column('conversation_id', String(80), primary_key=True),
    Column('id', String(100), primary_key=True), Column('position', Integer, nullable=False),
    Column('data', JSONB, nullable=False),
    ForeignKeyConstraint(['business_id', 'conversation_id'], ['conversations.business_id', 'conversations.id'], ondelete='CASCADE'),
    UniqueConstraint('business_id', 'conversation_id', 'position', name='uq_event_position'))


def database_url():
    value = os.getenv('DATABASE_URL')
    if not value:
        raise RuntimeError('DATABASE_URL is required. Start PostgreSQL and run app.bootstrap.')
    url = make_url(value)
    if url.get_backend_name() != 'postgresql':
        raise RuntimeError('DATABASE_URL must point to PostgreSQL.')
    return url.set(drivername='postgresql+psycopg')


@lru_cache(maxsize=8)
def get_engine(url=None):
    engine = create_engine(url or database_url(), pool_pre_ping=True, hide_parameters=True)
    from .telemetry import instrument
    instrument(engine)
    return engine


def business_id():
    return os.getenv('ORDERGUARD_BUSINESS_ID', 'little-crumb-v1')

configuration_drafts = Table('configuration_drafts', metadata,
    Column('business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
    Column('revision', Integer, nullable=False), Column('config', JSONB, nullable=False),
    Column('questions', JSONB, nullable=False), Column('history', JSONB, nullable=False))
configuration_versions = Table('configuration_versions', metadata,
    Column('business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
    Column('version', Integer, primary_key=True), Column('config', JSONB, nullable=False))
scenario_runs = Table('scenario_runs', metadata,
    Column('business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), primary_key=True),
    Column('id', String(80), primary_key=True),
    Column('lab_business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
    Column('result', JSONB, nullable=False))

orders = Table('orders', metadata,
    Column('business_id', String(80), primary_key=True),
    Column('conversation_id', String(80), primary_key=True),
    Column('requested_spec', JSONB, nullable=False),
    Column('accepted_commitment', JSONB), Column('production_snapshot', JSONB),
    ForeignKeyConstraint(['business_id', 'conversation_id'], ['conversations.business_id', 'conversations.id'], ondelete='CASCADE'))

# Instagram credentials stay in runtime secret variables; only references are stored.
instagram_accounts = Table('instagram_accounts', metadata,
    Column('id', String(100), primary_key=True),
    Column('business_id', String(80), ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False),
    Column('mode', String(20), nullable=False), Column('status', String(30), nullable=False),
    Column('token_env', String(120)),
    UniqueConstraint('id','business_id', name='uq_instagram_account_business'),
    CheckConstraint("mode IN ('live','replay')",name='ck_instagram_account_mode'))
instagram_inbox = Table('instagram_inbox', metadata,
    Column('account_id', String(100), primary_key=True), Column('id', String(100), primary_key=True),
    Column('business_id', String(80), nullable=False), Column('sender_id', String(100), nullable=False),
    Column('conversation_id', String(60), nullable=False), Column('incoming', JSONB, nullable=False),
    Column('content_hash', String(64), nullable=False), Column('status', String(30), nullable=False),
    Column('attempts', Integer, nullable=False, server_default='0'), Column('error', String(300)),
    Column('next_attempt_at', DateTime(timezone=True)),
    ForeignKeyConstraint(['account_id','business_id'],['instagram_accounts.id','instagram_accounts.business_id'],ondelete='CASCADE'))
instagram_outbox = Table('instagram_outbox', metadata,
    Column('account_id', String(100), primary_key=True), Column('event_id', String(100), primary_key=True),
    Column('business_id', String(80), nullable=False), Column('recipient_id', String(100), nullable=False),
    Column('text', String(8000), nullable=False), Column('status', String(40), nullable=False),
    Column('last_customer_at', DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(['account_id','event_id'],['instagram_inbox.account_id','instagram_inbox.id'],ondelete='CASCADE'),
    ForeignKeyConstraint(['account_id','business_id'],['instagram_accounts.id','instagram_accounts.business_id'],ondelete='CASCADE'))
instagram_replays = Table('instagram_replays',metadata,
    Column('id',String(100),primary_key=True),
    Column('business_id',String(80),ForeignKey('businesses.id',ondelete='CASCADE'),nullable=False),
    Column('lab_business_id',String(80),ForeignKey('businesses.id',ondelete='CASCADE'),nullable=False))
