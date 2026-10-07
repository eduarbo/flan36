"""Broaden the reference screw-head sweep to every enabled cap/key/rotation.
Read-only inputs; writes audit evidence under ignored build/.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import MultiPoint, Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from keycap_config import check

c = json.loads((ROOT / 'keycaps/catalog.json').read_text())
mounts = json.loads((ROOT / 'design/revI-mounts.json').read_text())['left']
minimum = float('inf')
count = 0
limiting = None
contacts = []
for variant in c['variants']:
    if not variant['qualified_reference_positions']:
        continue
    raw = (ROOT / variant['path']).read_bytes()
    n = struct.unpack_from('<I', raw, 80)[0]
    triangles = np.ndarray((n,), dtype=np.dtype([('n', '<f4', (3,)), ('v', '<f4', (3, 3)), ('a', '<u2')]), buffer=raw, offset=84)['v']
    hulls = {}
    for mount in mounts:
        zmax = mount['seat_z'] + mount['head_height'] + c['study_travel_mm'] - variant['seating_z_mm']
        if zmax not in hulls:
            points = triangles[triangles[:, :, 2] <= zmax][:, :2]
            crossings = []
            for i in range(3):
                a, b = triangles[:, i, :], triangles[:, (i+1) % 3, :]
                mask = (a[:, 2] < zmax) != (b[:, 2] < zmax)
                aa, bb = a[mask], b[mask]
                if len(aa):
                    crossings.append((aa + (bb-aa) * ((zmax-aa[:, 2])/(bb[:, 2]-aa[:, 2]))[:, None])[:, :2])
            if crossings:
                points = np.concatenate([points, *crossings])
            hulls[zmax] = MultiPoint(points).convex_hull if len(points) else None
        hull = hulls[zmax]
        if hull is None:
            continue
        for side, keys in c['layout'].items():
            for key in keys:
                for turn in variant['rotations_deg']:
                    shape = translate(rotate(hull, -key['angle']-turn, origin=(0, 0)), xoff=key['x'], yoff=key['y'])
                    x, y = mount['xy']
                    if side == 'right':
                        x = 160-x
                    gap = shape.distance(Point(x, y)) - mount['head_diameter']/2
                    pose = {'variant': variant['id'], 'side': side, 'key': key['ref'], 'rotation_deg': turn, 'mount': mount['id']}
                    if gap < minimum:
                        minimum, limiting = gap, pose
                    if gap <= 0:
                        config = json.loads(json.dumps(c['default_configuration']))
                        config['keycaps'][side][key['ref']].update(variant=variant['id'], rotation_deg=turn)
                        errors, _ = check(config, c)
                        contacts.append({**pose, 'conservative_gap_mm': gap, 'default_neighbors_errors': errors})
                    count += 1
report = {'scope': 'Every enabled variant at every key and allowed rotation, including poses rejected by cap/frame or neighbors; conservative full 3.5 mm travel vs nominal screw heads.',
          'pairs': count, 'minimum_gap_mm': minimum, 'limiting': limiting, 'conservative_contacts': contacts,
          'physical_acceptance': False}
out = ROOT / 'build/audit-20261007'
out.mkdir(parents=True, exist_ok=True)
(out / 'keycap-sweeps.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k: v for k, v in report.items() if k != 'conservative_contacts'}, indent=2))
print('Conservative contacts:', len(contacts))


def top_at_center(path):
    raw = (ROOT / path).read_bytes()
    n = struct.unpack_from('<I', raw, 80)[0]
    t = np.ndarray((n,), dtype=np.dtype([('n', '<f4', (3,)), ('v', '<f4', (3, 3)), ('a', '<u2')]), buffer=raw, offset=84)['v'].astype(float)
    a, u, v = t[:, 0], t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]
    det = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
    mask = abs(det) > 1e-10
    a, u, v, det = [x[mask] for x in [a, u, v, det]]
    s = (-a[:, 0]*v[:, 1]+a[:, 1]*v[:, 0])/det
    q = (-u[:, 0]*a[:, 1]+u[:, 1]*a[:, 0])/det
    z = a[:, 2]+s*u[:, 2]+q*v[:, 2]
    return max(z[(s >= -1e-8) & (q >= -1e-8) & (s+q <= 1+1e-8)])


variants = {v['id']: v for v in c['variants']}
homing = {'default_K14': {side: c['default_configuration']['keycaps'][side]['K14'] for side in ['left', 'right']}, 'profiles': {}}
for profile in ['normal', 'saddle']:
    normal = variants['choc_stem_choc_size_'+profile]
    bump = variants['choc_stem_choc_size_'+profile+'_homing']
    ordinary_top, bump_top = top_at_center(normal['path']), top_at_center(bump['path'])
    homing['profiles'][profile] = {'center_normal_top_mm': ordinary_top, 'center_homing_top_mm': bump_top, 'relief_mm': bump_top-ordinary_top}
(out / 'homing.json').write_text(json.dumps(homing, indent=2)+'\n')
