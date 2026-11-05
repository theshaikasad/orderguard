"""Recording sessions isolate capacity/data while using the normal real agent path."""
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app, get_store
from app.store import Store
from app.agent_models import State
from app.database import businesses, configuration_versions


def test_fresh_recording_preserves_existing_data_and_rules(store):
    with store.transaction():
        store.save(State(id='existing'))
    original = store.catalogue()
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            first = client.post('/api/demo/sessions').json()
            second = client.post('/api/demo/sessions').json()
        assert first['business_id'] != second['business_id']
        for result in (first, second):
            isolated = Store(store.engine.url, result['business_id'])
            expected = dict(original, id=result['business_id'])
            assert isolated.catalogue() == expected == result['business']
            assert isolated.runtime() == (1, False)
            assert isolated.all() == [State(id='recording')]
            with isolated._read() as session:
                assert session.execute(select(configuration_versions.c.config).where(
                    configuration_versions.c.business_id == isolated.business_id)).scalar_one() == expected
        assert store.all() == [State(id='existing')]
        assert store.catalogue() == original
    finally:
        app.dependency_overrides.clear()
        # Only these disposable test sessions are removed.
        from sqlalchemy import delete
        with store.engine.begin() as conn:
            conn.execute(delete(businesses).where(businesses.c.id.in_([first['business_id'], second['business_id']])))


def test_paused_business_cannot_silently_start_live_demo(store):
    from sqlalchemy import update
    with store.transaction():
        store._session.execute(update(businesses).where(businesses.c.id == store.business_id).values(paused=True))
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as client:
            assert client.post('/api/demo/sessions').status_code == 409
    finally:
        app.dependency_overrides.clear()
