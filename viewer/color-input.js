// SPDX-License-Identifier: GPL-3.0-or-later
// Keep the native swatch, but make every color usable as plain copyable text.
export function normalizeHex(value){
 const hex=value.trim().replace(/^#/,'');
 if(/^[0-9a-f]{3}$/i.test(hex))return '#'+[...hex].map(c=>c+c).join('').toLowerCase();
 return /^[0-9a-f]{6}$/i.test(hex)?'#'+hex.toLowerCase():null;
}
export function enhanceColorInput(swatch){
 const editor=document.createElement('div');editor.className='color-editor';
 swatch.before(editor);editor.append(swatch);
 const hex=document.createElement('input');hex.id=swatch.id+'-hex';hex.type='text';hex.className='hex-input';hex.spellcheck=false;hex.autocomplete='off';hex.setAttribute('autocapitalize','off');hex.setAttribute('aria-label',swatch.getAttribute('aria-label')+' HEX');hex.placeholder='#RRGGBB';
 const copy=document.createElement('button');copy.type='button';copy.className='copy-color';copy.textContent='Copy';copy.setAttribute('aria-label','Copy '+swatch.getAttribute('aria-label')+' HEX');
 const notice=document.createElement('small');notice.id=hex.id+'-notice';notice.className='color-notice';notice.setAttribute('role','status');hex.setAttribute('aria-describedby',notice.id);
 editor.append(hex,copy,notice);
 let mixed=false,committing=false,last='';
 function clear(){hex.removeAttribute('aria-invalid');notice.textContent='';}
 function commit(){
  const color=normalizeHex(hex.value);if(!color){if(!mixed||hex.value){hex.setAttribute('aria-invalid','true');notice.textContent='Use 3 or 6 hex digits, e.g. #34A87C.';}return false;}
  clear();committing=true;hex.value=color;swatch.value=color;
  swatch.dispatchEvent(new Event('input',{bubbles:true}));swatch.dispatchEvent(new Event('change',{bubbles:true}));committing=false;return true;
 }
 hex.addEventListener('focus',()=>hex.select());
 hex.addEventListener('input',()=>{clear();copy.disabled=swatch.disabled||!normalizeHex(hex.value);if(/^#?[0-9a-f]{6}$/i.test(hex.value.trim()))commit();});
 hex.addEventListener('change',commit);
 hex.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();commit();}else if(event.key==='Escape'){clear();hex.value=mixed?'':swatch.value;copy.disabled=mixed;hex.select();}});
 copy.onclick=async()=>{
  const color=normalizeHex(hex.value);if(!color)return;
  try{await navigator.clipboard.writeText(color);notice.textContent='Copied.';}
  catch{hex.focus();hex.select();notice.textContent='Selected — copy with your keyboard or text menu.';}
 };
 return {sync(values,disabled=swatch.disabled){
  mixed=new Set(values.map(v=>v.toLowerCase())).size>1;swatch.disabled=disabled;hex.disabled=disabled;
  const current=JSON.stringify(values);
  if(committing||current!==last||document.activeElement!==hex){hex.value=mixed?'':values[0].toLowerCase();clear();}last=current;
  hex.placeholder=mixed?'Mixed':'#RRGGBB';copy.disabled=disabled||!normalizeHex(hex.value);
 }};
}
