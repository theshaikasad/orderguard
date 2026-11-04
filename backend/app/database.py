"""PostgreSQL schema and connection configuration. No credentials are logged."""
import os
from functools import lru_cache
from sqlalchemy import (MetaData, Table, Column, String, Integer, ForeignKey,
                        ForeignKeyConstraint, UniqueConstraint, CheckConstraint, create_engine)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url

metadata = MetaData()
businesses = Table('businesses', metadata,
    Column('id', String(80), primary_key=True), Column('config', JSONB, nullable=False))
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
    return create_engine(url or database_url(), pool_pre_ping=True, hide_parameters=True)


def business_id():
    return os.getenv('ORDERGUARD_BUSINESS_ID', 'little-crumb-v1')
