"""Read back native source, apply/viewer round trip, change a parameter, reopen.
Only temporary copies under build/revI are saved.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import sys,json,hashlib,copy,os,argparse
from pathlib import Path
import FreeCAD as A
import FreeCADGui as G
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/freecad'))
from configuration import apply,extract
from keycap_config import normalize
argv=sys.argv[1:]
while argv and not argv[0].startswith('--'):argv.pop(0)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,default=ROOT/'mechanical/revI/Flan36.FCStd')
parser.add_argument('--report',type=Path,default=ROOT/'validation/revI-freecad.json')
args=parser.parse_args(argv)
trial_directory=ROOT/'build/revI' if args.report.resolve()==(ROOT/'validation/revI-freecad.json').resolve() else args.report.parent
trial_directory.mkdir(parents=True,exist_ok=True)
args.report.parent.mkdir(parents=True,exist_ok=True)
assert args.source.resolve()!=(trial_directory/'customized.FCStd').resolve(),'The source must not be the temporary study'
G.showMainWindow();G.getMainWindow().hide()
print('Opening native configuration source',file=sys.__stdout__,flush=True)
doc=A.openDocument(str(args.source));doc.recompute()
sourcehash=hashlib.sha256(args.source.read_bytes()).hexdigest()
reference_roof=float(doc.Parameters.FrameTop)
opaque_samples=0
for obj in [o for o in doc.Objects if hasattr(o,'FrameStyle')]:
    right=obj.Name.startswith('R_')
    for x in [111.6,134.4]:
        for y in [25,40,55]:
            for z in [reference_roof-1.7,reference_roof-1.4]:
                # Body walls must remain present immediately below the roof.
                assert obj.Shape.isInside(A.Vector(160-x if right else x,-y,z),1e-6,False),(obj.Name,'side-wall gap',x,y,z)
                opaque_samples+=1
original=extract(doc);expected=normalize(json.loads((ROOT/'design/configurations/default.json').read_text()))
# The saved reference predates per-key colors; verify its geometry and retain its actual native colors.
for side,keys in original['keycaps'].items():
    for ref,key in keys.items():expected['keycaps'][side][ref]['color']=key['color']
assert original==expected
assert not any(o.TypeId.endswith('Python') for o in doc.Objects),'Native source requires a custom proxy'
nextconfig=json.loads((ROOT/'design/configurations/saddle-sculpted.json').read_text())
nextconfig['keycaps']['left']['K30']={'variant':'choc_stem_mx_size_normal_90deg','rotation_deg':90}
nextconfig['batteries']={'left':'301230','right':'adafruit-1570'}
nextconfig['cases']={'left':{'style':'rim','cover':False},'right':{'style':'terrace','cover':True}}
nextconfig['frames']['left']={'style':'gameboy','color':'#ad7656'}
nextconfig['frames']['right']={'style':'talavera','color':'#596c7a'}
nextconfig=normalize(nextconfig)
nextconfig['cases']['left'].update(base_color='#e4a266',plate_color='#202735',match_frame=True)
nextconfig['frames']['left'].update(color='#e4a266',accents={'detail':'#181c29','accent':'#abe8bc','secondary':'#9364c7'})
margin=apply(doc,nextconfig);assert extract(doc)==nextconfig
assert not doc.L_ActiveFrame.Visibility and doc.R_ActiveFrame.Visibility
assert not doc.L_SteelTarget0.Visibility
assert doc.L_ActiveTray.LinkedObject.CaseStyle=='rim' and doc.R_ActiveTray.LinkedObject.CaseStyle=='terrace'
legacy=copy.deepcopy(original);legacy.pop('cases');apply(doc,legacy);assert extract(doc)==normalize(legacy)
assert all(extract(doc)['cases'][side]['style']=='solid' for side in ['left','right'])
apply(doc,nextconfig)
bad=copy.deepcopy(nextconfig);bad['cases']['right']['style']='unknown'
try:apply(doc,bad);raise AssertionError('Invalid case accepted')
except ValueError:pass
assert extract(doc)==nextconfig
for side,prefix in [('left','L_'),('right','R_')]:
    for k in json.loads((ROOT/'design/layout.json').read_text())['halves'][side]:
        o=doc.getObject(prefix+k['ref']);assert abs(o.Placement.Base.x-k['x'])<1e-6 and abs(o.Placement.Base.y+k['y'])<1e-6
        assert abs(o.Mesh.BoundBox.ZMin-11.7)<1e-5,(o.Name,o.Mesh.BoundBox.ZMin,o.Placement.Base.z)
    assert doc.getObject(prefix+'ActiveFrame').Shape.isValid()
    battery=doc.getObject(prefix+'ActiveBattery')
    assert battery.LinkedObject.BatteryStyle==nextconfig['batteries'][side]
    assert all(abs(getattr(battery.Shape.BoundBox,k)-getattr(battery.LinkedObject.Shape.BoundBox,k))<1e-6 for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax'])
    assert abs(battery.Shape.BoundBox.ZMin-float(doc.Parameters.BatteryBottom))<1e-6
invalid=copy.deepcopy(nextconfig);invalid['keycaps']['left']['K30']['rotation_deg']=0
try:apply(doc,invalid);raise AssertionError('Invalid rotation accepted')
except ValueError:pass
assert extract(doc)==nextconfig
cell=doc.Parameters.getCellFromAlias('FrameTop');doc.Parameters.set(cell,str(reference_roof+.4)+' mm');doc.recompute()
for obj in doc.Objects:assert 'Invalid' not in obj.State,(obj.Name,obj.State)
for prefix in ['L_','R_']:
    obj=doc.getObject(prefix+'ActiveFrame')
    print('Edited frame readback',prefix,obj.LinkedObject.Name,obj.Shape.BoundBox.ZMax,flush=True)
    assert abs(obj.Shape.BoundBox.ZMax-(reference_roof+.4))<1e-6
path=trial_directory/'customized.FCStd';doc.saveAs(str(path));A.closeDocument(doc.Name)
doc=A.openDocument(str(path));doc.recompute();assert extract(doc)==nextconfig
for prefix in ['L_','R_']:assert abs(doc.getObject(prefix+'ActiveFrame').Shape.BoundBox.ZMax-(reference_roof+.4))<1e-6
assert hashlib.sha256(args.source.read_bytes()).hexdigest()==sourcehash
report={'source_sha256':sourcehash,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native_features_no_custom_proxy':True,'configuration_roundtrip':True,'mixed_battery_profiles_roundtrip':True,'mixed_cases_and_open_cover_roundtrip':True,'legacy_configuration_normalized':True,'reopened_customized_file':True,'all_36_key_centres_unchanged':True,'stem_tip_datum_mm':11.7,'FrameTop_edit_mm':[reference_roof,reference_roof+.4],'preset':'saddle-sculpted','thumb_variant':'MX-size Normal 90deg','frames':['gameboy','talavera'],'invalid_configuration_rejected_atomically':True,'xy_margin_mm':margin,'source_file_unchanged':True,'opaque_side_wall_samples':opaque_samples}
args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
A.closeDocument(doc.Name)

# Avoid the known bundled Qt teardown crash after all assertions and saves.
# This is scoped to run_macos.py's own subprocess, never an interactive FreeCAD session.
if os.environ.get('FILO_FREECAD_SUBPROCESS')=='1':
    sys.__stdout__.flush();sys.__stderr__.flush();os._exit(0)
