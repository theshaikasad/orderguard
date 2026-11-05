"""Build a real-product film. Source recordings are never replaced by mocked replies."""
from pathlib import Path
import json, subprocess, textwrap, re, sys, math, wave
from PIL import Image, ImageDraw, ImageFont
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'artifacts/video-production'; OUT.mkdir(exist_ok=True)
W,H=1920,1080; INK='#263e35'; PAPER='#f3f5ee'; MUTED='#7f9079'; GOLD='#bc9b68'
FONT='/System/Library/Fonts/SFNS.ttf'; SERIF='/System/Library/Fonts/Supplemental/Georgia.ttf'
def font(n,bold=False):
 return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else FONT,n)
def run(args): subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def duration(path): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)]))
def fitlines(draw,text,f,maxw):
 words=text.split();lines=[];line=''
 for word in words:
  nxt=(line+' '+word).strip()
  if draw.textlength(nxt,font=f)>maxw and line:lines.append(line);line=word
  else:line=nxt
 if line:lines.append(line)
 return lines
SCENES=[
 {'id':'hook','d':14,'title':'Every message can\nchange an order.','kicker':'THE SMALL BUSINESS INBOX','narration':'A cake changes size. Then flavor. Then the date. For a small business, one missed message can become an expensive mistake.','kind':'title'},
 {'id':'intro','d':11,'title':'Meet OrderGuard.','sub':'An AI sales + order operations agent.','kicker':'LESS INBOX. MORE BUSINESS.','narration':'Small businesses need more than another chatbot. Meet Order Guard: an AI sales and order operations agent, grounded in each seller’s business.','kind':'customer','raw':'customer-real'},
 {'id':'quote','d':15,'title':'Understands the request.\nAsks what is missing.','sub':'Real Meta Muse Spark inference','kicker':'01 / FROM HELLO TO A CLEAR QUOTE','narration':'The customer asks for a chocolate cake. Meta Muse Spark understands the request and asks for the details it needs. A one kilogram cake for pickup is nine hundred rupees.','kind':'customer','raw':'customer-real'},
 {'id':'extras','d':15,'title':'Changes happen.\nThe price stays correct.','sub':'₹900 cake + ₹150 eggless + ₹250 floral = ₹1,300','kicker':'02 / REVISIONS WITHOUT CONFUSION','narration':'Now make it eggless, with floral decoration. The backend applies the configured charges, and replaces the old quote. The new total is thirteen hundred rupees. Muse does not invent the price.','kind':'customer','raw':'customer-real'},
 {'id':'accept','d':13,'title':'A natural yes.\nAn exact commitment.','sub':'Owner intervention: none for this valid acceptance.','kicker':'03 / ROUTINE ORDERS, HANDLED','narration':'A natural yes accepts this exact valid quote. The seller sees the saved commitment automatically. Acceptance does not verify payment, and it does not start production.','kind':'seller','raw':'seller-real'},
 {'id':'late','d':19,'title':'Autonomous where possible.\nHuman approval where necessary.','sub':'Late production change · original plan protected','kicker':'04 / THE EXPENSIVE MISTAKE, PREVENTED','narration':'Here is the difficult case, verified in Scenario Lab. Production has already started when the customer changes the cake. Order Guard preserves the frozen production instructions and creates one clear owner review. A request is never silently turned into a promise.','kind':'lab','raw':'lab-production'},
 {'id':'setup','d':15,'title':'Teach it your business.','sub':'Muse proposes sourced drafts. The seller reviews and publishes.','kicker':'05 / CONFIGURABLE, NOT A BAKERY SCRIPT','narration':'The same system works for a florist. The seller describes the catalogue and policies in natural language. Muse proposes sourced draft rules; the seller reviews and publishes the configuration.','kind':'full','raw':'bloom-settings'},
 {'id':'bloom','d':14,'title':'Bloom & Co. / ₹859','sub':'₹699 roses + ₹50 ribbon + ₹30 card + ₹80 delivery','kicker':'ONE BUSINESS. ITS OWN RULES.','narration':'For Bloom and Company, the real verified order is eight hundred fifty nine rupees: roses, ribbon, a greeting card, and delivery. The accepted order keeps its original commercial terms.','kind':'full','raw':'bloom-859'},
 {'id':'version','d':11,'title':'New price. New quote.\nOld commitment preserved.','sub':'New quote ₹959 · earlier accepted order ₹859','kicker':'VERSIONED BUSINESS CONFIGURATION','narration':'After a published price change, a new quote is nine hundred fifty nine rupees. The earlier accepted order stays at eight hundred fifty nine. History is preserved.','kind':'full','raw':'bloom-959'},
 {'id':'engine','d':17,'title':'Language is probabilistic.\nCommitments should not be.','kicker':'THE ENGINEERING BEHIND THE EXPERIENCE','narration':'Muse interprets language and composes validated replies. Deterministic rules authorize prices, policies, and capacity. PostgreSQL persists sourced commitments atomically. One hundred fifty one backend tests pass, with eight complex scenarios verified using real Muse. The Instagram adapter is tested with synthetic events; live Instagram is not connected.','kind':'architecture'},
 {'id':'end','d':14,'title':'OrderGuard.','sub':'Less inbox. More business.','kicker':'BUILT FOR THE BUSINESSES AROUND US','narration':'Friendly conversations. Reliable orders. Human judgment when it matters. Order Guard. Less inbox. More business.','kind':'title'},
]
# Optional newer browser recordings have real per-step timestamps and persisted response evidence.
live_path=OUT/'live-capture.json'; live=json.loads(live_path.read_text()) if live_path.exists() else None
USE_LIVE=('--live' in sys.argv and live and (OUT/'raw/live-customer.webm').exists())
if USE_LIVE:
 lookup={x['name']:x for x in live['steps']}
 for s,n in [('quote','quote'),('extras','extras'),('accept','accepted')]:
  scene=next(x for x in SCENES if x['id']==s);step=lookup[n]
  scene.update(raw='live-seller' if s=='accept' else 'live-customer',start=0,live=True,step=step,result={'quote':46.5,'extras':70.5,'accept':92.0}[s])
 # Clarification is its own real UI segment, shown just before the full quote.
 next(x for x in SCENES if x['id']=='intro').update(raw='live-customer',start=0,live=True,step=lookup['clarify'],result=20.5)

