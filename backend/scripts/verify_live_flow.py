"""Opt-in real HTTP + Muse + PostgreSQL check against the running local backend.

Creates one uniquely named synthetic conversation; never resets existing data.
Run from backend: .venv/bin/python scripts/verify_live_flow.py --live
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import get_store  # Same absolute .env/bootstrap and DB as the API.
from app.agent_models import State


def main():
    if '--live' not in sys.argv:
        raise SystemExit('Opt in with --live; this sends synthetic turns to real Meta via localhost:8000.')
    cid = f'm12-{uuid4().hex[:12]}'
    day = (datetime.now(ZoneInfo('Asia/Kolkata')) + timedelta(days=7)).date().isoformat()
    store = get_store()
    with httpx.Client(base_url='http://127.0.0.1:8000', timeout=120) as client:
        def send(mid, text):
            body = {'message_id': mid, 'text': text}
            for attempt in range(3):
                response = client.post(f'/api/conversations/{cid}/messages', json=body)
                if response.status_code != 503:
                    break
                # An interpretation failure saves nothing. Retry the same ID,
                # just as the browser does; never substitute a simulated result.
                print(f'Interpretation attempt {attempt + 1}: {response.json()["detail"]}', flush=True)
            response.raise_for_status()
            state = State.model_validate_json(response.text)
            assert state.source == 'meta', 'Not a real Meta result'
            assert store.get(cid) == state, 'API response differs from persisted PostgreSQL state'
            assert state.turns[-1].reply_source == 'meta', 'Reply generation fell back; not a live-composed reply'
            assert 'offer-' not in state.assistant_reply
            print(f'  {mid}: {state.assistant_reply}', flush=True)
            return state

        s = send('inquiry', 'What cakes do you make?')
        assert not s.offered_terms and not s.accepted_commitment
        s = send('partial', 'I would like a chocolate cake.')
        assert 'size' in s.missing_fields and not s.offered_terms
        s = send('a', f'I need 1 chocolate cake, 1 kg, on {day} for pickup.')
        assert s.offered_terms.total == 900 and not s.accepted_commitment
        print('PASS A: real Meta quote ₹900; PostgreSQL matches HTTP response')
        s = send('ambiguous', 'Yes')
        assert not s.accepted_commitment
        s = send('b', 'Make it eggless with floral decoration.')
        assert s.offered_terms.total == 1300 and not s.accepted_commitment
        assert any(e.kind == 'offer_invalidated' for e in s.events)
        print('PASS B: customization repriced ₹1300; old offer invalidated')
        s = send('d', 'Could you give me 90% off?')
        assert s.offered_terms.total == 1300 and s.offered_terms.discount_percent == 0
        assert 'fixed' in s.assistant_reply
        print('PASS D: fixed-price refusal; total stays ₹1300')
        s = send('clarify', 'Yes, go ahead')
        assert not s.accepted_commitment, 'Acceptance after an alternative suggestion is ambiguous'
        acceptance = 'I confirm'
        s = send('c', acceptance)
        assert s.status == 'accepted' and s.accepted_commitment.terms == s.offered_terms
        assert s.accepted_commitment.evidence[0] == 'c' and s.production_snapshot is None
        duplicate = send('c', acceptance)
        assert duplicate == s
        print('PASS C / duplicate: exact commitment persisted; retry adds no turn/event/reply')
        response = client.post(f'/api/conversations/{cid}/owner-action', json={'action': 'start_production'})
        response.raise_for_status()
        frozen = State.model_validate_json(response.text).production_snapshot
        s = send('late', 'Change the flavor to red velvet.')
        assert s.decision == 'needs_owner' and s.offered_terms is None
        assert s.requested_spec['product'].value == 'red_velvet'
        assert s.accepted_commitment == frozen == s.production_snapshot
        assert s.production_snapshot.terms.spec['product'].value == 'chocolate'
        assert State.model_validate_json(client.get(f'/api/conversations/{cid}').text) == s
        assert sum(t.sender == 'customer' for t in s.turns) == 9
        assert sum(t.sender == 'baker' for t in s.turns) == 9
        print('PASS state split: late request needs owner; accepted/production snapshots unchanged')
        print(f'PASS: source=meta; persisted conversation={cid}; customer turns=9; replies=9; reply_source=meta')


if __name__ == '__main__':
    main()
