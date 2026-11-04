import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app, FIXTURE
from app.models import Demo

client = TestClient(app)


def test_health():
    assert client.get('/health').json() == {'status': 'ok'}


def test_demo_contract():
    response = client.get('/api/v1/demo')
    assert response.status_code == 200
    demo = Demo.model_validate_json(response.text)
    order = demo.conversations[0].orders[0]
    assert order.requested.dietary.value == 'Eggless requested'
    assert order.production.dietary.value == order.accepted.dietary.value
    assert order.payment.value == 'Claimed · pending human verification'
    assert demo.conversations[0].alerts[0].priority == 'critical'
    assert demo.mode == 'demo'


@pytest.mark.parametrize('corruption', ['evidence', 'duplicate', 'timezone', 'extra'])
def test_reject_invalid_fixture(corruption):
    data = json.loads(FIXTURE.read_text())
    c = data['conversations'][0]
    if corruption == 'evidence':
        c['alerts'][0]['evidence']['message_ids'] = ['missing']
    elif corruption == 'duplicate':
        c['messages'][1]['id'] = c['messages'][0]['id']
    elif corruption == 'timezone':
        c['messages'][0]['sent_at'] = '2026-11-04T10:00:00'
    else:
        data['inferred'] = True
    with pytest.raises(ValidationError):
        Demo.model_validate_json(json.dumps(data))


def test_local_cors():
    response = client.get('/api/v1/demo', headers={'Origin': 'http://localhost:3000'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:3000'
