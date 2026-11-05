"""Opt-in paired Muse reply-selection experiment; no customer state is changed."""
import argparse,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.provider import MetaProvider
from app.replies import compose_reply
p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');p.add_argument('--output',default='/tmp/reasoning-experiment.json');a=p.parse_args()
if not a.live:p.error('--live required')
results=[]
for effort in ['', 'low']:
    os.environ['MUSE_REPLY_REASONING_EFFORT']=effort
    provider=MetaProvider()
    reply,source=compose_reply(provider,[['Our prices are fixed, so I can’t offer a discount.','We keep our prices fixed, so there isn’t a discount available.'],['Would you like to go ahead at the listed price?']],{'tone':'Friendly, casual','permitted_action':'fixed_price','recent_conversation':[{'speaker':'customer','text':'Can I get a discount?'}]})
    result={'effort':effort or 'model_default','source':source,'reply':reply,'metrics':provider.metrics};results.append(result)
    Path(a.output).write_text(json.dumps(results,indent=2,ensure_ascii=False));print(result,flush=True)
    assert source=='meta'
