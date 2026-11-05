"""Opt-in recording rehearsal: real frontend HTTP, Muse and persisted PostgreSQL.

Never resets data. Leaves its isolated synthetic session available for inspection.
"""
import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
from app.agent_models import State
from app.store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--base', default='http://frontend:3000')
    parser.add_argument('--output', default='/tmp/recording-demo-verification.json')
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required; this uses the real Meta API with synthetic messages.')
    report = {'steps': []}
    with httpx.Client(base_url=args.base, timeout=250) as client:
        r = client.post('/api/demo/sessions', json={})
        r.raise_for_status()
        session = r.json()
        report['session'] = session
        bid, cid = session['business_id'], session['conversation_id']
        client.headers['X-Orderguard-Business'] = bid
        store = Store(business=bid)
        config = session['business']
        day = (datetime.now(ZoneInfo('Asia/Kolkata')) + timedelta(days=max(7, config['policy']['lead_days'] + 2))).date()
        while day.isoformat() in config['policy']['closed_dates']:
            day += timedelta(days=1)

        def send(mid, text):
            started = time.perf_counter()
            r = client.post(f'/api/conversations/{cid}/messages', json={'message_id': mid, 'text': text})
            r.raise_for_status()
            state = State.model_validate_json(r.text)
            assert state.source == 'meta'
            assert state.turns[-1].reply_source == 'meta', 'Checked fallback used; do not call this a live-composed reply.'
            assert state == store.get(cid), 'HTTP response differs from persisted PostgreSQL state.'
            reread = client.get(f'/api/conversations/{cid}')
            reread.raise_for_status()
            assert State.model_validate_json(reread.text) == state
            report['steps'].append({'message': text, 'seconds': round(time.perf_counter() - started, 2), 'state': state.model_dump(mode='json')})
            Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))
            print(f'{mid}: {state.assistant_reply} [{report["steps"][-1]["seconds"]}s]', flush=True)
            return state

        base = config['products']['chocolate']['sizes']['1']
        total = base + config['customizations']['eggless'] + config['customizations']['floral_decoration']
        s = send('cake', f"Hi! I'd like one 1 kg chocolate cake for pickup on {day.isoformat()}.")
        assert s.offered_terms.total == base and not s.accepted_commitment
        s = send('extras', 'Please make it eggless with floral decoration.')
        assert s.offered_terms.total == total and not s.accepted_commitment
        s = send('accept', "Perfect, let's go ahead!")
        assert s.accepted_commitment.terms == s.offered_terms and s.accepted_commitment.terms.total == total
        assert s.production_snapshot is None and s.payment == 'unknown'
        accepted = s.accepted_commitment.model_copy(deep=True)
        s = send('unsupported', 'Actually, please change my cake to pistachio instead.')
        assert s.decision == 'needs_owner' and s.alerts
        assert s.accepted_commitment == accepted and s.offered_terms is None
        report['result'] = 'PASS: live interpretation and composition, repricing, acceptance, owner alert, PostgreSQL and HTTP consistency'
        Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(report['result'], flush=True)
        print(f'Isolated synthetic workspace: {bid}; conversation: {cid}', flush=True)


if __name__ == '__main__':
    main()
