// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const esbuild=require('esbuild'),Module=require('node:module');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const bundled=await esbuild.build({stdin:{contents:"export * from './config.js';export * from './storage.js';",resolveDir:__dirname},bundle:true,write:false,platform:'node',format:'cjs'});
 const module=new Module(path.join(__dirname,'rebrand-runtime.cjs'));module.paths=Module._nodeModulePaths(__dirname);module._compile(bundled.outputFiles[0].text,path.join(__dirname,'rebrand-runtime.cjs'));
 const {check,normalize,restoreConfiguration,savedKey}=module.exports,catalog=JSON.parse(fs.readFileSync(path.join(root,'keycaps/catalog.json')));
 const presets=fs.readdirSync(path.join(root,'design/configurations')).filter(n=>n.endsWith('.json')).map(n=>JSON.parse(fs.readFileSync(path.join(root,'design/configurations',n))));
 for(const f of [catalog.default_configuration,...presets]){
  const old={...f,schema:'filo36-config-1'},current={...f,schema:'flan36-config-1'};
  assert.equal(check(old,catalog).errors.length,0);assert.equal(check(current,catalog).errors.length,0);assert.deepEqual(normalize(old,catalog),normalize(current,catalog));
  const map=new Map([['filo36.configuration.v1',JSON.stringify(old)]]),storage={getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};
  const result=restoreConfiguration(storage,catalog);assert.deepEqual(result.configuration,normalize(current,catalog));assert.equal(map.get('filo36.configuration.v1'),JSON.stringify(old));assert.equal(map.has(savedKey),false,'Restoring legacy data must not write during startup');
  const preferred=normalize(catalog.default_configuration,catalog);storage.setItem(savedKey,JSON.stringify(preferred));assert.deepEqual(restoreConfiguration(storage,catalog).configuration,preferred);
  storage.setItem(savedKey,'broken');assert.equal(restoreConfiguration(storage,catalog).configuration,null);assert.equal(map.get(savedKey),'broken');
  storage.setItem=()=>{throw Error('quota')};assert.equal(restoreConfiguration(storage,catalog).configuration,null);assert.equal(map.get(savedKey),'broken');
 }
 fs.mkdirSync(path.join(root,'build/reliability-fix'),{recursive:true});fs.writeFileSync(path.join(root,'build/reliability-fix/rebrand-config.json'),JSON.stringify({fixtures:presets.length+1,legacy_and_new_equivalent:true,legacy_storage_preserved:true,new_key_preferred:true,invalid_new_is_preserved:true,quota_does_not_lose_restored_configuration:true},null,2)+'\n');console.log('PASS: JS schemas, storage migration, precedence, invalid data and quota');
})().catch(e=>{console.error(e);process.exit(1)});
