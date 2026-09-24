// Functional browser regression tests against the bundled app with an isolated API fixture.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const root = new URL('../../python/src/pkdb/curation/static/', import.meta.url);
const state = { csrf_token:'fixture-csrf',workspace:'/tmp/curation-fixture',endpoint:'https://example.invalid',account:'curator',offline:false,paused:false,vocabulary:{status:'current'},github:{user:'github-curator',users:[{login:'github-curator',name:'Example Curator'},{login:'second',name:'Second User'}],issues:[{number:1,title:'drug/Example2026',html_url:'https://github.com/example/data/issues/1',assignees:['github-curator'],study_ids:['one']},{number:2,title:'NotLocal2026',html_url:'https://github.com/example/data/issues/2',assignees:['github-curator'],study_ids:[]}]},studies:[{id:'one',name:'Example2026',sid:'PKDB00001',path:'drug/Example2026',status:'invalid',mode:'validate',files:[{id:'outputs.xlsx',path:'outputs.xlsx'}],problems:[{severity:'error',code:'vocabulary.unknown',message:'Unknown measurement <script>alert(1)</script>',source:{file:'outputs.xlsx',sheet:'Sheet1',cell:'C10'},suggestions:[{message:'Choose a supported measurement.'}]}]},{id:'two',name:'Second2026',sid:'PKDB00002',path:'drug/Second2026',status:'discovered',mode:'validate',files:[],problems:[]}],jobs:[]};
state.jobs = [{id:'queued-job',study_id:'two',action:'validate',status:'queued'}, {id:'unknown-job',study_id:'one',action:'upload',status:'unknown',persistence:'unknown',endpoint:'https://example.invalid'}];
const calls = [], errors = [];
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('http://curation.test/**',async route=>{
    const req=route.request(), path=new URL(req.url()).pathname;
    if (path.startsWith('/local/')) {
      if(req.method()==='POST') {const body=req.postDataJSON();calls.push({path,body,csrf:req.headers()['x-csrf-token']});if(path==='/local/settings')Object.assign(state.github,{user:body.github_user || state.github.user});if(path==='/local/pause')state.paused=body.paused;}
      await route.fulfill({contentType:'application/json',body:JSON.stringify(path==='/local/state'?state:{csrf_token:'fixture-csrf'})});return;
    }
    const file=path==='/'?'index.html':path.replace('/static/','');
    await route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:await readFile(new URL(file,root),'utf8')});
  });
  await page.goto('http://curation.test/#token=fixture-launch');
  await page.getByRole('button',{name:'Example2026',exact:true}).waitFor();
  assert.equal(new URL(page.url()).hash,'');
  await page.getByRole('checkbox',{name:'Select Example2026',exact:true}).check();
  await page.getByRole('button',{name:'Validate now',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('queued'));
  assert(calls.some(c=>c.path==='/local/jobs'&&c.body.action==='validate'&&c.body.ids[0]==='one'&&c.csrf==='fixture-csrf'));
  await page.getByRole('button',{name:'Example2026',exact:true}).click();
  await page.getByRole('button',{name:'Problems',exact:true}).click();
  assert.match(await page.locator('.problem').textContent(),/C10/);
  assert.match(await page.locator('.problem').textContent(),/<script>alert/);
  assert.match(await page.locator('.problem').textContent(),/Choose a supported measurement/);
  await page.getByRole('button',{name:'Open file',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('default application'));
  assert(calls.some(c=>c.path==='/local/files/open'&&c.body.file==='outputs.xlsx'));
  await page.getByRole('button',{name:'Upload selected',exact:true}).click();
  assert.match(await page.locator('#upload-context').textContent(),/example.invalid.*curator/);
  assert(!calls.some(c=>c.path==='/local/jobs'&&c.body.action==='upload'));
  await page.getByRole('button',{name:'Validate and upload',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('upload job'));
  assert(calls.some(c=>c.path==='/local/jobs'&&c.body.action==='upload'));
  await page.getByRole('button',{name:'Assigned studies',exact:true}).click();
  assert.equal(await page.locator('#studies tr').count(),1);
  assert.match(await page.locator('#unmatched').textContent(),/NotLocal2026/);
  await page.locator('#study-search').fill('does-not-exist');
  assert.equal(await page.locator('#selection-count').textContent(),'0 studies selected');
  await page.getByRole('button',{name:'Connection settings',exact:true}).click();
  await page.locator('#settings-key').fill('fake-browser-key');
  await page.locator('#settings-dialog').getByRole('button',{name:'Cancel',exact:true}).click();
  assert.equal(await page.locator('#settings-key').inputValue(),'');
  await page.getByRole('button',{name:'Cancel queued job',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('Queued job canceled'));
  assert(calls.some(c=>c.path==='/local/jobs/cancel'&&c.body.ids[0]==='queued-job'));
  await page.getByRole('button',{name:'Clear finished history',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('Finished history cleared'));
  assert(calls.some(c=>c.path==='/local/history/clear'));
  await page.getByRole('button',{name:'Review unknown outcome',exact:true}).click();
  assert(!calls.some(c=>c.path==='/local/retry'));
  assert.match(await page.locator('#retry-context').textContent(),/Previous target: https:\/\/example.invalid/);
  await page.locator('#retry-acknowledge').check();
  await page.getByRole('button',{name:'Validate and retry upload',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('Explicit retry queued'));
  assert(calls.some(c=>c.path==='/local/retry'&&c.body.id==='one'&&c.body.acknowledge_unknown===true));
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);
  console.log('Curation browser smoke passed: session, validation, diagnostics, safe rendering, file opening, upload review, assignments, selection, credential clearing, cancellation, history, explicit retry, responsive layout.');
} finally {await browser.close();}
