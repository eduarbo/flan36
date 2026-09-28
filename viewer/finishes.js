// SPDX-License-Identifier: GPL-3.0-or-later
import finishes from '../design/frame-finishes.json';
export {finishes};

export function framePalette(style,body,accents){
  const theme=finishes.styles[style];
  const p=theme?{...theme.colors,body:body||theme.colors.body}:{body:body||'#304d4e'};
  for(const role of ['detail','accent','secondary'])p[role]=accents?.[role]||p[role]||p.body;return p;
}
export function createFrameFinishes(geometryFor,material){
  const cache=new Map();
  return function frame(style,side,body,accents){
    const path=`mechanical/revI/${side}-frame-${style}.stl`;
    if(!cache.has(path)){
      // Groups come from exact native material volumes. Geometry, winding and
      // role boundaries must survive unchanged into previews and GLB exports.
      const g=geometryFor(path).clone();
      if(!g.groups.length){
        if(finishes.styles[style])throw Error('Native flush materials unavailable: '+path);
        g.addGroup(0,g.index.count,0);
      }
      let offset=0;
      for(const group of g.groups){
        if(group.start!==offset||group.count%3||!Number.isInteger(group.materialIndex)||!finishes.roles[group.materialIndex])throw Error('Invalid native frame material group: '+path);
        offset+=group.count;
      }
      if(offset!==g.index.count)throw Error('Incomplete native frame material groups: '+path);
      cache.set(path,g);
    }
    const palette=framePalette(style,body,accents);
    return {geometry:cache.get(path),material:finishes.roles.map(role=>material(palette[role]||palette.body)),palette};
  };
}