def overlay(s):
 im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
 if s['kind'] in ['title','architecture']:
  d.rectangle((0,0,W,H),fill=PAPER)
  for r,a in [(380,15),(285,25),(190,35)]:d.ellipse((1530-r,250-r,1530+r,250+r),outline=GOLD,width=1)
 d.rectangle((0,0,W,106),fill=PAPER)
 d.rounded_rectangle((52,25,104,78),radius=15,fill=INK);d.text((64,31),'og',font=font(28),fill='#f2e5ca')
 d.text((122,39),'OrderGuard',font=font(27,True),fill=INK)
 d.text((720,44),'Simulated customer conversations · Real Meta Muse inference',font=font(22),fill=INK)
 d.line((52,105,1868,105),fill='#dbe1d2',width=2)
 if s['kind']=='title':
  d.text((130,262),s['kicker'],font=font(22,True),fill=MUTED)
  y=345
  for line in s['title'].split('\n'):d.text((122,y),line,font=font(113,True),fill=INK);y+=128
  if s.get('sub'):d.text((130,y+25),s['sub'],font=font(50),fill=MUTED)
  d.text((132,825),'META GLOBAL AI DEVELOPER HACKATHON 2026',font=font(19,True),fill=MUTED)
 elif s['kind']=='customer':
  d.rectangle((0,106,855,930),fill=PAPER)
  d.text((62,205),s['kicker'],font=font(18,True),fill=MUTED)
  y=284
  for line in fitlines(d,s['title'].replace('\n',' '),font(66,True),720):d.text((58,y),line,font=font(66,True),fill=INK);y+=83
  if s.get('sub'):
   for line in fitlines(d,s['sub'],font(30),700):d.text((62,y+35),line,font=font(30),fill=MUTED);y+=42
  d.rounded_rectangle((62,748,746,836),radius=18,fill='#e3ead8')
  d.text((86,769),'REAL APP · REAL PERSISTED RESULTS',font=font(24,True),fill=INK)
 else:
  d.rectangle((0,106,W,232),fill=PAPER)
  d.text((56,123),s['kicker'],font=font(16,True),fill=MUTED)
  d.text((52,157),s['title'].replace('\n',' '),font=font(42,True),fill=INK)
  if s.get('sub'):d.text((56,207),s['sub'],font=font(21),fill=MUTED)
 if s['kind']=='architecture':
  nodes=[('Customer','message'),('Meta Muse Spark','interpret + compose'),('Business engine','price + policy + capacity'),('PostgreSQL','sourced commitments'),('Seller','genuine exceptions')]
  for i,(title,desc) in enumerate(nodes):
   x=50+i*375;d.rounded_rectangle((x,422,x+335,590),radius=24,fill='#e4eadb',outline='#cedac2',width=2)
   d.text((x+22,450),title,font=font(29,True),fill=INK)
   for j,line in enumerate(fitlines(d,desc,font(22),290)):d.text((x+22,505+j*30),line,font=font(22),fill=MUTED)
   if i<4:d.text((x+341,470),'→',font=font(31),fill=INK)
  d.text((70,697),'151 backend tests passed',font=font(35,True),fill=INK)
  d.text((70,755),'8 complex scenarios verified using real Muse',font=font(30),fill=MUTED)
  d.text((70,813),'PostgreSQL · Docker · signature-verified synthetic webhook replay',font=font(27),fill=MUTED)
 d.rectangle((0,930,W,H),fill=INK)
 label='Recorded real inference · model waiting time shortened in editing' if s.get('live') else 'Actual application footage · previously verified, persisted Meta results'
 if s['kind'] in ('title','architecture'):label='Local synthetic simulator · no live Instagram or payment connection'
 d.text((58,946),label,font=font(18),fill='#c3d1b8')
 path=OUT/'frames'/('overlay-'+s['id']+'.png');im.save(path);return path

