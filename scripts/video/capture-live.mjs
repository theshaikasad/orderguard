import {chromium} from '/tmp/orderguard-video-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
const root=new URL('../../',import.meta.url).pathname, out=root+'artifacts/video-production/';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--hide-scrollbars']});
const ctx=await browser.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:out+'raw',size:{width:1920,height:1080}}});
const r=await ctx.request.post('http://127.0.0.1:3000/api/demo/sessions',{data:{}});if(!r.ok())throw Error('session failed');const session=await r.json();
await ctx.addInitScript(s=>localStorage.setItem('orderguard-recording-session-v1',JSON.stringify(s)),session);
const customer=await ctx.newPage(),seller=await ctx.newPage();
await customer.goto('http://127.0.0.1:3000/demo/customer');await seller.goto('http://127.0.0.1:3000/demo/seller');
await customer.waitForTimeout(1600);
const start=Date.now(), report={session,started:new Date().toISOString(),steps:[]};
const at=()=>+( (Date.now()-start)/1000).toFixed(3);
async function send(name,text){
 const begin=at();await customer.getByRole('textbox',{name:'Message the bakery'}).pressSequentially(text,{delay:17});
 await customer.waitForTimeout(450);
 const waiting=customer.waitForResponse(r=>r.url().endsWith('/messages')&&r.request().method()==='POST',{timeout:240000});
 const sent=at();await customer.getByRole('button',{name:'Send message',exact:true}).click();
 const response=await waiting;const state=await response.json();if(!response.ok())throw Error('Real inference failed '+response.status());
 if(state.source!=='meta')throw Error('Not Meta inference');
 await customer.waitForTimeout(1600);const shown=at();
 await customer.screenshot({path:out+'frames/live-'+name+'-customer.png'});await seller.screenshot({path:out+'frames/live-'+name+'-seller.png'});
 report.steps.push({name,text,begin,sent,shown,state});await fs.writeFile(out+'live-capture.json',JSON.stringify(report,null,2));
 console.log('REAL',name,'quote',state.offered_terms?.total,'reply',state.turns.at(-1).reply_source,'seconds',shown-sent);
 await customer.waitForTimeout(2200);
}
try{
 await send('clarify','Hi! Could I order a chocolate cake?');
 await send('quote','One 1 kg cake for pickup on 2026-11-12, please.');
 await send('extras','Please make it eggless with floral decoration.');
 await send('accepted',"Perfect, let's go ahead!");
 const prod=await ctx.request.post('http://127.0.0.1:3000/api/conversations/recording/owner-action',{headers:{'X-Orderguard-Business':session.business_id},data:{action:'start_production'}});if(!prod.ok())throw Error('Production failed');
 report.production_at=at();await customer.waitForTimeout(1500);
 await send('production-change','Please change the flavor to red velvet.');
 const final=report.steps.at(-1).state;if(!final.production_snapshot||final.decision!=='needs_owner')throw Error('Missing frozen plan');
 await fs.writeFile(out+'live-capture.json',JSON.stringify(report,null,2));
 await customer.waitForTimeout(3000);
}finally{
 const cv=customer.video(),sv=seller.video();await ctx.close();await fs.rename(await cv.path(),out+'raw/live-customer.webm');await fs.rename(await sv.path(),out+'raw/live-seller.webm');await browser.close();
}
