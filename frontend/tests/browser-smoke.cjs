// Smoke test de UI con API simulada; requiere Playwright y un servidor estático local.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const base=process.env.PREVIEW_URL || 'http://127.0.0.1:8765';
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../../backend/app/data/curriculum/a1_curriculum.json'),'utf8'));
const dialogues=JSON.parse(fs.readFileSync(path.join(__dirname,'../../backend/app/data/curriculum/dialogues.json'),'utf8')).dialogues;
let topicId=0,lessonId=0;
data.modules.forEach((m,i)=>{m.id=i+1;m.lessons.forEach(l=>{l.id=++lessonId;l.topics.forEach(t=>{t.id=++topicId;t.status=t.id===1?'current':'new';t.mastery_level=0;});l.done_count=0;l.total_count=l.topics.length;l.completed=false;});});
dialogues.forEach((d,i)=>{d.id=i+1;d.turns.forEach((t,j)=>{t.id=j+1;t.order_index=j;});});
const topics=data.modules.flatMap(m=>m.lessons.flatMap(l=>l.topics));
const user={id:1,username:'Preview',current_level:'A1',streak_days:0,total_xp:0};
let profile={user_id:1,nickname:'Alex',job:'Developer',city:'San Salvador',interests:{},hidden_items:{dialogues:[],topics:[]}};

(async()=>{
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL || 'chrome',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',d=>d.dismiss());
  await page.addInitScript(user=>{
   localStorage.setItem('duofeynman_token','preview');localStorage.setItem('duofeynman_user',JSON.stringify(user));
   HTMLMediaElement.prototype.play=()=>Promise.resolve();
  },user);
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url()), p=url.pathname;
   let body={};
   if(p==='/api/me')body=user;
   else if(p==='/api/me/profile') {if(route.request().method()==='PUT') profile={...profile,...route.request().postDataJSON()};body=profile;}
   else if(p==='/api/curriculum/path')body={modules:data.modules,next_topic:{...topics[0],topic_id:1,level:'A1',lesson_title_en:'Greetings'}};
   else if(p.startsWith('/api/curriculum/topics/'))body=topics.find(t=>t.id===Number(p.split('/').pop()));
   else if(p==='/api/attempts/start')body={id:1};
   else if(p==='/api/attempts/stt-status')body={available:true};
   else if(p==='/api/srs/stats')body={due_today:0};
   else if(p==='/api/srs/due')body=[{topic:topics[0],repetitions:1,interval_days:3}];
   else if(p==='/api/dialogues')body=dialogues;
   else if(p.startsWith('/api/dialogues/'))body=dialogues[Number(p.split('/').pop())-1];
   else if(p==='/api/progress/dashboard')body={summary:{...user,mastered_topics:0,average_score:0},last_7_days:[],achievements_unlocked:[],achievements_pending:[]};
   else if(p==='/api/progress/insights')body={averages:{score:0,fluency:0,code_switch_rate:0,avg_words_per_attempt:0},spanish_leaks:[],grammar_drills:[],weak_topics:[],fast_mastered:[],errors_by_category:[]};
   else if(p==='/api/dictation/next')body={dictation_id:'12345678-1234-1234-1234-123456789012',hint_en:topics[0].prompt_en,hint_es:topics[0].prompt_es,word_count:6};
   else if(p.endsWith('/audio') || p==='/api/tts')return route.fulfill({status:200,contentType:'audio/wav',body:Buffer.from('RIFF')});
   else if(p==='/api/attempts/round')body={overall_score:.8,fluency_score:.8,word_count:12,vocab_coverage:.8,connector_coverage:1,code_switch_rate:0,encouragement_es:'Buen intento. Mirá las correcciones y volvé a intentar.',next_action:'REFINE',errors:[],socratic_questions:['What do you do next?'],subscores:{}};
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto(base);
  await page.locator('.topic-btn').first().waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'),'en');
  const initial=await page.locator('#view-home').innerText();
  assert(!initial.includes('Tu camino'));
  assert(initial.includes(topics[0].prompt_en));
  await page.screenshot({path:path.join(require('node:os').tmpdir(),'duofeynman-home-smoke.png'),animations:'disabled'});
  const translation=page.locator('.topic-btn').first().locator('xpath=following-sibling::button[1]');
  await translation.focus(); await page.keyboard.press('Enter');
  assert((await page.locator('#view-home').innerText()).includes(topics[0].prompt_es));
  assert((await page.locator('#view-home').innerText()).includes(topics[0].prompt_en));
  await translation.click();
  await page.locator('.topic-btn').first().click();
  await page.locator('.mode-btn[data-mode="write"]').click();
  await page.locator('#write-area').fill('Hello, my name is Alex. I am from El Salvador.');
  await page.locator('#btn-submit-write').click();
  await page.locator('#feedback:not(.hidden)').waitFor();
  assert((await page.locator('#encouragement').innerText()).includes('Good try.'));
  const views=['profile','dashboard','srs','dictation','dialogues'];
  for(const action of views){
   await page.locator('.view.active .btn-back-home').click();
   await page.locator(`.quick-btn[data-action="${action}"]`).click();
   await page.waitForTimeout(150);
   assert.equal(await page.locator('.view.active').getAttribute('id'),'view-'+action);
   if(action==='srs') {
    assert((await page.locator('#srs-content').textContent()).includes('You have 1 topic to review.'));
    assert((await page.locator('#srs-content').textContent()).includes(topics[0].prompt_en));
   }
   if(action==='profile')assert(!(await page.locator('[name="job"]').getAttribute('placeholder')).includes('Ej:'));
   const size=await page.evaluate(()=>({body:document.documentElement.scrollWidth,screen:innerWidth}));
   assert(size.body<=size.screen+2,`${action}: horizontal overflow ${JSON.stringify(size)}`);
  }
  await page.locator('.dlg-start').first().click();
  await page.locator('#view-chat.active').waitFor();
  await page.locator('#chat-setting .setting-label').waitFor();
  assert((await page.locator('#chat-setting').textContent()).includes('Scene context'));
  await page.waitForTimeout(400);
  await page.screenshot({path:path.join(require('node:os').tmpdir(),'duofeynman-browser-smoke.png'),fullPage:true,animations:'disabled'});
  assert.deepEqual(errors,[]);
  console.log('BROWSER_SMOKE_OK: English UI, keyboard translation, practice, five views, mobile layout, chat, CSP');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
