"""Opt-in live HTTP -> frontend proxy -> FastAPI -> Muse -> PostgreSQL check."""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import get_store
from app.agent_models import State


def main():
    if '--live' not in sys.argv:
        raise SystemExit('Use --live; makes real Meta calls and leaves a synthetic conversation.')
    base = os.getenv('VERIFY_API_URL', 'http://frontend:3000')
    cid = f'm2-live-{uuid4().hex[:10]}'
    store = get_store()
    day = (datetime.now(ZoneInfo('Asia/Kolkata')) + timedelta(days=9)).date().isoformat()
    with httpx.Client(base_url=base, timeout=120) as client:
        config = client.get('/api/business/config')
        config.raise_for_status()
        assert config.json()['policy']['pricing'] == 'fixed'
        assert client.get('/api/v1/demo').json()['source'] == 'fixture'
        def send(mid, text):
            for _ in range(3):
                response = client.post(f'/api/conversations/{cid}/messages', json={'message_id': mid, 'text': text})
                if response.status_code != 503:
                    break
                print('Interpretation unavailable; retrying the same message ID.', flush=True)
            response.raise_for_status()
            state = State.model_validate_json(response.text)
            assert state == store.get(cid)
            assert state.source == 'meta' and state.turns[-1].reply_source == 'meta'
            print(f'{mid}: status={state.status}; source=meta; reply_source=meta; PostgreSQL matches HTTP', flush=True)
            return state
        s = send('quote', f'I need 1 chocolate cake, 1 kg, on {day} for pickup.')
        assert s.offered_terms.total == 900 and s.accepted_commitment is None
        s = send('extras', 'Make it eggless with floral decoration.')
        assert s.offered_terms.total == 1300
        s = send('accept', 'I confirm')
        assert s.status == 'accepted' and s.accepted_commitment.terms.total == 1300
        assert s.payment == 'unknown' and s.production_snapshot is None
        assert send('accept', 'I confirm') == s
        r = client.post(f'/api/conversations/{cid}/owner-action', json={'action': 'start_production'})
        r.raise_for_status()
        s = State.model_validate_json(r.text)
        assert s.production_snapshot == s.accepted_commitment
        assert s == store.get(cid)
        assert len([t for t in s.turns if t.sender == 'customer']) == 3
        print(f'PASS portable workflow: {cid}; ₹900 -> ₹1300 -> natural acceptance; duplicate unchanged; production frozen.', flush=True)


if __name__ == '__main__':
    main()
