import { chromium } from '/tmp/orderguard-video-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
const root = new URL('../../', import.meta.url).pathname;
const out = root+'artifacts/video-production/';
const base='http://127.0.0.1:3000';
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--hide-scrollbars','--autoplay-policy=no-user-gesture-required']});
const evidence=JSON.parse(await fs.readFile(root+'artifacts/demo-polish/live-http.json','utf8'));
const bakery={...evidence.session,business_id:'demo-30ee0915069943509e3e914c488689ae',conversation_id:'recording'};
async function scene(name,url,{business='little-crumb-v1',demo=null,action=null,hold=6500}={}){
 const ctx=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir:out+'raw',size:{width:1920,height:1080}},colorScheme:'light'});
 await ctx.addInitScript(({business,demo})=>{localStorage.setItem('orderguard-business',business);if(demo)localStorage.setItem('orderguard-recording-session-v1',JSON.stringify(demo));},{business,demo});
 const page=await ctx.newPage();
 await page.goto(base+url,{waitUntil:'networkidle',timeout:45000});
 await page.waitForTimeout(1200);
 if(action)await action(page);
 await page.screenshot({path:out+'frames/'+name+'.png'});
 await page.waitForTimeout(hold);
 const video=page.video();await ctx.close();await fs.rename(await video.path(),out+'raw/'+name+'.webm');
 console.log('CAPTURED',name,flush=>{});
}
try{
 await scene('customer-real','/demo/customer',{demo:bakery,action:async p=>{await p.locator('.demo-messages').evaluate(el=>el.scrollTo({top:0,behavior:'instant'}));await p.waitForTimeout(1500);await p.locator('.demo-messages').evaluate(el=>el.scrollBy({top:350,behavior:'smooth'}));},hold:7000});
 await scene('seller-real','/demo/seller',{demo:bakery,action:async p=>{await p.locator('.demo-messages').evaluate(el=>el.scrollTo({top:el.scrollHeight,behavior:'instant'}));},hold:7000});
 await scene('lab-production','/lab',{action:async p=>{const run=p.locator('button.run-history').filter({hasText:'Late production change'}).first();if(await run.count()){await run.scrollIntoViewIfNeeded();await run.click();await p.waitForTimeout(1200);await p.locator('.lab-result').scrollIntoViewIfNeeded();await p.evaluate(()=>window.scrollTo({top:0,behavior:'smooth'}));}},hold:8000});
 const bloom='shop-6e3e0b5f795a45fa937920f1afe9360b';
 await scene('bloom-settings','/settings',{business:bloom,action:async p=>{await p.getByRole('button',{name:'Products & Pricing',exact:true}).click();},hold:5000});
 await scene('bloom-859','/?conversation=submission-complete-01',{business:bloom,action:async p=>{await p.locator('.orders').evaluate(el=>el.scrollTo({top:0,behavior:'instant'}));await p.locator('.messages').evaluate(el=>el.scrollTo({top:el.scrollHeight,behavior:'instant'}));},hold:7000});
 await scene('bloom-959','/?conversation=submission-complete-02',{business:bloom,hold:6000});
 await scene('overview','/overview',{business:bloom,hold:5000});
}finally{await browser.close();}
