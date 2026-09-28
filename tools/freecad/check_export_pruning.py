"""Check current exporter pruning against tessellation-independent bounds.

python3 tools/freecad/run_macos.py tools/freecad/check_export_pruning.py \
  --source mechanical/revI/Flan36.FCStd \
  --output validation/revI-export-pruning.json

This supplemental check proves equivalence for the supplied native snapshot.
It does not assert that ordinary BoundBox is safe for future geometry: it can
undershoot curved geometry after tessellation. No native document is opened,
recomputed or saved. Stored BReps and identity AppLinks are read directly.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse,ast,hashlib,json,os,sys,time,traceback,xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
import FreeCAD as A,Part,MeshPart
ROOT=Path(__file__).resolve().parents[2]
EXPORTER=ROOT/'tools/freecad/export_revI.py'
AXES=('XMin','YMin','ZMin','XMax','YMax','ZMax')
def log(s):sys.__stdout__.write(s+'\n');sys.__stdout__.flush()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(b):return tuple(getattr(b,k) for k in AXES)
def possible(a,b):return all(min(a[i+3],b[i+3])>max(a[i],b[i]) for i in range(3))
def solid_only(s):return s.ShapeType=='Solid' or (s.ShapeType in ('Compound','CompSolid') and all(solid_only(c) for c in s.childShapes()))
class ExactBounds:
 def __init__(self):self.values={};self.hits=0;self.misses=0
 def get(self,s):
  key=s.exportBrepToString()
  if key in self.values:self.hits+=1;return self.values[key]
  value=bounds(s.optimalBoundingBox(False,False));self.values[key]=value;self.misses+=1;return value
def prepare(name,s,cache):
 assert not s.isNull() and s.isValid(),name
 # Same main-shape meshing settings as frozen export_revI.py. Mesh lives only
 # in this independent in-memory shape, never in a native document.
 m=MeshPart.meshFromShape(Shape=s,LinearDeflection=.03,AngularDeflection=.12,Relative=False)
 solids=s.Solids
 return {'name':name,'shape':s,'ordinary':bounds(s.BoundBox),'analytic':cache.get(s),'solid_only':solid_only(s),'solids':solids,'ordinary_children':[bounds(x.BoundBox) for x in solids],'analytic_children':[cache.get(x) for x in solids]}
def selection(a,b,kind):
 if not possible(a[kind],b[kind]):return ('empty',(),())
 if not a['solid_only'] or not b['solid_only'] or not a['solids'] or not b['solids']:return ('full',(),())
 pairs=[(i,j) for i,x in enumerate(a[kind+'_children']) for j,y in enumerate(b[kind+'_children']) if possible(x,y)]
 return ('selected',tuple(sorted({i for i,j in pairs})),tuple(sorted({j for i,j in pairs}))) if pairs else ('empty',(),())
def selected_volume(a,b,sel):
 mode,ai,bi=sel
 if mode=='empty':return 0.
 if mode=='full':return a['shape'].common(b['shape']).Volume
 sa=a['solids'][ai[0]] if len(ai)==1 else Part.makeCompound([a['solids'][i] for i in ai])
 sb=b['solids'][bi[0]] if len(bi)==1 else Part.makeCompound([b['solids'][i] for i in bi])
 return sa.common(sb).Volume

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,default=ROOT/'mechanical/revI/Flan36.FCStd')
 parser.add_argument('--output',type=Path,default=ROOT/'validation/revI-export-pruning.json')
 args,_=parser.parse_known_args()
 SOURCE=args.source.resolve();OUT=args.output.resolve();cache=ExactBounds()
 try:
  start=time.perf_counter();before=digest(SOURCE)
  exporter_hash=digest(EXPORTER)
  module=ast.parse(EXPORTER.read_text());fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='exact_common');ns={'Part':Part};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(EXPORTER),'exec'),ns);original=ns['exact_common']
  z=ZipFile(SOURCE);tree=ET.fromstring(z.read('Document.xml'));types={o.attrib['name']:o.attrib['type'] for o in tree.findall('./Objects/Object')};objects={o.attrib['name']:{p.attrib['name']:p for p in o.findall('./Properties/Property')} for o in tree.findall('./ObjectData/Object')}
  def attr(name,key,field='value',default=None):
   p=objects[name].get(key)
   return p[0].attrib.get(field,default) if p is not None and len(p) else default
  def identity_placement(name,key):
   p=objects[name].get(key)
   if p is None:return True
   d=p[0].attrib
   return all(abs(float(d[k])-v)<1e-12 for k,v in [('Px',0),('Py',0),('Pz',0),('Q0',0),('Q1',0),('Q2',0),('Q3',1)])
  records={};links={}
  def record(name):
   if name in records:return records[name]
   if types.get(name)=='App::Link':
    assert identity_placement(name,'LinkPlacement') and attr(name,'Scale')=='1.0000000000000000',name
    source=attr(name,'LinkedObject','name');assert identity_placement(source,'Placement'),(name,source,'linked source placement must be identity for this raw replay');links[name]=source;records[name]=record(source);return records[name]
   s=Part.Shape();s.importBrepFromString(z.read(attr(name,'Shape','file')).decode());records[name]=prepare(name,s,cache);return records[name]
  result={'schema':'flan36-export-pruning-audit-1','source_sha256':before,'exporter_sha256':exporter_hash,'checker_sha256':digest(Path(__file__)),'physical_acceptance':False,'native_opened':False,'native_recomputed':False,'native_saved':False,'source_file':SOURCE.name,'mesh_settings':{'linear_deflection_mm':.03,'angular_deflection':.12,'relative':False},'method':'Replay frozen exporter logical pair categories using saved local BReps and verified identity AppLinks. Compare parent and solid-child selections from ordinary and analytic bounds. Identical selections imply identical Boolean operands; any changed selection is evaluated with both exact Boolean operands. Analytic bounds are cached by complete immutable BRep string.','halves':{}}
  for side,prefix in [('left','L_'),('right','R_')]:
   names=[n for n in objects if attr(n,'PartID',default='').startswith(side+'-') and (attr(prefix+'Half','DisplayCoverInstalled')=='true' or attr(n,'Layer')!='lid')]
   active={attr(n,'PartID')[len(side)+1:]:record(n) for n in names};assert len(active)==32,(side,len(active))
   frames={attr(n,'FrameStyle'):record(n) for n in objects if n.startswith(prefix) and 'FrameStyle' in objects[n] and types[n]!='App::Link'}
   batteries={attr(n,'BatteryStyle'):record(n) for n in objects if n.startswith(prefix) and 'BatteryStyle' in objects[n] and types[n]!='App::Link'}
   cases={n[len(prefix+'Case_'):]:record(n) for n in objects if n.startswith(prefix+'Case_') and n.endswith(('_base','_plate'))}
   usb=prepare(side+'-usb-corridor',Part.makeBox(12,20,5,A.Vector(116.8 if side=='left' else 31.2,-18.8,6.7)),cache)
   log(side+': prepared '+str(len(active))+' active parts, '+str(len(frames))+' frames, '+str(len(cases))+' case pieces, '+str(len(batteries))+' cells')
   pairs=[]
   def add(category,an,a,bn,b):pairs.append((category,an,a,bn,b))
   activeitems=list(active.items())
   for i,(an,a) in enumerate(activeitems):
    for bn,b in activeitems[i+1:]:add('active',an,a,bn,b)
   for ident,a in batteries.items():
    for bn,b in activeitems:
     if bn!='battery':add('battery',ident,a,bn,b)
   for ident,a in frames.items():
    for bn,b in activeitems:
     if bn!='electronics-lid':add('frame',ident,a,bn,b)
    add('frame-usb',ident,a,'usb',usb)
   for ident,a in cases.items():
    for bn,b in activeitems:
     if bn not in ['tray','key-plate']:add('case',ident,a,bn,b)
    for bn,b in frames.items():add('case-frame',ident,a,bn,b)
    if ident.endswith('_base'):add('case-base-plate',ident,a,ident[:-5]+'_plate',cases[ident[:-5]+'_plate'])
   differences=[];counts={};tested=0
   for category,an,a,bn,b in pairs:
    counts[category]=counts.get(category,0)+1
    ordinary=selection(a,b,'ordinary');analytic=selection(a,b,'analytic')
    if ordinary==analytic:continue
    log(side+' discrepancy '+category+' '+an+' / '+bn)
    ov=selected_volume(a,b,ordinary);av=selected_volume(a,b,analytic);frozen=original(a['shape'],b['shape']).Volume;assert abs(ov-frozen)<1e-9,(side,an,bn,ov,frozen)
    differences.append({'category':category,'a':an,'b':bn,'ordinary_mode':ordinary[0],'analytic_mode':analytic[0],'ordinary_selected_children':[len(ordinary[1]),len(ordinary[2])],'analytic_selected_children':[len(analytic[1]),len(analytic[2])],'ordinary_volume_mm3':ov,'analytic_volume_mm3':av,'difference_mm3':av-ov,'missed_over_exporter_threshold':av>.001 and ov<=.001});tested+=1
   missed=[r for r in differences if r['missed_over_exporter_threshold']]
   wire_bounds=[{'object':prefix+'WireStudy'+str(i),'ordinary_bounds_mm':record(prefix+'WireStudy'+str(i))['ordinary'],'analytic_bounds_mm':record(prefix+'WireStudy'+str(i))['analytic']} for i in range(2)]
   result['halves'][side]={'active_count':len(active),'frame_count':len(frames),'case_piece_count':len(cases),'battery_profile_count':len(batteries),'logical_pair_counts':counts,'logical_pairs_checked':len(pairs),'gate_selection_differences':differences,'missed_intersections':missed,'wire_bounds':wire_bounds};log(side+': complete; '+str(len(pairs))+' pairs, '+str(tested)+' changed selections, '+str(len(missed))+' missed intersections')
  result.update(source_unchanged=before==digest(SOURCE),exporter_unchanged=exporter_hash==digest(EXPORTER),seconds=time.perf_counter()-start,analytic_cache={'hits':cache.hits,'misses':cache.misses},verified_identity_links=links)
  result['passed']=result['source_unchanged'] and result['exporter_unchanged'] and not any(h['missed_intersections'] for h in result['halves'].values())
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(result,indent=2)+'\n');log('RESULT '+str(OUT)+' passed='+str(result['passed']));os._exit(0 if result['passed'] else 2)
 except BaseException:traceback.print_exc(file=sys.__stdout__);sys.__stdout__.flush();os._exit(1)

if __name__=='__main__':main()
