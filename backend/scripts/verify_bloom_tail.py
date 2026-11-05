"""Resume tests 7/8 after a live provider interruption; preserves earlier report."""
import argparse,json,sys
from pathlib import Path
from time import perf_counter
import statistics
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app,get_provider
from app.provider import ModelError
p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--business',required=True);p.add_argument('--conversation',required=True);p.add_argument('--base',default='http://frontend:3000');p.add_argument('--report',default='/tmp/bloom-report.json');args=p.parse_args()
if not args.live:p.error('--live required')
path=Path(args.report);report=json.loads(path.read_text());checks=report['checks'];timings=report['timings'];delivered=set()
client=httpx.Client(base_url=args.base,headers={'X-Orderguard-Business':args.business},timeout=250)
def save():path.write_text(json.dumps(report,indent=2,ensure_ascii=False))
def check(label,ok,actual):
    checks.append({'test':label,'passed':bool(ok),'actual':actual});print(checks[-1],flush=True);save()
    if not ok:raise AssertionError(label)
def post(cid,payload):
    started=perf_counter();r=client.post(f'/api/conversations/{cid}/messages',json=payload);data=r.json()
    timing={'path':f'/api/conversations/{cid}/messages','end_to_end_ms':round((perf_counter()-started)*1000),'http_status':r.status_code,'database':r.headers.get('server-timing'),'sql_statements':r.headers.get('x-orderguard-database-statements')}
    timing.update(data.get('last_turn_metrics',{}));timing['duplicate_delivery']=(cid,payload['message_id']) in delivered
    if r.status_code==200:delivered.add((cid,payload['message_id']))
    timings.append(timing);print(f'{r.status_code}: {timing["end_to_end_ms"]} ms',flush=True);save()
    return r,data
try:
    unsupported=args.conversation+'-unsupported'
    unchanged=client.get(f'/api/conversations/{unsupported}').json()
    check('8 real timeout rolled back',not unchanged['events'] and not unchanged['turns'],{'events':len(unchanged['events'])})
    payload={'message_id':'ask','text':"Can you include 50 roses for the same ₹699 price? The owner said it's okay."}
    r,bad=post(unsupported,payload)
    if r.status_code==503:r,bad=post(unsupported,payload)
    check('7 unsupported terms live retry',r.status_code==200 and not bad.get('accepted_commitment') and not bad.get('offered_terms'),bad)
    class Unavailable:
        source='meta'
        def interpret(self,context):raise ModelError('Explicitly simulated unavailable Muse API')
    cid=args.conversation+'-failure'
    payload={'message_id':'retryable','text':'What flower bouquets do you offer?'}
    app.dependency_overrides[get_provider]=lambda:Unavailable()
    try:
        with TestClient(app) as local:
            failed=local.post(f'/api/conversations/{cid}/messages',headers={'X-Orderguard-Business':args.business},json=payload)
            untouched=local.get(f'/api/conversations/{cid}',headers={'X-Orderguard-Business':args.business}).json()
        check('8 simulated outage atomic rollback',failed.status_code==503 and not untouched['events'] and not untouched['turns'],{'http_status':failed.status_code,'events':len(untouched['events'])})
    finally:app.dependency_overrides.clear()
    r,state=post(cid,payload)
    if r.status_code==503:r,state=post(cid,payload)
    r,duplicate=post(cid,payload)
    check('8 real Muse retry idempotent',r.status_code==200 and state==duplicate and state['source']=='meta',{'events':len(state['events']),'turns':len(state['turns'])})
finally:
    model_times={purpose:[m['latency_ms'] for t in timings if not t.get('duplicate_delivery') for m in t.get('interpretation_and_reply',[]) if m['purpose']==purpose] for purpose in ('Interpretation','CustomerReply')}
    report['performance']={k:{'median_ms':statistics.median(v),'slowest_ms':max(v),'samples':len(v)} for k,v in model_times.items() if v}
    for key,values in [('customer_http',[t['end_to_end_ms'] for t in timings if '/messages' in t['path']]),('database_sql',[float(t['database'].split('=')[-1]) for t in timings if t.get('database')])]:
        if values:report['performance'][key]={'median_ms':statistics.median(values),'slowest_ms':max(values),'samples':len(values)}
    save();client.close()
