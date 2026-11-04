"""Opt-in paid network test: run from backend with --live. Never prints credentials."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from app.provider import MetaProvider, ModelError
from app.engine import catalogue
from app.agent_models import State
from app.replies import plan_reply, compose_reply
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
if '--live' not in sys.argv:
    raise SystemExit('Opt in with --live; this makes two real Meta requests.')
try:
    result = MetaProvider().interpret({'business': catalogue(), 'state': {}, 'server_now': '2026-11-04T12:00:00+05:30', 'new_message': {'message_id': 'smoke1', 'text': 'What chocolate cakes do you make?'}})
    assert 'inquiry' in result.intents
    print('PASS: real Muse structured interpretation validated; source=meta')
    state = State(id='smoke', missing_fields=['product', 'size', 'quantity', 'date', 'fulfillment'])
    reply, source = compose_reply(MetaProvider(), plan_reply(state, catalogue(), 'clarify'), {'tone': 'Warm and brief', 'permitted_action': 'clarify', 'recent_conversation': []})
    assert source == 'meta', 'Live reply generation used fallback'
    print('PASS: real Muse customer reply validated; reply_source=meta')
    print(reply)
except ModelError as exc:
    raise SystemExit(str(exc)) from None
