"""Historical additive-roof acceptance check; its command is retired.
Current slim/flush validation is performed by install_slim_flush.py and
flush_frames.validate_variant. The old unchanged-geometry contract is preserved
below only as historical evidence, not applied to the new material partition.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from pathlib import Path
import sys,os,json,argparse,hashlib,zipfile,traceback
import FreeCAD as A
import FreeCADGui as G
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from install_extra_frames import snapshot,snapshot_changes
from extra_frames import load_spec,find_smooth,validate_variant,STYLES
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(*v):sys.__stdout__.write(' '.join(map(str,v))+'\n');sys.__stdout__.flush()
def main():
 raise SystemExit('Historical additive-roof checker retired. Use tools/freecad/install_slim_flush.py and the current flush-material validation; reproduce the old unchanged-source contract only at its recorded historical commit.')
 args=sys.argv[1:];own=str(Path(__file__).resolve())
 if own in args:args=args[args.index(own)+1:]
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args(args)
 source_hash,candidate_hash=sha(a.source),sha(a.candidate)
 G.showMainWindow();G.getMainWindow().hide()
 original=A.openDocument(str(a.source.resolve()));original.recompute();names={o.Name for o in original.Objects};before=snapshot(original,names)
 params={alias:original.Parameters.getContents(original.Parameters.getCellFromAlias(alias)) for alias in json.loads((ROOT/'design/revI.json').read_text())['parameters']}
 groups={o.Name:{c.Name for c in o.Group} for o in original.Objects if 'Group' in o.PropertiesList}
 A.closeDocument(original.Name);log('Original snapshot',len(names),'objects')
 doc=A.openDocument(str(a.candidate.resolve()));doc.recompute();after=snapshot(doc,names);equivalent={}
 changes=snapshot_changes(before,after,equivalent);assert not changes,changes
 assert params=={alias:doc.Parameters.getContents(doc.Parameters.getCellFromAlias(alias)) for alias in params}
 for name,members in groups.items():assert members.issubset({c.Name for c in doc.getObject(name).Group}),(name,'missing original group members')
 log('Original objects preserved; equivalent changed BREP records',len(equivalent))
 spec=load_spec(ROOT);halves={}
 for side,prefix in [('left','L_'),('right','R_')]:
  doc.getObject(prefix+'Half').Placement=A.Placement();doc.recompute();smooth=find_smooth(doc,side);halves[side]={}
  for style in STYLES:
   log('Checking native frame',side,style);halves[side][style]=validate_variant(doc,side,smooth,doc.getObject(prefix+'ExtraFrame_'+style+'_Final'),spec)
 A.closeDocument(doc.Name)
 assert sha(a.source)==source_hash and sha(a.candidate)==candidate_hash
 with zipfile.ZipFile(a.candidate) as z:assert 'GuiDocument.xml' in z.namelist()
 paths=['tools/freecad/check_frame_extensions.py','tools/freecad/install_extra_frames.py','tools/freecad/shape_equivalence.py','tools/freecad/extra_frames.py','design/frame-extensions.json']
 result={'status':'saved_and_reopened','native_reopen_recompute_passed':True,'gui_document_preserved':True,'source_sha256':source_hash,'output_sha256':candidate_hash,'source_objects_preserved':len(names),'original_geometry_appearance_unchanged':True,'source_parameters_unchanged':True,'halves':halves,'equivalent_brep_hash_changes':equivalent,'inputs':[{'path':f,'sha256':sha(ROOT/f)} for f in paths],'manufacturing_ready':False,'physical_fit':'unqualified; digital geometry only'}
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n');log('PASS native source preservation and eight closed frames')
if __name__=='__main__':
 status=0
 try:main()
 except Exception:traceback.print_exc();status=1
 sys.__stdout__.flush();sys.__stderr__.flush();os._exit(status)
