"""Actual PostgreSQL; synthetic signed webhooks; explicitly mocked model/transport."""
from datetime import datetime,timedelta,timezone
import json
from uuid import uuid4
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select,delete,insert,update
from app.database import businesses,instagram_accounts,instagram_inbox,instagram_outbox
from app.bootstrap import seed
from app.store import Store
from app.provider import ModelError
from app.main import app,get_store,get_provider
from app import instagram as ig
from test_agent import MockProvider,DATE


def payload(account='12345',mid='message-1',text='What do you sell?',sender='67890',timestamp=None,attachments=None,echo=False):
    msg={'mid':mid,'text':text}
    if attachments is not None:msg['attachments']=attachments
    if echo:msg['is_echo']=True
    return json.dumps({'object':'instagram','entry':[{'id':account,'messaging':[{'sender':{'id':sender},'recipient':{'id':account},'timestamp':int((timestamp or datetime.now(timezone.utc)).timestamp()*1000),'message':msg}]}]}).encode()


@pytest.fixture
def account(store,monkeypatch):
    monkeypatch.setenv('INSTAGRAM_ACCESS_TOKEN_TEST','synthetic-secret-never-real')
    aid=str(int(uuid4().hex[:14],16))
    ig.register(store,aid,'INSTAGRAM_ACCESS_TOKEN_TEST')
    return aid


def receive(store,account,body):
    return ig.ingest(store,body,ig.sign(body,'test-app-secret'),'test-app-secret')


def test_valid_raw_signature_and_invalid_tampering(store,account):
    body=payload(account)
    sig=ig.sign(body,'test-app-secret')
    with pytest.raises(HTTPException):ig.ingest(store,body+b' ',sig,'test-app-secret')
    assert ig.status(store)['messages']==[]
    receive(store,account,body)
    assert ig.status(store)['messages'][0]['status']=='pending'
    assert store.all()==[]  # Webhook acknowledges without running the model.


@pytest.mark.parametrize('signature',[None,'sha1=bad','sha256=bad',''])
def test_missing_or_bad_signature_cannot_write(store,account,signature):
    with pytest.raises(HTTPException):ig.ingest(store,payload(account),signature,'secret')
    assert ig.status(store)['messages']==[]


def test_duplicate_delivery_and_conflicting_content(store,account):
    body=payload(account)
    receive(store,account,body)
    assert receive(store,account,body)['receipts'][0]['duplicate']
    other=json.loads(body);other['entry'][0]['messaging'][0]['message']['text']='Altered content'
    with pytest.raises(HTTPException):receive(store,account,json.dumps(other).encode())
    assert len(ig.status(store)['messages'])==1


def test_model_failure_backoff_and_idempotent_recovery(store,account):
    body=payload(account);r=receive(store,account,body);eid=r['receipts'][0]['id']
    class Unavailable(MockProvider):
        def interpret(self,c):raise ModelError('Synthetic outage')
    now=datetime.now(timezone.utc)
    failed=ig.process_one(store,Unavailable(),account,eid,now=now)
    assert failed['status']=='error' and store.all()==[]
    assert ig.process_one(store,MockProvider(),account,eid,now=now)['status']=='retry_wait'
    state=ig.process_one(store,MockProvider(),account,eid,now=now+timedelta(seconds=6))
    assert state['status']=='processed' and state['outbound']=='held_for_owner'
    saved=store.get(state['state']['id'])
    duplicate=ig.process_one(store,Unavailable(),account,eid,now=now+timedelta(seconds=10))
    assert duplicate['status']=='processed' and store.get(saved.id)==saved
    assert len(ig.status(store)['reply_drafts'])==1


def test_three_failures_require_review_without_order(store,account):
    r=receive(store,account,payload(account))
    class Fails(MockProvider):
        def interpret(self,c):raise ModelError('Unavailable')
    for n in (0,10,30):
        result=ig.process_one(store,Fails(),account,r['receipts'][0]['id'],now=datetime.now(timezone.utc)+timedelta(seconds=n))
    assert result['status']=='needs_review' and result['attempts']==3 and store.all()==[]


