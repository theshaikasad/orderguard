"""Real PostgreSQL consistency, isolation, migration and import checks."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4
from datetime import timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import insert, select, delete, func, inspect
from sqlalchemy.exc import IntegrityError
from app.bootstrap import migrate, seed
from app.database import businesses, customers, conversations, messages, events
from app.store import Store
from app.import_sqlite import import_sqlite
from app.agent_models import State, Incoming
from app.engine import process
from test_agent import MockProvider, quoted, accepted, turn, NOW, DATE


def test_migration_and_seed_are_idempotent(store, pg_engine):
    migrate(pg_engine)
    seed(pg_engine, store.business_id)
    assert {'businesses','customers','conversations','messages','events','alembic_version'} <= set(inspect(pg_engine).get_table_names())
    assert store.catalogue()['policy']['pricing'] == 'fixed'
    with pg_engine.begin() as conn:
        assert conn.execute(select(func.count()).select_from(customers).where(customers.c.business_id == store.business_id)).scalar_one() == 2
        changed = store.catalogue()
        changed['name'] = 'Approved existing name'
        conn.execute(businesses.update().where(businesses.c.id == store.business_id).values(config=changed))
    seed(pg_engine, store.business_id)
    assert store.catalogue()['name'] == 'Approved existing name'


def test_independent_connections_preserve_accepted_state_and_audit(store):
    state = accepted(store)
    assert store.reopen().get('demo') == state
    with store.engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(messages).where(messages.c.business_id == store.business_id)).scalar_one() == len(state.turns)
        assert conn.execute(select(func.count()).select_from(events).where(events.c.business_id == store.business_id)).scalar_one() == len(state.events)


def test_business_and_conversation_isolation(store):
    first = quoted(store)
    other_bid = 'test-' + uuid4().hex
    seed(store.engine, other_bid)
    try:
        other = Store(store.engine.url, other_bid)
        assert other.get('demo').turns == []
        assert other.all() == []
        second = turn(store, 1, cid='different')
        assert store.get('demo') == first and second.accepted_commitment is None
        other.reset()
        assert store.get('demo') == first
    finally:
        with store.engine.begin() as conn:
            conn.execute(delete(businesses).where(businesses.c.id == other_bid))


def test_message_unique_constraint_and_atomic_rollback(store):
    state = quoted(store)
    with pytest.raises(IntegrityError):
        with store.engine.begin() as conn:
            conn.execute(insert(messages).values(business_id=store.business_id, conversation_id='demo',
                id=state.turns[0].id, position=100, sender='customer', data=state.turns[0].model_dump(mode='json')))
    assert store.get('demo') == state


def test_stale_direct_write_is_rejected(store):
    quoted(store)
    stale = store.reopen()
    old = stale.get('demo')
    new = turn(store, 2, text='Hello')
    old.status = 'cancelled'
    with pytest.raises(HTTPException) as exc:
        stale.save(old)
    assert exc.value.status_code == 409 and store.get('demo') == new


def test_existing_audit_cannot_be_rewritten(store):
    state = quoted(store)
    state.turns[0].text = 'Rewritten'
    with pytest.raises(HTTPException):
        store.save(state)
    assert store.reopen().get('demo').turns[0].text != 'Rewritten'


def test_failed_transaction_leaves_no_partial_state(store):
    with pytest.raises(ValueError):
        with store.transaction():
            store.get('rollback')
            store.save(State(id='rollback'))
            raise ValueError('Abort')
    assert not any(s.id == 'rollback' for s in store.all())


def test_simultaneous_duplicate_calls_interpret_only_once(store):
    started, release = Event(), Event()
    class Slow(MockProvider):
        def interpret(self, context):
            started.set()
            assert release.wait(10)
            return super().interpret(context)
    provider = Slow({'product':'chocolate','size':'1','quantity':'1','date':DATE,'fulfillment':'pickup'})
    incoming = Incoming(message_id='parallel', text='A cake', timestamp=NOW)
    def send():
        return process(store.reopen(), provider, 'parallel', incoming, now=NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(send)
        assert started.wait(5)
        second = pool.submit(send)
        release.set()
        a, b = first.result(timeout=15), second.result(timeout=15)
    assert a == b and provider.calls == 1 and len(a.turns) == 2


def test_parallel_acceptance_cannot_oversell_shared_capacity(store):
    spec = {'product':'chocolate','size':'1','quantity':'2','date':DATE,'fulfillment':'pickup'}
    turn(store, 1, MockProvider(spec), cid='a')
    turn(store, 1, MockProvider(spec), cid='b')
    def accept(cid):
        return process(store.reopen(), MockProvider(intents=['accept']), cid,
            Incoming(message_id='confirm', text='I confirm', timestamp=NOW+timedelta(seconds=10)), now=NOW+timedelta(seconds=20))
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(accept, ['a','b']))
    assert sum(s.accepted_commitment is not None for s in (a,b)) == 1
    assert sum(s.decision == 'needs_owner' for s in (a,b)) == 1


def test_sqlite_import_preserves_history_and_is_atomic(store, tmp_path):
    # Build an actual legacy-format SQLite file; importer only opens it read-only.
    state = accepted(store)
    path = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE conversations (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
        db.execute('INSERT INTO conversations VALUES (?,?)', ('demo', state.model_dump_json()))
    before = path.read_bytes()
    store.reset()
    assert import_sqlite(path, store) == 1
    assert store.reopen().get('demo') == state
    assert import_sqlite(path, store) == 0
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO conversations VALUES (?,?)', ('aaa-new', State(id='aaa-new').model_dump_json()))
        changed = state.model_copy(deep=True)
        changed.status = 'cancelled'
        db.execute('UPDATE conversations SET state=? WHERE id=?', (changed.model_dump_json(),'demo'))
    with pytest.raises(ValueError):
        import_sqlite(path, store)
    assert not any(s.id == 'aaa-new' for s in store.all())
    assert store.get('demo') == state
