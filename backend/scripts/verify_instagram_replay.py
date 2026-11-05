"""Opt-in genuine Muse inference through signed synthetic Instagram replay."""
import argparse,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
import httpx
p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--base',default='http://frontend:3000');p.add_argument('--business',default='shop-bb147585b244422e9c3de275eb4a528e');p.add_argument('--output',default='/tmp/instagram-replay.json');a=p.parse_args()
if not a.live:p.error('--live required; uses Meta inference, never Instagram delivery')
results=[]
with httpx.Client(base_url=a.base,headers={'X-Orderguard-Business':a.business},timeout=250) as c:
    r=c.post('/api/channels/instagram/replays',json={});r.raise_for_status();rid=r.json()['id']
    day=(datetime.now(timezone.utc)+timedelta(days=30)).date().isoformat()
    for mid,text in [('request',f'I need one bouquet of 12 red roses with ribbon wrapping and a handwritten greeting card, delivered to 18 Garden Lane, Indiranagar, Bengaluru on {day}.'),('accept',"Perfect, let's go ahead!")]:
        r=c.post(f'/api/channels/instagram/replays/{rid}/messages',json={'message_id':mid,'text':text});r.raise_for_status();result=r.json();results.append(result)
        Path(a.output).write_text(json.dumps(results,indent=2,ensure_ascii=False));print(mid,result['status'],result['transport'],result.get('latency_ms'),flush=True)
        assert result['status']=='processed' and result['state']['source']=='meta' and result['outbound']=='disabled' and not result['live_instagram']
    accepted=result['state']['accepted_commitment'];assert accepted and accepted['terms']['total']==959
    assert result['state']['payment']=='unknown' and not result['state']['production_snapshot']
    duplicate=c.post(f'/api/channels/instagram/replays/{rid}/messages',json={'message_id':'accept','text':"Perfect, let's go ahead!"});duplicate.raise_for_status();d=duplicate.json()
    assert d['state']==result['state'] and d['receipt']['receipts'][0]['duplicate']
    print('PASS: signed replay → real Muse → ₹959 accepted → duplicate unchanged. No Instagram send.',flush=True)