def test_account_business_routing_and_access_isolation(store,account):
    bid='test-'+uuid4().hex;seed(store.engine,bid);other=Store(store.engine.url,bid)
    try:
        r=receive(other,account,payload(account))  # Header-selected store cannot steal routing.
        assert ig.status(other)['messages']==[] and len(ig.status(store)['messages'])==1
        with pytest.raises(HTTPException):ig.process_one(other,MockProvider(),account,r['receipts'][0]['id'])
        with pytest.raises(HTTPException):ig.register(other,account,'INSTAGRAM_ACCESS_TOKEN_TEST')
        with pytest.raises(HTTPException):ig.disconnect(other,account)
    finally:
        with store.engine.begin() as conn:conn.execute(delete(businesses).where(businesses.c.id==bid))


def test_unknown_account_and_echo_do_not_invent_orders(store,account):
    assert receive(store,account,payload('9999999999999'))['received']==0
    assert receive(store,account,payload(account,echo=True))['received']==0
    assert store.all()==[] and ig.status(store)['messages']==[]


def test_attachment_requires_review_and_invalid_recipient_is_atomic(store,account):
    body=payload(account,text='',attachments=[{'type':'image','payload':{'url':'https://example.invalid/private.jpg'}}])
    r=receive(store,account,body)
    assert r['receipts'][0]['status']=='needs_review'
    assert store.all()==[]
    other=json.loads(payload(account,mid='bad-recipient'));other['entry'][0]['messaging'][0]['recipient']['id']='wrong'
    with pytest.raises(HTTPException):receive(store,account,json.dumps(other).encode())
    assert len(ig.status(store)['messages'])==1


def test_out_of_order_delivery_held_for_review(store,account):
    now=datetime.now(timezone.utc)
    first=receive(store,account,payload(account,timestamp=now))['receipts'][0]['id']
    result=ig.process_one(store,MockProvider(),account,first,now=now)
    saved=store.get(result['state']['id'])
    older=receive(store,account,payload(account,mid='older',timestamp=now-timedelta(minutes=1)))['receipts'][0]['id']
    assert ig.process_one(store,MockProvider(),account,older,now=now)['status']=='needs_review'
    assert store.get(saved.id)==saved


def test_disconnect_stops_processing_and_removes_only_token_reference(store,account):
    eid=receive(store,account,payload(account))['receipts'][0]['id']
    ig.disconnect(store,account)
    with pytest.raises(HTTPException):ig.process_one(store,MockProvider(),account,eid)
    assert len(ig.status(store)['messages'])==1 and not store.all()
    with store.engine.connect() as conn:
        assert conn.execute(select(instagram_accounts.c.token_env).where(instagram_accounts.c.id==account)).scalar_one() is None


def test_no_secret_returned_or_stored_as_plaintext(store,account):
    assert 'synthetic-secret-never-real' not in json.dumps(ig.status(store))
    with store.engine.connect() as conn:
        assert conn.execute(select(instagram_accounts.c.token_env).where(instagram_accounts.c.id==account)).scalar_one()=='INSTAGRAM_ACCESS_TOKEN_TEST'


def test_webhook_challenge_and_receive_disabled_by_default(store,monkeypatch):
    monkeypatch.setenv('INSTAGRAM_VERIFY_TOKEN','synthetic-verify')
    monkeypatch.delenv('INSTAGRAM_INGEST_ENABLED',raising=False)
    c=TestClient(app)
    assert c.get('/webhooks/instagram?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=42').status_code==403
    assert c.get('/webhooks/instagram?hub.mode=subscribe&hub.verify_token=synthetic-verify&hub.challenge=42').text=='42'
    assert c.post('/webhooks/instagram',content=payload()).status_code==503


def test_signed_replay_isolated_reset_and_duplicate(store):
    r=ig.start_replay(store)
    try:
        first=ig.replay_message(store,MockProvider(),r['id'],'Hello','m1')
        assert first['transport']=='signed_synthetic_replay' and not first['live_instagram'] and first['outbound']=='disabled'
        duplicate=ig.replay_message(store,MockProvider(),r['id'],'Hello','m1')
        assert duplicate['state']==first['state'] and duplicate['receipt']['receipts'][0]['duplicate']
        assert store.all()==[]
    finally:ig.reset_replays(store)
    with pytest.raises(HTTPException):ig.replay_state(store,r['id'])


def prepare_draft(store,account):
    eid=receive(store,account,payload(account))['receipts'][0]['id']
    ig.process_one(store,MockProvider(),account,eid)
    return eid


def test_transport_disabled_requires_explicit_authorization(store,account):
    eid=prepare_draft(store,account)
    with pytest.raises(HTTPException):ig.InstagramTransport().send_text(store,account,eid)