def caption(text,path):
 im=Image.new('RGBA',(W,112),(0,0,0,0));d=ImageDraw.Draw(im);f=font(31)
 lines=fitlines(d,text,f,1740)
 for i,line in enumerate(lines[:2]):d.text(((W-d.textlength(line,font=f))/2,8+i*41),line,font=f,fill='#ffffff')
 im.save(path)

segments=[];srt=[];clock=0
only=set(sys.argv[sys.argv.index('--only')+1].split(',')) if '--only' in sys.argv else None
if (OUT/'raw/setup-history.webm').exists():
 next(x for x in SCENES if x['id']=='setup').update(raw='setup-history',start=1.4)
for n,s in enumerate(SCENES):
 audio=OUT/'audio'/(s['id']+'.aiff')
 if not audio.exists():run(['say','-v','Samantha','-r','174','-o',str(audio),s['narration']])
 ad=duration(audio);s['d']=max(s['d'],ad+1.0)
 if s['d']>24:s['d']=24
 sentences=re.split(r'(?<=[.!?])\s+',s['narration']);total=sum(len(x.split()) for x in sentences);caps=[];t=.25
 for i,txt in enumerate(sentences):
  cd=ad*len(txt.split())/total;cp=OUT/'frames'/f'caption-{s["id"]}-{i}.png';caption(txt,cp);caps.append((cp,t,min(s['d'],t+cd)));srt.append((clock+t,clock+min(s['d'],t+cd),txt));t+=cd
 frame=overlay(s);target=OUT/(f'part-{n:02d}.mp4');segments.append(target)
 source=OUT/'raw'/(s.get('raw','')+'.webm')
 args=['ffmpeg','-y','-hide_banner','-loglevel','error']
 static=s['kind'] in ['title','architecture']
 if static:args+=['-loop','1','-framerate','30','-i',str(frame)]
 else:args+=['-ss',str(s.get('start',3)),'-i',str(source),'-loop','1','-framerate','30','-i',str(frame)]
 ai=1 if static else 2;args+=['-i',str(audio)]
 for cp,a,b in caps:args+=['-loop','1','-framerate','30','-i',str(cp)]
 d=s['d']; filters=[]
 if static:
  filters+=["[0:v]scale=1920:1080,zoompan=z='1+0.000025*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=30,setsar=1[base]"]
 else:
  # Tight editorial crops keep actual product text readable. No DOM/API output is altered.
  if s['kind']=='customer':
   cy=240 if s['id']=='intro' else 340 if s['id']=='quote' else 385
   crop=f'crop=600:475:935:{cy},scale=1040:824,pad=1920:1080:855:106:color=0xf3f5ee'
  elif s['kind']=='lab':crop='crop=830:510:960:330,scale=1300:798,pad=1920:1080:310:234:color=0xf3f5ee'
  elif s['id'] in ['bloom','version']:crop='crop=1350:795:420:258,scale=1770:1042,crop=1770:696:0:90,pad=1920:1080:75:234:color=0xf3f5ee'
  elif s['kind']=='seller':crop='crop=1390:790:375:225,scale=1770:1006,crop=1770:696:0:0,pad=1920:1080:75:234:color=0xf3f5ee'
  elif s['id']=='setup' and s.get('raw')=='setup-history':crop='crop=1120:540:380:540,scale=1450:700,pad=1920:1080:235:234:color=0xf3f5ee'
  else:crop='crop=1330:800:380:150,scale=1770:1064,crop=1770:696:0:0,pad=1920:1080:75:234:color=0xf3f5ee'
  if s.get('live'):
   step=s['step'];offset=3.45;begin=step['begin']+offset;sent=step['sent']+offset
   result=s['result'];end=min(sent+1.0,result-.4)
   # Three genuine recorded intervals: customer input, accelerated real wait, response.
   filters += [f'[0:v]split=3[typing][waiting][reply]',f'[typing]trim=start={begin}:end={end},setpts=PTS-STARTPTS[a0]',f'[waiting]trim=start={end}:end={result},setpts=(PTS-STARTPTS)/18[a1]',f'[reply]trim=start={result}:duration={0.7 if s["id"]=="accept" else 2.0},setpts=PTS-STARTPTS[a2]',f'[a0][a1][a2]concat=n=3:v=1:a=0,{crop},fps=30,tpad=stop_mode=clone:stop_duration={d},setsar=1[shot]']
  else:
   filters += [f'[0:v]trim=duration={5.2 if s["id"]=="setup" else d},setpts=PTS-STARTPTS,{crop},fps=30,tpad=stop_mode=clone:stop_duration={d},setsar=1[shot]']
  filters += ['[shot][1:v]overlay=0:0:shortest=0[base]']
 previous='base'
 for i,(cp,a,b) in enumerate(caps):
  idx=ai+1+i;name=f'cap{i}';filters.append(f'[{previous}][{idx}:v]overlay=0:974:enable=\'between(t,{a:.3f},{b:.3f})\'[{name}]');previous=name
 filters.append(f'[{previous}]fade=t=in:st=0:d=0.25,fade=t=out:st={d-.25:.3f}:d=0.25,format=yuv420p[v]')
 filters.append(f'[{ai}:a]adelay=250|250,apad=whole_dur={d},atrim=duration={d},loudnorm=I=-16:TP=-1.5:LRA=7[a]')
 args+=['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(d),'-r','30','-c:v','libx264','-preset','veryfast','-crf','21','-threads','4','-c:a','aac','-b:a','160k','-ar','48000','-movflags','+faststart',str(target)]
 print('RENDER',s['id'],round(d,2),'seconds',flush=True)
 try:
  if not only or s['id'] in only or not target.exists():run(args)
 except subprocess.CalledProcessError as e:
  print(e.stderr.decode()[-5000:]);raise
 clock+=d
(OUT/'concat.txt').write_text(''.join("file '"+str(x)+"'\n" for x in segments))
joined=OUT/'assembled.mp4';run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(OUT/'concat.txt'),'-c','copy','-movflags','+faststart',str(joined)])
# Original, locally synthesized ambient bed. No sampled or commercial music.
sr=48000;t=np.arange(int((clock+1)*sr),dtype=np.float64)/sr
waveform=np.zeros_like(t)
for hz in [130.8128,164.8138,195.9977,261.6256]:
 waveform += .014*np.sin(2*np.pi*hz*t)*(0.65+0.35*np.sin(2*np.pi*.025*t+hz))
