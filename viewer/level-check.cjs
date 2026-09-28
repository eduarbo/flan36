// Exercise Level color continuity and the actual exported print assets.
// SPDX-License-Identifier: GPL-3.0-or-later
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'build/level-case/viewer-check');fs.mkdirSync(out,{recursive:true});
require('esbuild').buildSync({stdin:{contents:"export {applyTheme,setColor} from './appearance.js'; export {normalize,check} from './config.js'; export {selectedParts,mesh3MF,printKit} from './printing.js';",resolveDir:__dirname},bundle:true,platform:'node',format:'cjs',outfile:path.join(out,'level.cjs')});
const {applyTheme,setColor,normalize,check,selectedParts,mesh3MF,printKit}=require(path.join(out,'level.cjs'));
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p))),catalog=read('keycaps/catalog.json');
let cfg=normalize(catalog.default_configuration,catalog);
for(const side of ['left','right'])cfg.cases[side].style='level';
const themes=read('design/themes.json').themes;
for(const theme of themes){
 const themed=applyTheme(cfg,theme,['left','right']);assert.deepEqual(check(themed,catalog).errors,[],theme.name);
 for(const side of ['left','right'])assert.equal(themed.cases[side].plate_color,themed.frames[side].color);
 for(const [part,role] of [['frame','body'],['case','base_color'],['case','plate_color']]){
  const next=setColor(themed,['left'],part,role,'#456789');assert.deepEqual(check(next,catalog).errors,[]);
  assert.equal(next.cases.left.plate_color,'#456789');assert.equal(next.frames.left.color,'#456789');
  assert.deepEqual(next.cases.right,themed.cases.right);
 }
 const separate=structuredClone(themed);separate.cases.left.match_frame=false;
 const painted=setColor(separate,['left'],'case','plate_color','#abcdef');
 assert.equal(painted.cases.left.plate_color,'#abcdef');assert.equal(painted.frames.left.color,themed.frames.left.color);
}
if(process.argv.includes('--colors-only')){console.log(`PASS: ${themes.length} Level themes, linked HEX editing and independent colors`);process.exit(0);}
const scene=read('build/viewer-scene.json');
function stlBounds(base64){const b=Buffer.from(base64,'base64'),lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(let i=0,n=b.readUInt32LE(80);i<n;i++)for(let v=0;v<3;v++)for(let a=0;a<3;a++){const x=b.readFloatLE(84+50*i+12+12*v+4*a);lo[a]=Math.min(lo[a],x);hi[a]=Math.max(hi[a],x);}return [lo,hi];}
const parts=selectedParts(cfg,scene.printing,'both','complete');
for(const side of ['left','right']){
 const shell=parts.find(p=>p.id===`${side}-case-level-plate`);assert.ok(shell,'Selected kit lost Level shell');
 const bounds=stlBounds(shell.stl);assert.ok(Math.abs(bounds[0][2]-6.3)<1e-4);assert.ok(Math.abs(bounds[1][2]-13.39)<1e-4);
 assert.equal(crypto.createHash('sha256').update(Buffer.from(shell.stl,'base64')).digest('hex'),crypto.createHash('sha256').update(fs.readFileSync(path.join(root,shell.path))).digest('hex'));
 assert.ok(mesh3MF(shell).bytes.length>1000);
 for(const style of Object.keys(catalog.frame_styles)){
  const asset=scene.printing.assets[`${side}-frame-${style}`];assert.ok(Math.abs(stlBounds(asset.stl)[1][2]-13.39)<1e-4);
 }
}
const report={themes:themes.length,case_style:'level',frame_and_shell_top_mm:13.39,selected_parts:parts.map(p=>p.id),native_stl_bytes_match:true,print_3mf_generated:true,physical_acceptance:false};
fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report,null,2)+'\n');console.log('PASS: Level themes, exact native print bytes, 3MF and all frame heights');
global.requestAnimationFrame=callback=>setTimeout(callback,0);
printKit(cfg,scene.printing,{half:'both',scope:'shells'}).then(kit=>{
 const folder=path.join(root,'build/themes-print');fs.mkdirSync(folder,{recursive:true});
 fs.writeFileSync(path.join(folder,'level-shells.zip'),kit.bytes);
 console.log('Level shell kit saved for independent STL/3MF topology and registration checks');
}).catch(error=>{console.error(error);process.exitCode=1;});