@pytest.mark.parametrize('code',[200,401,429,503])
def test_transport_contract_once_only_and_sanitized_failures(store,account,monkeypatch,code):
    eid=prepare_draft(store,account)
    monkeypatch.setenv('INSTAGRAM_OUTBOUND_ENABLED','true');monkeypatch.setenv('INSTAGRAM_API_VERSION','v26.0')
    calls=[]
    def handle(request):
        calls.append(request)
        assert request.url.host=='graph.instagram.com' and request.url.path==f'/v26.0/{account}/messages'
        assert json.loads(request.content)['recipient']['id']=='67890'
        return httpx.Response(code,json={'message_id':'synthetic-delivery'} if code==200 else {'error':{'message':'Not copied to UI'}})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result=ig.InstagramTransport(client).send_text(store,account,eid,explicitly_authorized=True)
        assert result['status']==('sent' if code==200 else 'delivery_unknown')
        with pytest.raises(HTTPException):ig.InstagramTransport(client).send_text(store,account,eid,explicitly_authorized=True)
    assert len(calls)==1


def test_transport_timeout_never_automatically_resends(store,account,monkeypatch):
    eid=prepare_draft(store,account)
    monkeypatch.setenv('INSTAGRAM_OUTBOUND_ENABLED','true');monkeypatch.setenv('INSTAGRAM_API_VERSION','v26.0')
    def fail(request):raise httpx.ReadTimeout('Synthetic timeout')
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        result=ig.InstagramTransport(client).send_text(store,account,eid,explicitly_authorized=True)
    assert result=={'status':'delivery_unknown','automatic_retry':False}


def test_outside_window_not_sent_even_when_authorized(store,account,monkeypatch):
    eid=prepare_draft(store,account)
    monkeypatch.setenv('INSTAGRAM_OUTBOUND_ENABLED','true')
    with pytest.raises(HTTPException):ig.InstagramTransport().send_text(store,account,eid,explicitly_authorized=True,now=datetime.now(timezone.utc)+timedelta(hours=25))


def test_signed_public_http_routes_by_account_not_client_header(store,account,monkeypatch):
    from app.main import get_channel_store
    app.dependency_overrides[get_channel_store]=lambda:store.reopen()
    monkeypatch.setenv('INSTAGRAM_INGEST_ENABLED','true');monkeypatch.setenv('INSTAGRAM_APP_SECRET','test-app-secret')
    body=payload(account)
    try:
        c=TestClient(app)
        r=c.post('/webhooks/instagram',content=body,headers={'X-Hub-Signature-256':ig.sign(body,'test-app-secret'),'X-Orderguard-Business':'another-business'})
        assert r.status_code==200 and r.json()['received']==1
        assert len(ig.status(store)['messages'])==1 and not store.all()
        assert c.post('/webhooks/instagram',content=body,headers={'X-Hub-Signature-256':'bad'}).status_code==403
    finally:app.dependency_overrides.clear()


def test_competing_processors_create_exactly_one_order_turn(store,account):
    from concurrent.futures import ThreadPoolExecutor
    eid=receive(store,account,payload(account))['receipts'][0]['id']
    def run(_):return ig.process_one(store.reopen(),MockProvider(),account,eid)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[1,2]))
    assert all(r['status']=='processed' for r in results)
    assert len(store.all())==1 and len(store.all()[0].turns)==2
    assert len(ig.status(store)['reply_drafts'])==1


def test_webhook_enqueue_does_not_wait_for_slow_model_business_lock(store,account):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    first=receive(store,account,payload(account))['receipts'][0]['id']
    started,release=Event(),Event()
    class Slow(MockProvider):
        def interpret(self,c):
            started.set()
            assert release.wait(10)
            return super().interpret(c)
    with ThreadPoolExecutor(max_workers=2) as pool:
        processing=pool.submit(ig.process_one,store.reopen(),Slow(),account,first)
        assert started.wait(5)
        try:
            incoming=pool.submit(receive,store.reopen(),account,payload(account,mid='another-customer',sender='11111'))
            assert incoming.result(timeout=3)['received']==1
        finally:release.set()
        assert processing.result(timeout=10)['status']=='processed'


def test_self_originating_message_cannot_start_reply_loop(store,account):
    assert receive(store,account,payload(account,sender=account))['received']==0
    assert store.all()==[]


def test_non_ascii_signature_is_a_rejection_not_server_error(store,account):
    with pytest.raises(HTTPException) as exc:ig.ingest(store,payload(account),'sha256=é','secret')
    assert exc.value.status_code==403 and not ig.status(store)['messages']
