// Regresiones del estado del navegador, sin dependencias ni red.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = name => fs.readFileSync(path.join(__dirname, '../js', name), 'utf8');

function store() {
  const data = new Map();
  return { get: k => data.get(k) ?? null, set: (k,v) => data.set(k,v), remove: k => data.delete(k),
    getJSON: (k,d) => data.has(k) ? JSON.parse(data.get(k)) : d,
    setJSON: (k,v) => data.set(k, JSON.stringify(v)) };
}

test('perfil conserva cambios offline y los separa por usuario', async () => {
  let online = false, id = 1;
  const profiles = {1: {user_id:1,nickname:'old'}, 2:{user_id:2,nickname:'other'}};
  const ctx = vm.createContext({Store:store(), console, API:{
    getUser: () => ({id}), getProfile: async () => profiles[id],
    putProfile: async p => {if(!online) throw Error('offline'); profiles[id]=p; return p;}
  }});
  vm.runInContext(source('profile.js'),ctx);
  await vm.runInContext("Profile.save({nickname:'new'})",ctx);
  id=2;
  assert.equal(vm.runInContext('Profile.get().nickname',ctx),'');
  await vm.runInContext('Profile.loadFromServer()',ctx);
  assert.equal(vm.runInContext('Profile.get().nickname',ctx),'other');
  id=1; online=true;
  await vm.runInContext('Profile.loadFromServer()',ctx);
  assert.equal(profiles[1].nickname,'new');
  assert.equal(profiles[2].nickname,'other');
});

test('una respuesta de guardado vieja no pisa una edición nueva', async () => {
  const pending=[];
  const ctx=vm.createContext({Store:store(),console,API:{getUser:()=>({id:1}),
    putProfile: p=>new Promise(resolve=>pending.push({p,resolve}))}});
  vm.runInContext(source('profile.js'),ctx);
  const first=vm.runInContext("Profile.save({nickname:'first'})",ctx);
  const second=vm.runInContext("Profile.save({nickname:'second'})",ctx);
  pending[0].resolve(pending[0].p);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(pending[1].p.nickname,'second');
  pending[1].resolve(pending[1].p);
  await Promise.all([first,second]);
  assert.equal(vm.runInContext('Profile.get().nickname',ctx),'second');
});

test('TTS descarta audio que llega después de stop o de otro pedido', async () => {
  const pending=[],played=[];
  const ctx=vm.createContext({Store:store(),console,window:{},
    URL:{createObjectURL:b=>b,revokeObjectURL:()=>{}},
    API:{tts:()=>new Promise(resolve=>pending.push(resolve))},
    Audio:class {constructor(url){this.url=url;} async play(){played.push(this.url);} pause(){}}
  });
  vm.runInContext(source('tts.js'),ctx);
  const first=vm.runInContext("TTS.speak('first')",ctx);
  vm.runInContext('TTS.stop()',ctx);
  pending[0]('first audio'); await first;
  assert.equal(played.length,0);
  const second=vm.runInContext("TTS.speak('second')",ctx);
  const third=vm.runInContext("TTS.speak('third')",ctx);
  pending[2]('third audio'); await third;
  pending[1]('second audio'); await second;
  assert.deepEqual(played,['third audio']);
});
