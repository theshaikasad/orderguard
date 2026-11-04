import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
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



def get_store():
    return Store()


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
