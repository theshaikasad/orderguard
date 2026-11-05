import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from .models import Demo

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures' / 'bakery_demo.json'
app = FastAPI(title='OrderGuard', version='0.2.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[v.strip() for v in os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',') if v.strip()],
    allow_methods=['GET', 'POST'],
    allow_headers=['Accept', 'Content-Type'],
)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/v1/demo', response_model=Demo)
def demo() -> Demo:
    return Demo.model_validate_json(FIXTURE.read_text())

# PostgreSQL transactions serialize shared business capacity across processes.
from typing import Annotated
from fastapi import Depends, HTTPException, Path as ApiPath
from .agent_models import Incoming, State, ProductionRequest, Turn, Business, ResetResponse
from .provider import MetaProvider, ModelError
from .store import Store
from .engine import process, event
from datetime import datetime, timezone



def get_store(x_orderguard_business: str | None = Header(default=None, pattern=r'^[a-zA-Z0-9_-]{1,80}$')):
    store = Store(business=x_orderguard_business)
    with store._read() as session:
        from .database import businesses
        from sqlalchemy import select
        if not session.execute(select(businesses.c.id).where(businesses.c.id == store.business_id, ~businesses.c.id.like('lab-%'))).first():
            raise HTTPException(404, 'Business workspace not found.')
    return store


def get_provider():
    return MetaProvider()


ConversationId = Annotated[str, ApiPath(pattern=r'^[a-zA-Z0-9_-]{1,60}$')]


@app.get('/api/business/config', response_model=Business)
def business_config(store=Depends(get_store)):
    return Business.model_validate(store.catalogue())


@app.get('/api/conversations/{cid}', response_model=State)
def conversation(cid: ConversationId, store=Depends(get_store)):
    return store.get(cid)


@app.post('/api/conversations/{cid}/messages', response_model=State)
def message(cid: ConversationId, body: Incoming, store=Depends(get_store), provider=Depends(get_provider)):
    with store.transaction():
        try:
            return process(store, provider, cid, body)
        except ModelError as exc:
            raise HTTPException(503, str(exc)) from None


@app.post('/api/conversations/{cid}/owner-action', response_model=State)
def owner_action(cid: ConversationId, body: ProductionRequest, store=Depends(get_store)):
    """Explicit local simulator owner action, never callable by the model."""
    with store.transaction():
        s = store.get(cid)
        if not s.accepted_commitment or s.decision == 'needs_owner' or s.payment != 'unknown':
            raise HTTPException(409, 'Only an accepted plan without pending review can enter simulated production.')
        if s.production_snapshot:
            return s
        s.production_snapshot = s.accepted_commitment.model_copy(deep=True)
        s.status = 'in_production'
        mid = f'owner-{len(s.events)+1}'
        s.turns.append(Turn(id=mid, sender='owner', timestamp=datetime.now(timezone.utc),
                            text='Owner started simulated production. Payment has not been verified.', source=s.source))
        event(s, 'production_started', mid, 'Frozen accepted commitment')
        store.save(s)
        return s


@app.post('/api/demo/reset', response_model=ResetResponse)
def reset(store=Depends(get_store)) -> dict[str, str]:
    with store.transaction():
        store.reset()
    return {'status': 'reset'}


@app.get('/ready')
def ready(store=Depends(get_store)):
    # Validates connectivity, schema and the configured business seed.
    store.catalogue()
    return {'status': 'ready'}

# Local workspace selection, not authentication. Never expose this service publicly.
from fastapi import Header
from pydantic import BaseModel, Field
from sqlalchemy import select, insert, update
from .database import businesses, scenario_runs
from .configuration import (settings, save_draft, onboarding, publish, empty_business,
                            DraftSave, SetupMessage, Publish, Pause)


@app.get('/api/businesses')
def list_businesses(store=Depends(get_store)):
    with store._read() as session:
        rows = session.execute(select(businesses.c.id, businesses.c.config, businesses.c.active_version)
            .where(~businesses.c.id.like('lab-%'), ~businesses.c.id.like('test-%'))).all()
        return [{'id':r.id, 'name':r.config['name'] or 'New business', 'active': bool(r.active_version)} for r in rows]


@app.post('/api/businesses')
def create_business(store=Depends(get_store)):
    from uuid import uuid4
    bid = 'shop-' + uuid4().hex
    config = empty_business(bid).model_dump(mode='json')
    with store.engine.begin() as conn:
        conn.execute(insert(businesses).values(id=bid, config=config, active_version=0, paused=True))
    return {'id':bid}


@app.get('/api/settings')
def get_settings(store=Depends(get_store)):
    return settings(store)


@app.post('/api/settings/draft')
def update_settings(body: DraftSave, store=Depends(get_store)):
    return save_draft(store, body)


@app.post('/api/settings/chat')
def setup_chat(body: SetupMessage, store=Depends(get_store), provider=Depends(get_provider)):
    try:
        return onboarding(store, provider, body)
    except ModelError as exc:
        raise HTTPException(503, str(exc)) from None


