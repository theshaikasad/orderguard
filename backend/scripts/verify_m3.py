"""Opt-in real Muse onboarding and all six scenarios through the HTTP API.

Creates synthetic businesses and isolated lab copies; never resets seller orders.
"""
import argparse
import json
import sys
import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--base',default='http://127.0.0.1:8000')
    parser.add_argument('--scenarios',default='ABECDF')
    args=parser.parse_args()
    if not args.live:
        parser.error('Real Muse calls require --live')
    with httpx.Client(base_url=args.base,timeout=180) as client:
        def request(method,path,**kw):
            response=client.request(method,path,**kw)
            if not response.is_success:
                raise RuntimeError(f'{path}: HTTP {response.status_code}: {response.text[:300]}')
            return response.json()
        bid=request('POST','/api/businesses',json={})['id']
        client.headers['X-Orderguard-Business']=bid
        print(f'Synthetic onboarding business: {bid}',flush=True)
        description=('My business is Bloom Studio, a florist in Bengaluru. We sell a classic rose bouquet for ₹900 per bouquet. '
            'We offer pickup for free. Our minimum preparation time is 48 hours and we can handle 5 bouquets daily. '
            'Eggless costs ₹100 extra. Our deposit is 50 percent. We are open 10 AM to 6 PM IST. '
            'Cancellations or changes after acceptance need owner approval. Dietary requirements need owner review. '
            'Escalate unsupported requests and exact pickup times to me. Reply in warm, brief English.')
        draft=request('POST','/api/settings/chat',json={'revision':0,'text':description})
        assert draft['revision']==1 and draft['history'][-1]['source']=='meta'
        assert draft['config']['name']=='Bloom Studio'
        assert draft['config']['policy']['daily_capacity']==5
        assert 'eggless' not in draft['config']['customizations']
        assert draft['questions'], 'Ambiguous extra requires clarification'
        print('LIVE onboarding: sourced draft saved, ambiguous charge not applied, active config unchanged.',flush=True)
        # Explicit seller corrections of remaining model questions, using native manual edit API.
        config=draft['config']
        config.update(name='Bloom Studio',category='Florist',location='Bengaluru, India',commercial_reviewed=True)
        config['products']={'roses':{'name':'Rose bouquet','unit':'bouquet','sizes':{'classic':900}}}
        config['fulfillment']={'pickup':0}
        config['policy'].update(hours='10:00–18:00 IST',lead_hours=48,daily_capacity=5,deposit_percent=50,
            cancellation='Changes and cancellations after acceptance require owner approval.',
            dietary='Dietary or safety requests require owner review.',escalation='Unsupported requests and exact slots need owner approval.')
        draft=request('POST','/api/settings/draft',json={'revision':draft['revision'],'config':config,'questions':[]})
        active=request('POST','/api/settings/publish',json={'revision':draft['revision'],'reviewed':True})
        assert active['active_version']==1
        request('POST','/api/settings/pause',json={'paused':False})
        from datetime import datetime,timedelta,timezone
        day=(datetime.now(timezone.utc)+timedelta(days=10)).date().isoformat()
        state=request('POST','/api/conversations/m3-live-florist/messages',json={'message_id':'inquiry',
            'text':f'I would like 1 Rose bouquet, classic size, on {day}, for pickup.'})
        assert state['offered_terms']['total']==900 and state['source']=='meta'
        assert 'cake' not in state['assistant_reply'].lower()
        state=request('POST','/api/conversations/m3-live-florist/messages',json={'message_id':'accept','text':'I confirm'})
        assert state['accepted_commitment']['terms']['total']==900
        print('LIVE non-bakery agent: published florist rules → ₹900 quote → acceptance.',flush=True)
        # Demo bakery scenario runs are independent copies; actual bakery orders untouched.
        client.headers['X-Orderguard-Business']='little-crumb-v1'
        results=[]
        for scenario in args.scenarios:
            run=request('POST','/api/lab/runs',json={'scenario':scenario})
            print(f'Scenario {scenario} run {run["id"]}',flush=True)
            while run['status']=='running':
                run=request('POST',f'/api/lab/runs/{run["id"]}/step',json={'step':run['step']})
                last=run['observations'][-1]
                print(f'  Step {run["step"]}: {last["latency_ms"]} ms; error={last["error"]}',flush=True)
            print(json.dumps({'scenario':scenario,'status':run['status'],'mode':run['mode'],'checks':run['checks']},ensure_ascii=False),flush=True)
            results.append(run)
        if any(r['status']!='passed' or r['mode']!='meta' for r in results):
            sys.exit(1)


if __name__=='__main__':
    main()
