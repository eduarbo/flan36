#!/usr/bin/env python3
"""Bind the Level delivery to current native, PCB, viewer and print evidence.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from check_slim_flush_delivery import (ROOT,sha,read,bound_hash,require,
    native_report,viewer_report,stl_bounds,inputs)

OUTPUT=ROOT/'validation/revI-level-delivery.json'

def run():
    contract=read('design/level-case-workflow.json')
    protected=['design/layout.json','design/revI-profiles.json','design/revI-mounts.json',
        'design/revI-magnets.json','design/batteries.json','design/revI-wire-study.json',
        'hardware/revI/flan36-left.kicad_pcb','hardware/revI/flan36-right.kicad_pcb']
    for path in protected:
        original=subprocess.check_output(['git','show',contract['source_commit']+':'+path],cwd=ROOT)
        bound_hash(path,hashlib.sha256(original).hexdigest())
    native=sha('mechanical/revI/Flan36.FCStd');model=read('design/revI.json')
    require(model['fcstd_sha256']==native,'Native/export mismatch')
    require(model['manufacturing_ready'] is False,'Physical status changed')
    for item in model['inputs']:bound_hash(item['path'],item['sha256'])
    for name,part in model['parts'].items():bound_hash('mechanical/revI/'+name+'.stl',part['stl_sha256'])
    recipe=model['level_stack']
    bound_hash('tools/freecad/level_stack.py',recipe['generator_sha256'])
    require(recipe['parameters_mm']['FrameTop']==13.39 and recipe['parameters_mm']['BatteryBottom']==1.4,'Stack datums changed')
    install=read('validation/revI-level-install.json')
    require(install['output_sha256']==native and install['saved_reopened'] and install['key_geometry_preserved'],'Native installation incomplete')
    geometry=native_report('validation/revI-level-geometry.json',native)
    bound_hash('tools/freecad/check_level_stack.py',geometry['checker_sha256'])
    require(geometry['nominal_acceptance'] and not geometry['failures'],'Geometry acceptance failed')
    require(geometry['commercial_pin_hole_fit_qualified'] is False and geometry['physical_acceptance'] is False,'Unmeasured fit claim')
    with zipfile.ZipFile(ROOT/'mechanical/revI/Flan36.FCStd') as z:
        tree=ET.fromstring(z.read('Document.xml'))
        require('GuiDocument.xml' in z.namelist(),'Native appearance missing')
        require(not any(e.get('type','').endswith('Python') for e in tree.iter()),'Custom proxy dependency')
    mechanical=native_report('validation/revI-mechanical.json',native)
    bound_hash('tools/freecad/export_revI.py',mechanical['checker_sha256'])
    require(model['export_execution']['native_sha256']==native,'Export provenance mismatch')
    catalog=read('keycaps/catalog.json');styles=set(catalog['frame_styles'])
    require(len(styles)==10 and catalog['default_configuration']['cases']['left']['style']=='level','Choices/default changed')
    for side,h in mechanical['halves'].items():
        require(not h['collisions'] and set(h['case_variants'])=={'solid','rim','terrace','level'},'Case checks incomplete')
        require(set(h['frame_variants'])==styles and set(h['battery_variants'])=={'301230','adafruit-1570'},'Component variants incomplete')
        for c in h['case_variants'].values():require(c['closed_meshes'] and c['connected_solids'] and not c['component_collisions_mm3'],'Invalid case')
        require(abs(stl_bounds(f'mechanical/revI/{side}-case-level-plate.stl')[5]-13.39)<1e-4,'Level print height mismatch')
        for style,f in h['frame_variants'].items():
            require(f['closed_mesh'] and not f['component_collisions_mm3'] and f['usb_envelope_collision_mm3']<.001,'Frame collision')
            require(abs(stl_bounds(f'mechanical/revI/{side}-frame-{style}.stl')[5]-13.39)<1e-4,'Frame print height mismatch')
            for material in model['frameVariants'][side+'-'+style].get('material_parts',[]):
                bound_hash('mechanical/revI/'+material['stl'],material['stl_sha256'])
                bound_hash('mechanical/revI/'+material['step'],material['step_sha256'])
    service=native_report('validation/revI-service.json',native)
    bound_hash('tools/freecad/check_revI_service.py',service['checker_sha256'])
    for side,h in service['halves'].items():
        require(set(h['frame_lift_paths'])==styles and not any(h['frame_lift_paths'].values()),'Frame extraction blocked')
        require(not h['pcb_lift_after_plate_modules_removed'] and not h['nominal_3mm_driver_shaft_collisions'],'PCB/tool access blocked')
    component=native_report('validation/revI-components.json',native)
    require(component['switch_instances']==36 and component['model_identity_without_reflection'],'Component registration changed')
    pcb=native_report('validation/revI-bottom-reset-step.json',native)
    require(pcb['passed'],'Actual KiCad STEP registration failed')
    bound_hash('tools/freecad/export_pcb_components.py',pcb['exporter_sha256'])
    for side,h in pcb['halves'].items():
        for c in h['components'].values():
            require(c['native_placement_difference_mm3']<.001,'PCB model placement differs')
            bound_hash(c['step_path'],c['step_sha256'])
    viewer=sha('docs/index.html')
    built=viewer_report('validation/revI-viewer.json',viewer)
    for s in built['sources']:bound_hash(s['path'],s['sha256'])
    checks={}
    for name,path,checker in [
        ('ui','build/viewer-ui-check.json','viewer/check.cjs'),
        ('themes','build/themes-print/ui.json','viewer/customize-check.cjs'),
        ('hex','build/hex-check/result.json','viewer/hex-check.cjs'),
        ('printing','build/themes-print/print-validation.json','tools/check_print_kit.py'),
        ('leads','build/slim-flush/battery-viewer/result.json','viewer/battery-leads-check.cjs')]:
        checks[name]=viewer_report(path,viewer,checker)
    require(checks['ui']['glb_selected_vertices_exact'] and checks['ui']['glb_keycaps']==36,'GLB mismatch')
    require(checks['printing']['passed'] and len(checks['printing']['kits'])==10,'Print kit coverage incomplete')
    finishes=viewer_report('build/viewer-multicolor/geometry.json',viewer,'viewer/finishes-check.cjs')
    require(finishes['exact_native_material_volumes'] and len(finishes['checked'])==20,'Native frame materials differ in viewer')
    level=read('build/level-case/viewer-check/result.json')
    require(level['native_stl_bytes_match'] and level['print_3mf_generated'] and level['themes']==16,'Level print/color check incomplete')
    caps=read('validation/revI-keycap-registration.json')
    require(caps['native_and_viewer_caps_checked']==36,'Cap placement coverage incomplete')
    for path,digest in caps['sources'].items():bound_hash(path,digest)
    render=read('validation/revI-render.json')
    bound_hash('design/revI.json',render['model_sha256']);bound_hash('tools/render_revI.py',render['renderer_sha256'])
    require('level' in render['views'],'Level render missing')
    for name,v in render['views'].items():bound_hash('docs/images/revI-'+name+'.png',v['image_sha256'])
    for path in [ROOT/'README.md',*(ROOT/'docs').glob('*.md')]:
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if not target.startswith(('https:','http:','#','mailto:')):
                link=(path.parent/target.split('#')[0]).resolve()
                require(link.exists() or link==OUTPUT,'Broken documentation link: '+target)
    sha('tools/check_level_delivery.py')
    result={'schema':'flan36-level-delivery-1','digital_update_accepted':True,
        'native_source_sha256':native,'viewer_sha256':viewer,'frame_glass_shell_top_mm':13.39,
        'reduction_mm':1.41,'physical_acceptance':False,'manufacturing_qualified':False,
        'commercial_pin_hole_fit_qualified':False,'request_contract':'design/level-case-workflow.json',
        'coverage':{'cases':4,'frames':10,'battery_profiles':2,'cap_swept_poses_per_half':1008,'themes':16,'print_kits':10},
        'limits':['Commercial nice!view hole and actual connector engagement unmeasured.',
            'Printed fits, strength, battery insulation, wire flex, retention and operation unqualified.',
            'Boards remain unrouted. This is a digital prototype, not an absolute physical minimum.'],
        'inputs':[{'path':p,'sha256':h} for p,h in sorted(inputs.items())]}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: current native, PCB, Level case, ten frames, both cells, caps, viewer and print-kit delivery')

if __name__=='__main__':run()
