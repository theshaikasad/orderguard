"""All store/agent regressions run against real PostgreSQL, never SQLite mocks."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from app.database import get_engine, businesses
from app.bootstrap import migrate, seed
from app.store import Store


@pytest.fixture(scope='session')
def pg_engine():
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.fail('TEST_DATABASE_URL is required: run tests against a disposable PostgreSQL database.')
    engine = get_engine(make_url(url).set(drivername='postgresql+psycopg'))
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def store(pg_engine):
    bid = 'test-' + uuid4().hex
    seed(pg_engine, bid)
    value = Store(pg_engine.url, bid)
    yield value
    with pg_engine.begin() as conn:
        conn.execute(delete(businesses).where(businesses.c.id == bid))
