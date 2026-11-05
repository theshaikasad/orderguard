"""Real Muse late-product change after explicit simulated production."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.store import Store
from app.provider import MetaProvider
from app import scenarios
p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--output',default='/tmp/late-flavor.json');a=p.parse_args()
if not a.live:p.error('--live required')
store=Store();run=scenarios.start(store,'E')
while run['status']=='running':
    run=scenarios.advance(store,MetaProvider(),run['id']);Path(a.output).write_text(json.dumps(run,indent=2,ensure_ascii=False));print('Step',run['step'],run['status'],flush=True)
print(run['checks'],flush=True)
if run['status']!='passed':raise SystemExit(1)
