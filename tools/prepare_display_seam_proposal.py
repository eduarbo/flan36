#!/usr/bin/env python3
"""Freeze the seam-only correction separately from approved R4 history.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy,hashlib,json,os
from pathlib import Path
from prepare_frame_redesign_r5 import rect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'design/proposals/display-seam-r1'
def prepare():
    previous=ROOT/'design/proposals/frame-master-r4/master.json'
    master=json.loads(previous.read_text())
    master.update(revision='R4-seam-1',status='NOMINAL_CORRECTION_CANDIDATE',
        previous_master_sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),
        source_sha256={'mechanical/revI/Flan36.FCStd':hashlib.sha256(Path(os.environ.get('FLAN36_REVIEW_SOURCE',ROOT/'mechanical/revI/Flan36.FCStd')).read_bytes()).hexdigest()},
        aperture_commands=rect(5.05,7.55,13.9,30.5),aperture_bounds_mm=[5.05,7.55,18.95,38.05],
        correction={'glass_clearance_mm':.1,'pcb_projection_overlap_mm':.05,'display_translation_mm':[0,0,0],
          'height_change_mm':0,'oblique_occlusion_guaranteed':False,
          'scope':'Glass-centered aperture and exact 2.40 mm screen bezel; all other approved paths and HEX colors unchanged.'})
    master['bezel'].update(outer_bounds_mm=[2.65,5.15,21.35,40.45],exterior_side_margins_mm=[2.65,2.65])
    # The earlier centering is already installed. Do not expose its old proposed
    # translation as an instruction in the current correction contract.
    history=master.pop('alignment_change')
    history['status']='HISTORICAL_R4_CHANGE_ALREADY_APPLIED'
    master['historical_r4_alignment']=history
    master['native_baseline']={'aperture_bounds_mm':[4.75,7.35,19.25,38.45],'frame_face_z_mm':13.59}
    master['original_request']='Correct exposed display side bands without a second display translation or height increase.'
    master['styles']={k:v for k,v in master['styles'].items() if k in ['talavera','gameboy','snes','phone','ipod']}
    for s in master['styles'].values():
        next(f for f in s['features'] if f['id']=='ScreenField')['commands']=rect(2.65,5.15,18.7,35.3,2.4)
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'master.json').write_text(json.dumps(master,indent=2)+'\n')
    print('Prepared seam candidate with 0.10 mm glass clearance, no stack change')
if __name__=='__main__':prepare()
