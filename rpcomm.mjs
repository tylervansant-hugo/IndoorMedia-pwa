import WebSocket from 'ws';
const CDP='http://127.0.0.1:18800';
const URL='http://127.0.0.1:4199/IndoorMedia-pwa/';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl); let id=0; const p=new Map();
await new Promise(r=>ws.on('open',r));
ws.on('message',d=>{const m=JSON.parse(d.toString()); if(m.id&&p.has(m.id)){p.get(m.id)(m);p.delete(m.id);}});
const send=(method,params={})=>new Promise(res=>{const mid=++id;p.set(mid,res);ws.send(JSON.stringify({id:mid,method,params}));});
const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});if(r.result&&r.result.exceptionDetails)throw new Error(JSON.stringify(r.result.exceptionDetails));return r.result&&r.result.result?r.result.result.value:undefined;};
await send('Page.enable');await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride',{width:440,height:1200,deviceScaleFactor:2,mobile:true});
await send('Page.navigate',{url:URL}); await sleep(2500);
await ev(`(()=>{const u={id:'tvs',name:'Tyler Van Sant',first_name:'Tyler',display_name:'Tyler Van Sant',email:'tyler.vansant@indoormedia.com',rep_id:'tvs'};localStorage.setItem('user',JSON.stringify(u));localStorage.setItem('impro_user',JSON.stringify(u));localStorage.setItem('impro_seen_walkthrough','1');return 1;})()`);
await send('Page.navigate',{url:URL}); await sleep(4000);

const stage={};
await ev(`(()=>{const el=[...document.querySelectorAll('button')].find(b=>/Prospect/i.test(b.textContent||''));if(el)el.click();})()`); await sleep(1500);
await ev(`(()=>{const i=[...document.querySelectorAll('input')].find(x=>/store, city, zip/i.test(x.placeholder||''));if(i){i.focus();i.value='Albany';i.dispatchEvent(new Event('input',{bubbles:true}));}})()`); await sleep(1800);
await ev(`(()=>{const c=document.querySelector('.store-card');if(c)c.click();})()`); await sleep(1200);
await ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>/Prospect Store/i.test(x.textContent||''));if(b)b.click();})()`); await sleep(2500);
await ev(`(()=>{const i=[...document.querySelectorAll('input')].find(x=>/keyword|business type|e\\.g|custom|auto|search/i.test((x.placeholder||''))&&x.offsetParent);if(i){i.focus();i.value='auto repair';i.dispatchEvent(new Event('input',{bubbles:true}));}})()`); await sleep(400);
await ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>/^\\s*(Search|🔍)/i.test(x.textContent||'')&&x.offsetParent);if(b)b.click();})()`); await sleep(6000);

// Open Email flow on first card
await ev(`(()=>{const card=document.querySelector('.prospect-card');const b=[...card.querySelectorAll('.big-contact-btn')].find(x=>/Email/i.test(x.textContent||''));if(b)b.click();})()`); await sleep(2500);

// Find the Community Connection template button and check it exists
stage.communityBtnExists = await ev(`(()=>{const card=document.querySelector('.prospect-card');return !![...card.querySelectorAll('.email-tpl-btn')].find(b=>/Community Connection/i.test(b.textContent||''));})()`);
// Click it
await ev(`(()=>{const card=document.querySelector('.prospect-card');const b=[...card.querySelectorAll('.email-tpl-btn')].find(x=>/Community Connection/i.test(x.textContent||''));if(b)b.click();})()`); await sleep(1500);

stage.preview = await ev(`(()=>{const card=document.querySelector('.prospect-card');const subj=card.querySelector('.email-subject');const body=card.querySelector('.email-body-text');return {subject:subj?subj.textContent:null, body:body?body.textContent:null};})()`);

const shot=await send('Page.captureScreenshot',{format:'png'});
if(shot.result&&shot.result.data){const fs=await import('fs');fs.writeFileSync('/tmp/comm.png',Buffer.from(shot.result.data,'base64'));}
ws.close();
console.log(JSON.stringify(stage,null,2));
