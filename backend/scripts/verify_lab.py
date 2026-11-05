"""Run genuine Muse Scenario Lab workflows through HTTP. No mocked provider."""
import argparse
import json
from pathlib import Path
import httpx

p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--base',default='http://frontend:3000');p.add_argument('--scenarios',default='ABECDF');p.add_argument('--business',default='little-crumb-v1');p.add_argument('--output',default='/tmp/lab-report.json');a=p.parse_args()
if not a.live:p.error('--live required')
results=[]
with httpx.Client(base_url=a.base,headers={'X-Orderguard-Business':a.business},timeout=250) as c:
    def post(path,body):
        r=c.post('/api/'+path,json=body);r.raise_for_status();return r.json()
    for key in a.scenarios:
        run=post('lab/runs',{'scenario':key})
        print(f'{key}: {run["id"]}',flush=True)
        while run['status']=='running':
            run=post(f'lab/runs/{run["id"]}/step',{'step':run['step']})
            print(f'  step {run["step"]}: {run["observations"][-1]}',flush=True)
        results.append(run);Path(a.output).write_text(json.dumps(results,indent=2,ensure_ascii=False))
        print(f'{key}: {run["status"]} {run["checks"]}',flush=True)
if any(r['status']!='passed' for r in results):raise SystemExit(1)
