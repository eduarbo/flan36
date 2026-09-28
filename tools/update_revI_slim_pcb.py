#!/usr/bin/env python3
"""Register PH2 side-entry connector, reset access and battery opening.
Only the enumerated unrouted study interfaces change; net UUIDs are preserved.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json,re,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
J1={'left':[125.45,57.2,270],'right':[34.55,59.2,90]}
RESET={'left':[119.0,59.5],'right':[41.0,59.5]}
NAME='PiantorSlim:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal'

def children(text):
 depth=0;quoted=False;escaped=False;start=None
 for i,c in enumerate(text):
  if quoted:
   if escaped:escaped=False
   elif c=='\\':escaped=True
   elif c=='"':quoted=False
  elif c=='"':quoted=True
  elif c=='(':
   depth+=1
   if depth==2:start=i
  elif c==')':
   if depth==2:yield start,i+1,text[start:i+1]
   depth-=1

def update_text(text,side):
 assert not any(re.match(r'\((segment|via)\s',s) for _,_,s in children(text)),'Routed board: refusing mechanical replacement'
 old=text
 for a,b,s in reversed(list(children(text))):
  if s.startswith('(footprint '):
   ref=re.search(r'\(property\s+"Reference"\s+"([^"]+)"',s)[1]
   if ref not in ['J1','SW2']:continue
   at=re.search(r'\(at\s+([\d.eE+-]+)\s+([\d.eE+-]+)([^)]*)\)',s)
   if ref=='J1':
    x,y,angle=J1[side];replacement=f'(at {x:.6f} {y:.6f} {angle})'
   else:
    x,y=RESET[side];replacement=f'(at {x:.6f} {y:.6f}{at[3]})'
   s=s[:at.start()]+replacement+s[at.end():]
   if ref=='SW2' and '(layer "F.Cu")' in s:
    # Native bottom flip about X: localY reverses; component pad nets/UUIDs remain.
    for pa,pb,item in reversed(list(children(s))):
     if not item.startswith(('(property ','(fp_','(pad ')):continue
     item=re.sub(r'\((at|start|end|center|mid) ([\d.eE+-]+) ([\d.eE+-]+)([^)]*)\)',lambda m:f'({m[1]} {m[2]} {-float(m[3]):g}{m[4]})',item)
     if item.startswith(('(property ','(fp_text ')):
      for ea,eb,effects in reversed(list(children(item))):
       if effects.startswith('(effects') and 'justify' not in effects:
        k=effects.rfind(')');effects=effects[:k]+'(justify mirror)'+effects[k:];item=item[:ea]+effects+item[eb:]
     s=s[:pa]+item+s[pb:]
    s=s.replace('"F.Cu"','"B.Cu"').replace('"F.Mask"','"B.Mask"').replace('"F.Paste"','"B.Paste"').replace('"F.Fab"','"B.Fab"').replace('"F.SilkS"','"B.SilkS"').replace('"F.CrtYd"','"B.CrtYd"')
   if ref=='J1':
    s=re.sub(r'^\(footprint "[^"]+"',f'(footprint "{NAME}"',s)
    s=s.replace('"BATTERY_PIGTAIL"','"JST_PH_S2B-PH-K-S"')
    for pa,pb,pad in reversed(list(children(s))):
     if not pad.startswith('(pad '):continue
     number=re.match(r'\(pad "([12])"',pad)[1];at=re.search(r'\(at[^)]*\)',pad)
     pad=pad[:at.start()]+f'(at {0 if number=="1" else 2} 0 {J1[side][2]})'+pad[at.end():]
     pad=re.sub(r'\(size[^)]*\)','(size 1.2 1.75)',pad);pad=re.sub(r'\(drill[^)]*\)','(drill 0.75)',pad)
     pad=pad.replace('thru_hole circle','thru_hole oval')
     s=s[:pa]+pad+s[pb:]
    if '(fp_rect' not in s:
     rect='\n\t\t(fp_rect (start -1.95 -1.35) (end 3.95 6.25) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))\n\t\t(fp_rect (start -2.45 -1.85) (end 4.45 6.75) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))\n'
     i=s.rfind(')');s=s[:i]+rect+s[i:]
   text=text[:a]+s+text[b:]
  elif s.startswith('(gr_line') and 'Edge.Cuts' in s:
   coords=re.findall(r'\((?:start|end) ([\d.eE+-]+) ([\d.eE+-]+)\)',s)
   xs=[116.55,129.05,117.65,119.85] if side=='left' else [43.45,30.95,42.35,40.15]
   if len(coords)==2 and all(any(abs(float(x)-xx)<1e-6 for xx in xs) for x,y in coords) and all(float(y) in [14.,12.,13.2,47.6,49.4] for x,y in coords):text=text[:a]+text[b:]
 aperture=[[116.55,13.2],[129.05,13.2],[129.05,47.6],[119.85,47.6],[119.85,49.4],[117.65,49.4],[117.65,47.6],[116.55,47.6]]
 if side=='right':aperture=[[160-x,y] for x,y in aperture]
 edges=[]
 for a,b in zip(aperture,aperture[1:]+aperture[:1]):edges.append(f'(gr_line (start {a[0]:.6f} {a[1]:.6f}) (end {b[0]:.6f} {b[1]:.6f}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))')
 i=text.rfind(')');text=text[:i]+'\n'+'\n'.join(edges)+'\n'+text[i:]

 text='\n'.join(line.rstrip() for line in text.splitlines())+'\n'
 return text,{'before_sha256':hashlib.sha256(old.encode()).hexdigest(),'after_sha256':hashlib.sha256(text.encode()).hexdigest(),'j1_at':J1[side],'reset_at':RESET[side],'reset_side':'B.Cu','reset_local_y_mirrored':True,'battery_aperture_y':[13.2,47.6],'rear_lead_notch_xy':[[117.65 if side=='left' else 40.15,47.6],[119.85 if side=='left' else 42.35,49.4]],'j1_pad_pitch_mm':2,'j1_drill_mm':.75,'j1_pad_size_mm':[1.2,1.75],'nets_preserved':['BAT_PLUS','GND'],'routing_changes':0}

def apply(folder):
 report={'scope':'Nominal slim electronics interfaces, unrouted board. No manufacturing acceptance.','halves':{}}
 for side in ['left','right']:
  path=folder/f'flan36-{side}.kicad_pcb';text,result=update_text(path.read_text(),side);path.write_text(text);report['halves'][side]=result
  sch=folder/f'flan36-{side}.kicad_sch'
  if sch.exists():
   schematic=sch.read_text().replace('PiantorSlim:Battery_pigtail_2.54',NAME)
   for a,b,symbol in reversed(list(children(schematic))):
    if symbol.startswith('(symbol ') and '(property "Reference" "J1"' in symbol:
     symbol=re.sub(r'(\(property "Value" )"[^"]+"',r'\1"JST_PH_S2B-PH-K-S"',symbol)
     schematic=schematic[:a]+symbol+schematic[b:]
   sch.write_text(schematic)
 library=folder/'libraries/PiantorSlim.pretty';library.mkdir(parents=True,exist_ok=True)
 (library/'JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal.kicad_mod').write_text('''(footprint "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"
 (version 20241229) (generator "flan36") (layer "F.Cu")
 (descr "Original nominal footprint from JST PH catalog dimensions; side-entry S2B-PH-K-S. Verify purchased part and polarity.")
 (property "Reference" "J1" (at 1 -2.5) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
 (property "Value" "JST_PH_S2B-PH-K-S" (at 1 7.5) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
 (fp_rect (start -1.95 -1.35) (end 3.95 6.25) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))
 (fp_rect (start -2.45 -1.85) (end 4.45 6.75) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
 (pad "1" thru_hole oval (at 0 0) (size 1.2 1.75) (drill 0.75) (layers "*.Cu" "*.Mask"))
 (pad "2" thru_hole oval (at 2 0) (size 1.2 1.75) (drill 0.75) (layers "*.Cu" "*.Mask"))
)
''')
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=ROOT/'hardware/revI');p.add_argument('--report',type=Path,default=ROOT/'validation/revI-slim-pcb.json');args=p.parse_args()
 result=apply(args.folder);args.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
