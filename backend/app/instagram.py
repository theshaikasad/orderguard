"""Instagram text adapter. Webhooks enqueue; workers draft; no automatic sends.

Live account/token registration is a server-side operation. Client-selected
business headers never route webhooks. Replay uses a separate isolated account.
No OAuth completion or account permissions are claimed by this adapter.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime,timedelta,timezone
from time import perf_counter
from uuid import uuid4
import httpx
from fastapi import HTTPException
from sqlalchemy import select,insert,update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .database import businesses,configuration_versions,instagram_accounts as accounts,instagram_inbox as inbox,instagram_outbox as outbox
from .agent_models import Incoming
from .provider import ModelError
from .store import Store
from .engine import process

MAX_BODY=128*1024


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def sign(body,secret):
    return 'sha256='+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()


def verify(body,signature,secret):
    if not secret:
        raise HTTPException(503,'Instagram webhook secret is not configured.')
    if len(body)>MAX_BODY:
        raise HTTPException(413,'Webhook payload exceeds the supported size.')
    if not signature or not re.fullmatch(r'sha256=[0-9a-f]{64}',signature) or not hmac.compare_digest(sign(body,secret),signature):
        raise HTTPException(403,'Invalid webhook signature.')


def normalize(body):
    try:
        data=json.loads(body)
        if data['object']!='instagram' or not isinstance(data['entry'],list):
            raise ValueError()
        result=[]
        for entry in data['entry']:
            account=str(entry['id'])
            if len(account)>100:
                raise ValueError()
            for message in entry.get('messaging',[]):
                # Echoes/receipts cannot become customer turns or trigger loops.
                if not message.get('message') or message['message'].get('is_echo'):
                    continue
                if str(message['recipient']['id'])!=account:
                    raise ValueError()
                sender=str(message['sender']['id'])
                if sender==account:
                    continue
                mid=str(message['message']['mid'])
                if not sender or not mid or len(sender)>100 or len(mid)>1000:
                    raise ValueError()
                timestamp=datetime.fromtimestamp(message['timestamp']/1000,tz=timezone.utc)
                text=message['message'].get('text')
                attachments=message['message'].get('attachments',[])
                incoming=Incoming(message_id='ig-'+digest(mid),text=text if isinstance(text,str) and text.strip() else '[Unsupported attachment: owner review required]',timestamp=timestamp)
                result.append({'account_id':account,'id':digest(mid),'sender_id':sender,
                    'conversation_id':'ig-'+digest(account+':'+sender)[:48],
                    'incoming':incoming.model_dump(mode='json'),'unsupported':bool(attachments) or not isinstance(text,str) or not text.strip()})
        if len(result)>100:
            raise ValueError()
        return result
    except (ValueError,TypeError,KeyError,OverflowError,OSError,AttributeError):
        raise HTTPException(422,'Unsupported Instagram text webhook payload.') from None


def register(store,account_id,token_env=None,mode='live'):
    """Server-side registration only. Never accepts a plaintext credential."""
    if mode=='live':
        if not re.fullmatch(r'[0-9]{1,40}',account_id):
            raise HTTPException(422,'Use the professional account numeric ID.')
        if not re.fullmatch(r'INSTAGRAM_ACCESS_TOKEN_[A-Z0-9_]{1,80}',token_env or '') or not os.getenv(token_env):
            raise HTTPException(422,'Configure a dedicated server-only Instagram token variable first.')
    with store.transaction():
        existing=store._session.execute(select(accounts).where(accounts.c.id==account_id).with_for_update()).mappings().first()
        if existing and existing['business_id']!=store.business_id:
            raise HTTPException(409,'That Instagram account belongs to another business.')
        values=dict(business_id=store.business_id,mode=mode,status='configured_unverified' if mode=='live' else 'replay',token_env=token_env)
        if existing:
            if existing['mode']!=mode:
                raise HTTPException(409,'Account mode cannot change.')
            store._session.execute(update(accounts).where(accounts.c.id==account_id).values(**values))
        else:
            store._session.execute(insert(accounts).values(id=account_id,**values))


def ingest(store,body,signature,secret,mode='live',expected_account=None):
    verify(body,signature,secret)
    messages=normalize(body)  # Validate the complete batch before storing any item.
    receipts=[]
    for msg in messages:
        if expected_account and msg['account_id']!=expected_account:
            raise HTTPException(403,'Replay cannot target another account.')
        with store.engine.connect() as conn:
            account=conn.execute(select(accounts).where(accounts.c.id==msg['account_id'],accounts.c.mode==mode,accounts.c.status!='disconnected')).mappings().first()
        if not account:
            continue  # Unknown/unconnected accounts never invent a business or customer.
        if mode=='replay' and account['business_id']!=store.business_id:
            raise HTTPException(403,'Replay account belongs to another business.')
        scoped=Store(store.engine.url,account['business_id'])
        with scoped.engine.begin() as connection:
            active=connection.execute(select(accounts).where(accounts.c.id==msg['account_id'],accounts.c.business_id==scoped.business_id).with_for_update()).mappings().one()
            if active['status']=='disconnected':
                continue
            fingerprint=digest(json.dumps({k:msg[k] for k in ('sender_id','conversation_id','incoming','unsupported')},sort_keys=True))
            old=connection.execute(select(inbox).where(inbox.c.account_id==msg['account_id'],inbox.c.id==msg['id'])).mappings().first()
            if old:
                if old['content_hash']!=fingerprint:
                    raise HTTPException(409,'Duplicate message ID has conflicting content.')
                receipts.append({'id':msg['id'],'duplicate':True,'status':old['status']})
                continue
            values={k:msg[k] for k in ('account_id','id','sender_id','conversation_id','incoming')}
            status='needs_review' if msg['unsupported'] else 'pending'
            connection.execute(insert(inbox).values(**values,business_id=scoped.business_id,content_hash=fingerprint,status=status,
                error='Media is not interpreted; owner review required.' if msg['unsupported'] else None,attempts=0))
            receipts.append({'id':msg['id'],'duplicate':False,'status':status})
    return {'received':len(receipts),'receipts':receipts,'transport':mode,'outbound':'disabled'}


def process_one(store,provider,account_id,event_id,now=None):
    now=now or datetime.now(timezone.utc)
    started=perf_counter()
    with store.transaction():
        row=store._session.execute(select(inbox).where(inbox.c.business_id==store.business_id,inbox.c.account_id==account_id,inbox.c.id==event_id).with_for_update()).mappings().first()
        if not row:
            raise HTTPException(404,'Message not found in this business.')
        account=store._session.execute(select(accounts).where(accounts.c.id==account_id,accounts.c.business_id==store.business_id)).mappings().one()
        if account['status']=='disconnected':
            raise HTTPException(409,'Account is disconnected; processing is paused.')
        if row['status'] not in ('pending','error') or row['attempts']>=3:
            return {'status':row['status'],'attempts':row['attempts']}
        if row['next_attempt_at'] and row['next_attempt_at']>now:
            return {'status':'retry_wait','attempts':row['attempts']}
        incoming=Incoming.model_validate_json(json.dumps(row['incoming']))
        attempts=row['attempts']+1
        try:
            state=process(store,provider,row['conversation_id'],incoming,now=now)
        except (ModelError,HTTPException) as exc:
            conflict=isinstance(exc,HTTPException) and exc.status_code in (409,422)
            status='needs_review' if conflict or attempts>=3 else 'error'
            # No order mutation is committed on model failure. Keep a bounded retry record.
            detail='Message requires owner review.' if conflict else 'Model unavailable or invalid output; safe retry pending.'
            store._session.execute(update(inbox).where(inbox.c.account_id==account_id,inbox.c.id==event_id).values(status=status,attempts=attempts,error=detail,next_attempt_at=now+timedelta(seconds=min(60,5*2**(attempts-1)))))
            return {'status':status,'attempts':attempts,'error':detail,'latency_ms':round((perf_counter()-started)*1000)}
        last_customer_at=incoming.timestamp
        held='replay_only' if account['mode']=='replay' else 'held_for_owner'
        if now-last_customer_at>timedelta(hours=24):
            held='outside_window'
        store._session.execute(pg_insert(outbox).values(account_id=account_id,event_id=event_id,business_id=store.business_id,
            recipient_id=row['sender_id'],text=state.assistant_reply or '',status=held,last_customer_at=last_customer_at).on_conflict_do_nothing())
        store._session.execute(update(inbox).where(inbox.c.account_id==account_id,inbox.c.id==event_id).values(status='processed',attempts=attempts,error=None,next_attempt_at=None))
        return {'status':'processed','attempts':attempts,'transport':account['mode'],'outbound':held,
                'state':state.model_dump(mode='json'),'latency_ms':round((perf_counter()-started)*1000),'inference':getattr(provider,'metrics',[])}


def status(store):
    with store._read() as session:
        connected=session.execute(select(accounts.c.id,accounts.c.mode,accounts.c.status).where(accounts.c.business_id==store.business_id)).mappings().all()
        incoming=session.execute(select(inbox.c.account_id,inbox.c.id,inbox.c.status,inbox.c.attempts,inbox.c.error,inbox.c.conversation_id).where(inbox.c.business_id==store.business_id)).mappings().all()
        drafts=session.execute(select(outbox.c.event_id,outbox.c.text,outbox.c.status).where(outbox.c.business_id==store.business_id)).mappings().all()
    return {'accounts':[dict(r) for r in connected],'messages':[dict(r) for r in incoming],'reply_drafts':[dict(r) for r in drafts],
        'live_inbound_enabled':os.getenv('INSTAGRAM_INGEST_ENABLED')=='true','outbound_enabled':False,
        'replays':replay_list(store), 'oauth':'not_implemented','note':'Local adapter only. Live account authorization and permissions are not verified.'}


def disconnect(store,account_id):
    with store.transaction():
        result=store._session.execute(update(accounts).where(accounts.c.business_id==store.business_id,accounts.c.id==account_id).values(status='disconnected',token_env=None))
        if not result.rowcount:
            raise HTTPException(404,'Account not found in this business.')
    return status(store)


class InstagramTransport:
    """No automatic resend after uncertain network outcomes. No runtime send route."""
    def __init__(self,client=None):
        self.client=client

    def send_text(self,store,account_id,event_id,*,explicitly_authorized=False,now=None):
        if not explicitly_authorized or os.getenv('INSTAGRAM_OUTBOUND_ENABLED')!='true':
            raise HTTPException(403,'Real customer sending is disabled; explicit authorization is required.')
        now=now or datetime.now(timezone.utc)
        with store.transaction():
            row=store._session.execute(select(outbox).where(outbox.c.business_id==store.business_id,outbox.c.account_id==account_id,outbox.c.event_id==event_id).with_for_update()).mappings().first()
            account=store._session.execute(select(accounts).where(accounts.c.business_id==store.business_id,accounts.c.id==account_id)).mappings().first()
            if not row or not account or account['mode']!='live' or account['status']!='configured_unverified':
                raise HTTPException(409,'A configured live account and held reply are required.')
            if row['status']!='held_for_owner' or now-row['last_customer_at']>timedelta(hours=24):
                raise HTTPException(409,'Reply is already handled or outside the conservative 24-hour window.')
            version=os.getenv('INSTAGRAM_API_VERSION','')
            token=os.getenv(account['token_env'] or '')
            if not re.fullmatch(r'v[0-9]{2}\.0',version) or not token:
                raise HTTPException(503,'Configure a verified API version and runtime token.')
            # Mark uncertain before any external effect, and commit BEFORE sending.
            store._session.execute(update(outbox).where(outbox.c.account_id==account_id,outbox.c.event_id==event_id).values(status='delivery_unknown'))
            recipient,text=row['recipient_id'],row['text']
        client=self.client or httpx.Client(timeout=15)
        try:
            response=client.post(f'https://graph.instagram.com/{version}/{account_id}/messages',headers={'Authorization':'Bearer '+token},json={'recipient':{'id':recipient},'message':{'text':text}})
            payload=response.json()
            ok=response.status_code==200 and isinstance(payload,dict) and isinstance(payload.get('message_id'),str) and bool(payload['message_id'])
            final='sent' if ok else 'delivery_unknown'
            if response.status_code in (401,403):
                with store.transaction():store._session.execute(update(accounts).where(accounts.c.id==account_id,accounts.c.business_id==store.business_id).values(status='reauthorization_required'))
        except (httpx.HTTPError,ValueError,TypeError):
            final='delivery_unknown'
        finally:
            if not self.client:client.close()
        with store.transaction():
            store._session.execute(update(outbox).where(outbox.c.account_id==account_id,outbox.c.event_id==event_id,outbox.c.business_id==store.business_id).values(status=final))
        return {'status':final,'automatic_retry':False}


def start_replay(store):
    """Clone published rules into a synthetic namespace; never consumes seller capacity."""
    if not store.runtime()[0]:
        raise HTTPException(409,'Publish a business configuration before replaying messages.')
    config=store.catalogue()
    bid='lab-instagram-'+uuid4().hex
    account='replay-'+uuid4().hex
    config['id']=bid
    with store.engine.begin() as conn:
        conn.execute(insert(businesses).values(id=bid,config=config,active_version=1,paused=False))
        conn.execute(insert(configuration_versions).values(business_id=bid,version=1,config=config))
        # A source-owned mapping allows only the originating workspace to manage the replay.
        conn.execute(insert(replay_sessions).values(id=account,business_id=store.business_id,lab_business_id=bid))
    lab=Store(store.engine.url,bid)
    register(lab,account,mode='replay')
    return {'id':account,'transport':'signed_synthetic_replay','outbound':'disabled'}


from .database import instagram_replays as replay_sessions


def replay_message(store,provider,replay_id,text,message_id):
    with store.transaction():
        return _replay_message(store,provider,replay_id,text,message_id)


def _replay_message(store,provider,replay_id,text,message_id):
    with store._read() as session:
        row=session.execute(select(replay_sessions).where(replay_sessions.c.business_id==store.business_id,replay_sessions.c.id==replay_id)).mappings().first()
    if not row:
        raise HTTPException(404,'Replay not found in this business.')
    lab=Store(store.engine.url,row['lab_business_id'])
    # Stable timestamp for duplicate replay IDs; conflicting content is rejected by ingest.
    eid=digest(message_id)
    with lab._read() as session:
        existing=session.execute(select(inbox.c.incoming).where(inbox.c.account_id==replay_id,inbox.c.id==eid)).scalar_one_or_none()
    timestamp=datetime.fromisoformat(existing['timestamp'].replace('Z','+00:00')) if existing else datetime.now(timezone.utc)
    body=json.dumps({'object':'instagram','entry':[{'id':replay_id,'messaging':[{'sender':{'id':'fictional-flower-customer'},'recipient':{'id':replay_id},'timestamp':int(timestamp.timestamp()*1000),'message':{'mid':message_id,'text':text}}]}]}).encode()
    key=secrets.token_hex(32)
    receipt=ingest(lab,body,sign(body,key),key,mode='replay',expected_account=replay_id)
    result=process_one(lab,provider,replay_id,eid)
    if 'state' not in result:
        with lab._read() as session:
            cid=session.execute(select(inbox.c.conversation_id).where(inbox.c.account_id==replay_id,inbox.c.id==eid)).scalar_one()
        result['state']=lab.get(cid).model_dump(mode='json')
    return {**result,'receipt':receipt,'transport':'signed_synthetic_replay','live_instagram':False,'outbound':'disabled'}


def replay_list(store):
    with store._read() as session:
        return session.execute(select(replay_sessions.c.id).where(replay_sessions.c.business_id==store.business_id)).scalars().all()


def reset_replays(store):
    from sqlalchemy import delete
    with store.transaction():
        ids=store._session.execute(select(replay_sessions.c.lab_business_id).where(replay_sessions.c.business_id==store.business_id)).scalars().all()
        if ids:store._session.execute(delete(businesses).where(businesses.c.id.in_(ids)))
    return {'status':'reset','scope':'synthetic_instagram_replays_only'}


def replay_state(store,rid):
    with store._read() as session:
        bid=session.execute(select(replay_sessions.c.lab_business_id).where(replay_sessions.c.id==rid,replay_sessions.c.business_id==store.business_id)).scalar_one_or_none()
    if not bid:raise HTTPException(404,'Replay not found in this business.')
    lab=Store(store.engine.url,bid)
    return {'transport':'signed_synthetic_replay','states':[s.model_dump(mode='json') for s in lab.all()],**status(lab)}
