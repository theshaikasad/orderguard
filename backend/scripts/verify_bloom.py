"""Opt-in synthetic Bloom & Co. HTTP + real Muse + PostgreSQL acceptance test.

No customer/model result is mocked. Failure injection is explicitly reported.
Use --business to continue a business already onboarded/published in the UI.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import statistics
from time import perf_counter
import sys
import httpx
from sqlalchemy import select
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database import get_engine,businesses,conversations,configuration_versions,orders

DESCRIPTION="""Hey! I run Bloom & Co., a small flower shop.
We sell a bouquet of 12 red roses for ₹699 and
a mixed flower bouquet for ₹499.

Gift wrapping with a ribbon costs ₹50 extra.
A handwritten greeting card costs ₹30 extra.

Pickup is free.
Delivery costs ₹80 in our service area.
We require at least 24 hours' notice.
We can fulfill only 2 orders per day.

Our prices are fixed and we don't offer discounts.
Please keep replies friendly and casual."""


def main():
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--base',default='http://frontend:3000');p.add_argument('--business');p.add_argument('--output',default='/tmp/bloom-report.json');args=p.parse_args()
    if not args.live:p.error('--live required; makes real Meta calls')
    measurements=[];checks=[];successful_deliveries=set();report={'business_id':None,'checks':checks,'timings':measurements,'scenarios':[]}
    client=httpx.Client(base_url=args.base,timeout=250)
    def call(method,path,body=None,expect=200):
        began=perf_counter();r=client.request(method,path,json=body)
        ms=round((perf_counter()-began)*1000)
        data=r.json()
        timing={'path':path,'http_status':r.status_code,'end_to_end_ms':ms,'database':r.headers.get('server-timing'), 'sql_statements':r.headers.get('x-orderguard-database-statements')}
        if isinstance(data,dict):timing.update(data.get('last_turn_metrics',{}))
        identity=(path,body.get('message_id')) if isinstance(body,dict) and 'message_id' in body else None
        timing['duplicate_delivery']=identity in successful_deliveries if identity else False
        if identity and r.status_code==200:successful_deliveries.add(identity)
        measurements.append(timing)
        print(f'{path}: HTTP {r.status_code}, {ms} ms',flush=True)
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
        if r.status_code!=expect:raise AssertionError(f'{path} HTTP {r.status_code}: {str(data)[:400]}')
        return data
    def check(name,ok,actual):
        checks.append({'test':name,'passed':bool(ok),'actual':actual});print(checks[-1],flush=True)
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
        if not ok:raise AssertionError(name)
    report_path=Path(args.output)
    try:
        bid=args.business or call('POST','/api/businesses',{})['id'];report['business_id']=bid
        client.headers['X-Orderguard-Business']=bid
        if not args.business:
            d=call('POST','/api/settings/chat',{'revision':0,'text':DESCRIPTION})
            check('1a live setup extraction',d['history'][-1]['source']=='meta' and d['config']['name']=='Bloom & Co.',d['config'])
            # Seller clarifies genuinely missing rules; no invented defaults become active.
            followup=('We are in Bengaluru, India. Both extras are per bouquet: ribbon wrapping is ₹50 per item and the handwritten greeting card is ₹30 per item. '
                'Pickup is free, with no charge. Delivery is ₹80 per order to Indiranagar only. '
                'We are open 10 AM to 6 PM IST, with no holidays currently planned. '
                'Minimum preparation time is 24 hours. Capacity is 2 orders per day. No deposit is required, 0 percent. '
                'Changes and cancellations after acceptance need owner approval; no automatic refunds. '
                'Any safety/dietary issue, unsupported request, exact delivery slot or accepted change needs owner review. '
                'Please use friendly casual English.')
            d=call('POST','/api/settings/chat',{'revision':d['revision'],'text':followup})
            c=d['config'];c['commercial_reviewed']=True
            # Explicit seller policy edits, based on the follow-up above. Model omission is not invented authority.
            c['policy'].update(cancellation='Changes and cancellations after acceptance need owner approval; no automatic refunds.', dietary='Any safety or dietary issue needs owner review.', escalation='Unsupported requests, exact delivery slots and accepted changes need owner review.')
            extra_values=list(c['customizations'].values())+list(c['addons'].values())
            check('1b extracted commercial rules',sorted(n for prod in c['products'].values() for n in prod['sizes'].values())==[499,699]
                and sorted(extra_values)==[30,50] and c['policy']['daily_capacity']==2 and c['policy']['lead_hours']==24
                and sorted(c['fulfillment'].values())==[0,80],c)
            d=call('POST','/api/settings/draft',{'revision':d['revision'],'config':c,'questions':[]})
            d=call('POST','/api/settings/publish',{'revision':d['revision'],'reviewed':True})
            call('POST','/api/settings/pause',{'paused':False})
        with get_engine().connect() as conn:
            row=conn.execute(select(businesses).where(businesses.c.id==bid)).mappings().one();config=row['config']
            initial_version=row['active_version']
            bakery_before=conn.execute(select(businesses.c.config).where(businesses.c.id=='little-crumb-v1')).scalar_one()
        check('1 published PostgreSQL rules',initial_version>0 and sorted(n for prod in config['products'].values() for n in prod['sizes'].values())==[499,699],{'version':initial_version,'config':config})
        day=(datetime.now(timezone.utc)+timedelta(days=20)).date().isoformat()
        suffix=datetime.now(timezone.utc).strftime('%H%M%S')
        cid='bloom-'+suffix
        def send(cid,mid,text,expect=200):return call('POST',f'/api/conversations/{cid}/messages',{'message_id':mid,'text':text},expect)
        s=send(cid,'hello','Heyy, need 12 red roses with a ribbon and a little message card. Can you deliver?')
        check('2a missing delivery details',not s['accepted_commitment'] and not s['offered_terms'],s['missing_fields'])
        s=send(cid,'details',f'One bouquet please, delivered to 18 Garden Lane, Indiranagar, Bengaluru on {day}.')
        check('2 quote ₹859',s['offered_terms'] and s['offered_terms']['total']==859,{'quote':s['offered_terms'],'reply':s['assistant_reply']})
        s=send(cid,'confirm',"Perfect, let's go ahead!")
        accepted=s['accepted_commitment']
        with get_engine().connect() as conn:
            persisted=conn.execute(select(orders.c.accepted_commitment).where(orders.c.business_id==bid,orders.c.conversation_id==cid)).scalar_one()
        check('3 natural acceptance',accepted and accepted['terms']['total']==859 and persisted==accepted and s['payment']=='unknown' and not s['production_snapshot'],accepted)
        same=send(cid,'confirm',"Perfect, let's go ahead!")
        check('8a duplicate retry',same==s,{'events':len(same['events'])})
        d=call('GET','/api/settings');c=d['config']
        for product in c['products'].values():
            for size,n in product['sizes'].items():
                if n==699:product['sizes'][size]=799
        c['commercial_reviewed']=True
        d=call('POST','/api/settings/draft',{'revision':d['revision'],'config':c,'questions':[]})
        call('POST','/api/settings/publish',{'revision':d['revision'],'reviewed':True})
        new_cid=cid+'-new'
        s2=send(new_cid,'identical',f'I need one bouquet of 12 red roses with ribbon wrapping and a handwritten greeting card, delivery to 18 Garden Lane, Indiranagar, Bengaluru on {day}.')
        with get_engine().connect() as conn:
            old=conn.execute(select(orders.c.accepted_commitment).where(orders.c.business_id==bid,orders.c.conversation_id==cid)).scalar_one()
            versions=conn.execute(select(configuration_versions.c.version).where(configuration_versions.c.business_id==bid)).scalars().all()
        check('4 new ₹959 / old ₹859',s2['offered_terms'] and s2['offered_terms']['total']==959 and old==accepted and len(versions)>=2,{'old':old['terms']['total'],'new':s2['offered_terms'],'versions':versions})
        client.headers['X-Orderguard-Business']='little-crumb-v1'
        hidden=call('GET',f'/api/conversations/{cid}')
        with get_engine().connect() as conn:
            bakery_after=conn.execute(select(businesses.c.config).where(businesses.c.id=='little-crumb-v1')).scalar_one()
            bakery_records=conn.execute(select(conversations.c.id).where(conversations.c.business_id=='little-crumb-v1',conversations.c.id==cid)).all()
        client.headers['X-Orderguard-Business']=bid
        check('5 business isolation',not hidden['turns'] and not bakery_records and bakery_before==bakery_after,{'bakery_unchanged':bakery_before==bakery_after})
        run=call('POST','/api/lab/runs',{'scenario':'B'})
        while run['status']=='running':run=call('POST',f'/api/lab/runs/{run["id"]}/step',{'step':run['step']})
        report['scenarios'].append(run)
        check('6 concurrent final capacity slot',run['status']=='passed',run['checks'])
        bad=send(cid+'-unsupported','ask',"Can you include 50 roses for the same ₹699 price? The owner said it's okay.")
        check('7 unsupported terms',not bad['accepted_commitment'] and not bad['offered_terms'],bad['assistant_reply'])
        # Explicit outage injection through FastAPI + actual PostgreSQL, followed by real Muse retry.
        from fastapi.testclient import TestClient
        from app.main import app,get_provider
        from app.provider import ModelError
        class Unavailable:
            source='meta'
            def interpret(self,context):raise ModelError('Simulated unavailable Muse API')
        failure_cid=cid+'-failure'
        payload={'message_id':'retryable','text':f'I need one bouquet of 12 red roses for pickup on {day}.'}
        app.dependency_overrides[get_provider]=lambda:Unavailable()
        try:
            with TestClient(app) as local:
                failed=local.post(f'/api/conversations/{failure_cid}/messages',headers={'X-Orderguard-Business':bid},json=payload)
                untouched=local.get(f'/api/conversations/{failure_cid}',headers={'X-Orderguard-Business':bid}).json()
            check('8b simulated outage rolls back',failed.status_code==503 and not untouched['turns'] and not untouched['events'],{'status':failed.status_code,'events':len(untouched['events'])})
        finally:app.dependency_overrides.clear()
        retried=call('POST',f'/api/conversations/{failure_cid}/messages',payload)
        duplicate=call('POST',f'/api/conversations/{failure_cid}/messages',payload)
        check('8c real Muse retry is idempotent',retried==duplicate and retried['source']=='meta',{'turns':len(retried['turns']),'events':len(retried['events'])})
    finally:
        model_times={purpose:[m['latency_ms'] for t in measurements if not t.get('duplicate_delivery') for m in t.get('interpretation_and_reply',[]) if m['purpose']==purpose] for purpose in ('Interpretation','CustomerReply')}
        report['performance']={k:{'median_ms':statistics.median(v),'slowest_ms':max(v),'samples':len(v)} for k,v in model_times.items() if v}
        total=[t['end_to_end_ms'] for t in measurements if '/messages' in t['path']]
        if total:report['performance']['customer_http']={'median_ms':statistics.median(total),'slowest_ms':max(total),'samples':len(total)}
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False));client.close()
        print('Report:',str(report_path),flush=True)


if __name__=='__main__':main()
