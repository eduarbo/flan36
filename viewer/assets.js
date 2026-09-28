// SPDX-License-Identifier: GPL-3.0-or-later
export function decodeBytes(text){
 if(Uint8Array.fromBase64)return Uint8Array.fromBase64(text);
 const binary=atob(text),bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);return bytes;
}
export async function unpack(bytes){return JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text());}
export function printLoader(descriptor,embedded){
 let pending;
 return ()=>pending??=(async()=>{
  let bytes;
  if(embedded.textContent.trim())bytes=decodeBytes(embedded.textContent);
  else{const response=await fetch(descriptor.url);if(!response.ok)throw Error('Print files could not be downloaded. Try again when connected.');bytes=new Uint8Array(await response.arrayBuffer());}
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  if(digest!==descriptor.sha256)throw Error('Print files do not match this viewer. Reload or use the offline download.');
  return unpack(bytes);
 })().catch(error=>{pending=null;throw error;});
}