waveform*=np.minimum(t/4,1)*np.minimum((clock+1-t)/4,1)
with wave.open(str(OUT/'audio/music.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(waveform,-1,1)*32767).astype(np.int16).tobytes())
def timestamp(v):
 ms=round(v*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
srtpath=ROOT/'artifacts/orderguard-hackathon-demo.srt';srtpath.write_text(''.join(f'{i+1}\n{timestamp(a)} --> {timestamp(b)}\n{txt}\n\n' for i,(a,b,txt) in enumerate(srt)))
candidate=OUT/'candidate.mp4'
run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(joined),'-i',str(OUT/'audio/music.wav'),'-i',str(srtpath),'-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-map','0:v','-map','[a]','-map','2:0','-c:v','copy','-c:a','aac','-b:a','192k','-c:s','mov_text','-metadata:s:s:0','language=eng','-movflags','+faststart',str(candidate)])
info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(candidate)]))
v=next(s for s in info['streams'] if s['codec_type']=='video');assert v['width']==1920 and v['height']==1080 and v['codec_name']=='h264';assert float(info['format']['duration'])<180
final=ROOT/'artifacts/orderguard-hackathon-demo.mp4'
if final.exists():final.replace(OUT/'previous-working.mp4')
candidate.replace(final)
(OUT/'verification.json').write_text(json.dumps(info,indent=2))
script='# OrderGuard hackathon film\n\n';shotlist='# OrderGuard video shot list\n\n';pos=0
for s in SCENES:
 script+=f'## {pos:.1f}–{pos+s["d"]:.1f}s / {s["title"].replace(chr(10)," ")}\n\n{s["narration"]}\n\n'
 shotlist+=f'- {pos:.1f}–{pos+s["d"]:.1f}s: {s["id"]}; actual source `{s.get("raw","original motion graphic")}`; narration Samantha (local macOS TTS); recorded synthetic conversations with real Meta output.\n'
 pos+=s['d']
script+='\nDisclosure: Actual application recordings. Synthetic customers. Real Meta Muse inference. Existing persisted runs are labelled; waiting is shortened through editing. Instagram is not live. Original synthesized background audio.\n'
(ROOT/'artifacts/orderguard-video-script.md').write_text(script);(ROOT/'artifacts/orderguard-video-shotlist.md').write_text(shotlist)
print('FINISHED',final,'duration',clock,'bytes',final.stat().st_size,flush=True)
