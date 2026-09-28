// SPDX-License-Identifier: GPL-3.0-or-later
import {copy} from './config.js';
export function createHistory(initial,limit=40){
 let past=[],future=[],current=copy(initial),group=null;
 return {
  record(next,gesture=null){if(JSON.stringify(current)===JSON.stringify(next))return;
   if(!gesture||gesture!==group){past.push(current);if(past.length>limit)past.shift();}
   current=copy(next);future=[];group=gesture;
  },
  peekUndo(){return past.length?copy(past.at(-1)):null;},peekRedo(){return future.length?copy(future.at(-1)):null;},
  undo(){if(!past.length)return null;future.push(current);current=past.pop();group=null;return copy(current);},
  redo(){if(!future.length)return null;past.push(current);current=future.pop();group=null;return copy(current);},
  endGesture(){group=null;},
  get canUndo(){return past.length>0;},get canRedo(){return future.length>0;}
 };
}