@app.post('/api/settings/publish')
def activate_settings(body: Publish, store=Depends(get_store)):
    return publish(store, body)


@app.post('/api/settings/pause')
def pause_settings(body: Pause, store=Depends(get_store)):
    with store.transaction():
        store._session.execute(update(businesses).where(businesses.c.id == store.business_id).values(paused=body.paused))
    return settings(store)


@app.get('/api/overview')
def overview(store=Depends(get_store)):
    states = store.all()
    config = store.catalogue()
    commitments = [s for s in states if s.accepted_commitment]
    days = {}
    for s in commitments:
        spec = s.accepted_commitment.terms.spec
        day = spec['date'].value
        days[day] = days.get(day, 0) + (1 if config['policy'].get('capacity_unit')=='orders' else int(spec['quantity'].value))
    return {'active_orders': len(commitments), 'attention': sum(s.decision == 'needs_owner' for s in states),
            'capacity': config['policy']['daily_capacity'], 'reserved_by_date': days,
            'orders': [s.model_dump(mode='json') for s in states]}

from . import scenarios

class ScenarioStart(BaseModel):
    scenario: str = Field(pattern='^[A-H]$')


@app.get('/api/lab')
def lab_index(store=Depends(get_store)):
    with store._read() as session:
        results = session.execute(select(scenario_runs.c.result).where(scenario_runs.c.business_id==store.business_id)).scalars().all()
    return {'scenarios':scenarios.SCENARIOS,'runs':results}


@app.post('/api/lab/runs')
def lab_start(body: ScenarioStart, store=Depends(get_store)):
    return scenarios.start(store, body.scenario)


class ScenarioStep(BaseModel):
    step: int = Field(ge=0)


@app.post('/api/lab/runs/{rid}/step')
def lab_step(rid: str, body: ScenarioStep, store=Depends(get_store), provider=Depends(get_provider)):
    return scenarios.advance(store, provider, rid, body.step)


@app.post('/api/lab/reset')
def lab_reset(store=Depends(get_store)):
    return scenarios.reset(store)


@app.middleware('http')
async def database_timing(request, call_next):
    from .telemetry import sql_metrics
    measurements = []
    token = sql_metrics.set(measurements)
    try:
        response = await call_next(request)
        response.headers['Server-Timing'] = f'db;dur={sum(measurements):.2f}'
        response.headers['X-Orderguard-Database-Statements'] = str(len(measurements))
        return response
    finally:
        sql_metrics.reset(token)

from fastapi import Request
from fastapi.responses import PlainTextResponse
from . import instagram


@app.get('/webhooks/instagram')
def instagram_challenge(request: Request):
    import hmac
    expected=os.getenv('INSTAGRAM_VERIFY_TOKEN','')
    if not expected:
        raise HTTPException(503,'Instagram verification is not configured.')
    if request.query_params.get('hub.mode')!='subscribe' or not hmac.compare_digest(request.query_params.get('hub.verify_token','').encode(),expected.encode()):
        raise HTTPException(403,'Invalid verification token.')
    challenge=request.query_params.get('hub.challenge','')
    if not challenge or len(challenge)>256:
        raise HTTPException(422,'Invalid challenge.')
    return PlainTextResponse(challenge)


def get_channel_store():
    return Store()


@app.post('/webhooks/instagram')
async def instagram_webhook(request: Request, store=Depends(get_channel_store)):
    # No client business header is accepted. Verified account ownership routes the event.
    if os.getenv('INSTAGRAM_INGEST_ENABLED')!='true':
        raise HTTPException(503,'Live Instagram ingestion is disabled.')
    from starlette.concurrency import run_in_threadpool
    chunks=[]
    size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>instagram.MAX_BODY:
            raise HTTPException(413,'Webhook payload exceeds the supported size.')
        chunks.append(chunk)
    body=b''.join(chunks)
    return await run_in_threadpool(instagram.ingest,store,body,request.headers.get('x-hub-signature-256'),os.getenv('INSTAGRAM_APP_SECRET',''))


@app.get('/api/channels/instagram')
def instagram_status(store=Depends(get_store)):
    return instagram.status(store)


@app.post('/api/channels/instagram/replays')
def instagram_replay_start(store=Depends(get_store)):
    return instagram.start_replay(store)


class ReplayMessage(BaseModel):
    message_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    text: str = Field(min_length=1,max_length=4000)


@app.post('/api/channels/instagram/replays/{rid}/messages')
def instagram_replay_turn(rid: str,body: ReplayMessage,store=Depends(get_store),provider=Depends(get_provider)):
    return instagram.replay_message(store,provider,rid,body.text,body.message_id)


@app.get('/api/channels/instagram/replays/{rid}')
def instagram_replay_read(rid: str,store=Depends(get_store)):
    return instagram.replay_state(store,rid)


@app.post('/api/channels/instagram/replays-reset')
def instagram_replay_reset(store=Depends(get_store)):
    return instagram.reset_replays(store)


@app.post('/api/channels/instagram/accounts/{aid}/disconnect')
def instagram_disconnect(aid: str,store=Depends(get_store)):
    return instagram.disconnect(store,aid)
