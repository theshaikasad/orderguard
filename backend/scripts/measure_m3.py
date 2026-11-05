"""Three representative live turns; SQL and total timing through the frontend proxy."""
import argparse,json,statistics
from datetime import datetime,timedelta,timezone
from pathlib import Path
from time import perf_counter
import httpx
p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--business',required=True);p.add_argument('--base',default='http://frontend:3000');p.add_argument('--output',default='/tmp/m3-performance.json');a=p.parse_args()
if not a.live:p.error('--live required')
prefix='timing-'+datetime.now(timezone.utc).strftime('%H%M%S');day=(datetime.now(timezone.utc)+timedelta(days=25)).date().isoformat();rows=[]
with httpx.Client(base_url=a.base,headers={'X-Orderguard-Business':a.business},timeout=250) as c:
    for cid,mid,text in [(prefix+'-inquiry','hello','Which flower bouquets do you sell?'),(prefix+'-quote','request',f'I would like one bouquet of 12 red roses with ribbon wrapping and a handwritten greeting card, for pickup on {day}.'),(prefix+'-quote','repeat','Could you remind me of the total?')]:
        start=perf_counter();r=c.post(f'/api/conversations/{cid}/messages',json={'message_id':mid,'text':text});data=r.json()
        row={'conversation_id':cid,'message_id':mid,'http_status':r.status_code,'end_to_end_ms':round((perf_counter()-start)*1000),'database_header':r.headers.get('server-timing'),'database_statements':r.headers.get('x-orderguard-database-statements'),'source':data.get('source'),'metrics':data.get('last_turn_metrics'),'error':data.get('detail')}
        rows.append(row);print(row,flush=True);Path(a.output).write_text(json.dumps({'turns':rows},indent=2))
summary={}
for key in ['Interpretation','CustomerReply']:
    v=[m['latency_ms'] for r in rows for m in (r['metrics'] or {}).get('interpretation_and_reply',[]) if m['purpose']==key]
    if v:summary[key]={'median_ms':statistics.median(v),'slowest_ms':max(v),'samples':len(v)}
for key,v in [('database_sql',[float(r['database_header'].split('=')[-1]) for r in rows if r['database_header']]),('customer_http',[r['end_to_end_ms'] for r in rows])]:
    if v:summary[key]={'median_ms':statistics.median(v),'slowest_ms':max(v),'samples':len(v)}
Path(a.output).write_text(json.dumps({'turns':rows,'summary':summary},indent=2));print(summary,flush=True)
if any(r['http_status']!=200 or r['source']!='meta' or not r['database_header'] for r in rows):raise SystemExit(1)
