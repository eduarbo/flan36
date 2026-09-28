"""Native flush co-print frame materials; no runtime proxies or raised details.

The material bodies share assembly coordinates. Their disjoint interiors exactly
partition the undecorated frame. The union is retained for collision checks and
single-material export; MaterialParts preserves the printable color boundaries.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWNER = 'flan36-flush-frames-1'
ROLES = ('body', 'detail', 'accent', 'secondary')
STYLES = tuple(json.loads((ROOT/'design/frame-finishes.json').read_text())['styles'])
BOUNDS = ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')
EPS = 1e-5


def load_spec(root=ROOT):
    root = Path(root)
    spec = json.loads((root / 'design/frame-finishes.json').read_text())
    if tuple(spec['styles']) != STYLES or tuple(spec['roles']) != ROLES:
        raise ValueError('Unexpected flush frame styles or material roles')
    if spec['decoration_mode'] != 'flush-co-print' or not 0 < spec['inlay_depth_mm'] <= .4:
        raise ValueError('Invalid flush inlay depth')
    if spec['minimum_backing_mm'] < .8:
        raise ValueError('The shell backing must remain at least 0.8 mm')
    for style, theme in spec['styles'].items():
        if sorted(theme.get('priority', ['accent','secondary','detail'])) != sorted(ROLES[1:]):
            raise ValueError((style, 'invalid material priority'))
        ids = set()
        for item in theme['features']:
            if item['id'] in ids or not item['id'].isalnum():
                raise ValueError((style, 'invalid feature identity', item['id']))
            ids.add(item['id'])
            if item['role'] not in ROLES[1:]:
                raise ValueError((style, item['id'], 'invalid material role'))
    return spec


def prop(obj, name, kind, value):
    if name not in obj.PropertiesList:
        obj.addProperty(kind, name, 'Flan36')
    setattr(obj, name, value)


def rgb(color):
    return tuple(int(color[i:i+2], 16) / 255 for i in (1, 3, 5))


def find_smooth(doc, side):
    prefix = 'L_' if side == 'left' else 'R_'
    matches = [o for o in doc.Objects if o.Name.startswith(prefix)
               and o.TypeId != 'App::Link' and (getattr(o, 'FrameTemplate', False)
               or getattr(o, 'FrameStyle', '') == 'smooth')]
    if len(matches) != 1:
        raise ValueError((side, 'expected one undecorated Smooth frame', len(matches)))
    return matches[0]


class Recipe:
    def __init__(self, doc, side, smooth, spec):
        import FreeCAD as A
        self.A, self.doc, self.side, self.smooth, self.spec = A, doc, side, smooth, spec
        self.prefix = ('L_' if side == 'left' else 'R_') + 'FlushFrame_'
        history = doc.getObject(('L_' if side == 'left' else 'R_') + 'Construction')
        self.group = doc.getObject(self.prefix + 'Materials')
        if self.group is None:
            self.group = doc.addObject('App::DocumentObjectGroup', self.prefix + 'Materials')
            prop(self.group, 'FlushFrameOwner', 'App::PropertyString', OWNER)
        elif getattr(self.group, 'FlushFrameOwner', '') != OWNER:
            raise ValueError(('Unowned flush material group', self.group.Name))
        self.group.Label = 'Flush frame materials · co-print together'
        if history is not None:
            history.addObject(self.group)
        self.used = []

    def add(self, kind, name):
        name = self.prefix + name
        obj = self.doc.getObject(name)
        if obj is None:
            obj = self.doc.addObject(kind, name)
            prop(obj, 'FlushFrameOwner', 'App::PropertyString', OWNER)
        elif obj.TypeId != kind or getattr(obj, 'FlushFrameOwner', '') != OWNER:
            raise ValueError(('Refusing to replace unowned native object', name))
        self.group.addObject(obj)
        self.used.append(obj)
        return obj

    def point(self, p):
        x, y = p
        return self.A.Vector(x if self.side == 'left' else 160 - x, -y, 0)

    def depth(self, obj, zprop, lengthprop):
        prop(obj, 'InlayDepth', 'App::PropertyLength', self.spec['inlay_depth_mm'])
        obj.setExpression(zprop, 'Parameters.FrameTop - InlayDepth')
        obj.setExpression(lengthprop, 'InlayDepth')

    def polygon(self, name, points):
        import Part
        import Sketcher
        sketch = self.add('Sketcher::SketchObject', name + 'Sketch')
        for i in reversed(range(sketch.GeometryCount)):
            sketch.delGeometry(i)
        points = [self.point(p) for p in points]
        for a, b in zip(points, points[1:] + points[:1]):
            i = sketch.addGeometry(Part.LineSegment(a, b), False)
            sketch.addConstraint(Sketcher.Constraint('Block', i))
        obj = self.add('Part::Extrusion', name)
        obj.Base, obj.Dir, obj.Solid = sketch, self.A.Vector(0, 0, 1), True
        self.depth(obj, 'Placement.Base.z', 'LengthFwd')
        return obj

    def primitive(self, name, item):
        kind = item['kind']
        if kind == 'roundrect':
            import Part
            import Sketcher
            x0,y0,x1,y1=item['xy']; r=item['radius_mm']
            if not 0 < r <= min(x1-x0,y1-y0)/2:
                raise ValueError((name,'invalid corner radius'))
            # True circular corners, not polygon approximations or baked meshes.
            q=1-math.sqrt(.5)
            segments=[[[x0+r,y0],[x1-r,y0]],[[x1-r,y0],[x1-r*q,y0+r*q],[x1,y0+r]],
                [[x1,y0+r],[x1,y1-r]],[[x1,y1-r],[x1-r*q,y1-r*q],[x1-r,y1]],
                [[x1-r,y1],[x0+r,y1]],[[x0+r,y1],[x0+r*q,y1-r*q],[x0,y1-r]],
                [[x0,y1-r],[x0,y0+r]],[[x0,y0+r],[x0+r*q,y0+r*q],[x0+r,y0]]]
            sketch=self.add('Sketcher::SketchObject',name+'Sketch')
            for i in reversed(range(sketch.GeometryCount)):sketch.delGeometry(i)
            for segment in segments:
                pts=[self.point(p) for p in segment]
                if len(pts)==2 and (pts[1]-pts[0]).Length<EPS:continue
                geometry=Part.LineSegment(*pts) if len(pts)==2 else Part.Arc(*pts)
                index=sketch.addGeometry(geometry,False)
                sketch.addConstraint(Sketcher.Constraint('Block',index))
            obj=self.add('Part::Extrusion',name)
            obj.Base,obj.Dir,obj.Solid=sketch,self.A.Vector(0,0,1),True
            self.depth(obj,'Placement.Base.z','LengthFwd')
            return [obj]
        if kind == 'ring':
            if not 0 < item['width_mm'] < item['radius_mm']:
                raise ValueError((name,'invalid ring width'))
            outer=self.primitive(name+'Outer',dict(item,kind='disc'))[0]
            inner=self.primitive(name+'Inner',dict(item,kind='disc',radius_mm=item['radius_mm']-item['width_mm']))[0]
            return [self.cut(name,outer,inner)]
        if kind == 'box':
            x0, y0, x1, y1 = item['xy']
            if x1 <= x0 or y1 <= y0:
                raise ValueError((name, 'invalid rectangle'))
            obj = self.add('Part::Box', name)
            obj.Length, obj.Width = x1-x0, y1-y0
            obj.Placement.Base = self.point((x0 if self.side == 'left' else x1, y1))
            self.depth(obj, 'Placement.Base.z', 'Height')
            return [obj]
        if kind == 'disc':
            obj = self.add('Part::Cylinder', name)
            obj.Radius, obj.Placement.Base = item['radius_mm'], self.point(item['xy'])
            self.depth(obj, 'Placement.Base.z', 'Height')
            return [obj]
        if kind == 'polygon':
            return [self.polygon(name, item['points'])]
        if kind == 'stroke':
            nodes, radius = [], item['width_mm']/2
            for i, (a, b) in enumerate(zip(item['points'], item['points'][1:])):
                dx, dy = b[0]-a[0], b[1]-a[1]
                length = math.hypot(dx, dy)
                if length <= EPS:
                    raise ValueError((name, 'zero length stroke'))
                nx, ny = -dy/length*radius, dx/length*radius
                nodes.append(self.polygon(name+'Segment'+str(i), [
                    [a[0]+nx, a[1]+ny], [b[0]+nx, b[1]+ny],
                    [b[0]-nx, b[1]-ny], [a[0]-nx, a[1]-ny]]))
            for i, point in enumerate(item['points']):
                nodes.extend(self.primitive(name+'Joint'+str(i),
                    dict(kind='disc', xy=point, radius_mm=radius)))
            return nodes
        raise ValueError((name, 'unsupported feature', kind))

    def combine(self, name, nodes):
        if len(nodes) == 1:
            obj = self.add('Part::Compound', name)
            obj.Links = nodes
        else:
            obj = self.add('Part::MultiFuse', name)
            obj.Shapes, obj.Refine = nodes, True
        return obj

    def common(self, name, a, b):
        obj = self.add('Part::Common', name)
        obj.Base, obj.Tool, obj.Refine = a, b, True
        return obj

    def cut(self, name, a, b):
        obj = self.add('Part::Cut', name)
        obj.Base, obj.Tool, obj.Refine = a, b, True
        return obj

    def build(self, style):
        theme = self.spec['styles'][style]
        raw = {role: [] for role in ROLES[1:]}
        for item in theme['features']:
            raw[item['role']].extend(self.primitive(style+'_'+item['id'], item))
        # The translated source limits every inlay to material with backing below.
        support = self.add('Part::Compound', style+'_BackingMask')
        support.Links = [self.smooth]
        prop(support, 'MinimumBacking', 'App::PropertyLength', self.spec['minimum_backing_mm'])
        support.setExpression('Placement.Base.z', 'MinimumBacking')
        mask = self.common(style+'_SupportedRoof', self.smooth, support)
        material = []
        # Explicit deterministic priority: accent over secondary over detail.
        # Subtraction gives disjoint material interiors even at crossing motifs.
        occupied = None
        for role in theme.get('priority', ('accent', 'secondary', 'detail')):
            if not raw[role]:
                continue
            fused = self.combine(style+'_'+role+'_Raw', raw[role])
            clipped = self.common(style+'_'+role+'_Clipped', fused, mask)
            obj = self.cut(style+'_'+role+'_Material', clipped, occupied) if occupied else clipped
            prop(obj, 'ColorRole', 'App::PropertyString', role)
            obj.Label = theme.get('label', style.title())+' · '+role+' · flush inlay'
            material.append(obj)
            occupied = self.combine(style+'_'+role+'_Occupied', material)
        body = self.cut(style+'_body_Material', self.smooth, occupied)
        prop(body, 'ColorRole', 'App::PropertyString', 'body')
        body.Label = theme.get('label', style.title())+' · recessed shell'
        materials = [body] + sorted(material, key=lambda o: ROLES.index(o.ColorRole))
        final = self.add('Part::MultiFuse', style+'_Final')
        final.Shapes, final.Refine = materials, False
        final.Label = 'Frame · '+theme.get('label', style.title())+' · flush co-print'
        prop(final, 'FrameStyle', 'App::PropertyString', style)
        prop(final, 'MaterialParts', 'App::PropertyLinkList', materials)
        prop(final, 'SmoothSource', 'App::PropertyLink', self.smooth)
        prop(final, 'PrototypePrintable', 'App::PropertyBool', True)
        prop(final, 'InlayDepth', 'App::PropertyLength', self.spec['inlay_depth_mm'])
        prop(final, 'ModelStatus', 'App::PropertyString', 'Flush co-print prototype; physical fit untested')
        prop(final, 'MaterialSpecSHA256', 'App::PropertyString',
             hashlib.sha256(json.dumps(theme, sort_keys=True).encode()).hexdigest())
        return final


def face_roles(obj):
    """Classify exposed native faces by owning material, without height rules."""
    parts = list(obj.MaterialParts)
    shape_stamp = hashlib.sha256(obj.Shape.exportBrepToString().encode()).hexdigest()
    material_stamp = hashlib.sha256(''.join(part.ColorRole+':'+
        hashlib.sha256(part.Shape.exportBrepToString().encode()).hexdigest() for part in parts).encode()).hexdigest()
    if (getattr(obj, 'FrameFaceRolesShapeSHA256', '') == shape_stamp and
            getattr(obj, 'FrameFaceRolesMaterialSHA256', '') == material_stamp):
        cached = json.loads(obj.FrameFaceRoles)
        if len(cached) == len(obj.Shape.Faces) and all(role in ROLES for role in cached):
            return cached

    def overlaps(a, b):
        # Non-strict overlap: planar/coplanar faces can have a zero-length axis.
        return all(min(getattr(a, axis+'Max'), getattr(b, axis+'Max'))+EPS >=
                   max(getattr(a, axis+'Min'), getattr(b, axis+'Min')) for axis in 'XYZ')

    material_faces = [(part.ColorRole, part.Shape, part.Shape.BoundBox,
                       [(face, face.BoundBox) for face in part.Shape.Faces]) for part in parts]
    result = []
    for face in obj.Shape.Faces:
        candidates = [(role, shape, faces) for role, shape, bounds, faces in material_faces
                      if overlaps(face.BoundBox, bounds)]
        identical = [role for role, _, faces in candidates
                     if any(overlaps(face.BoundBox, bounds) and face.isSame(other)
                            for other, bounds in faces)]
        if len(set(identical)) == 1:
            result.append(identical[0])
            continue
        # Exact intersection fallback for faces split by the Boolean union.
        # No centroid approximation: curved/trimmed faces retain correct roles.
        areas = [(face.common(shape).Area, role) for role, shape, _ in candidates]
        area, role = max(areas)
        if abs(area-face.Area) > max(EPS, face.Area*1e-5):
            raise ValueError((obj.Name, 'union face crosses a material boundary', face.Area, areas))
        result.append(role)
    prop(obj, 'FrameFaceRoles', 'App::PropertyString', json.dumps(result))
    prop(obj, 'FrameFaceRolesShapeSHA256', 'App::PropertyString', shape_stamp)
    prop(obj, 'FrameFaceRolesMaterialSHA256', 'App::PropertyString', material_stamp)
    return result


def validate_variant(doc, side, smooth, obj, spec=None, output_dir=None):
    import FreeCAD as A
    import MeshPart
    import Part
    spec = spec or load_spec()
    base, whole = smooth.Shape, obj.Shape
    roof = float(doc.Parameters.FrameTop.Value)
    if not base.isValid() or len(base.Solids) != 1 or not whole.isValid() or len(whole.Solids) != 1:
        raise ValueError((obj.Name, 'invalid/disconnected frame union'))
    removed, added = base.cut(whole).Volume, whole.cut(base).Volume
    if max(removed, added) > EPS:
        raise ValueError((obj.Name, 'flush union changed undecorated envelope', removed, added))
    if whole.BoundBox.ZMax > roof+EPS:
        raise ValueError((obj.Name, 'raised decoration remains'))
    material_parts, pairs = [], {}
    parts = list(obj.MaterialParts)
    target = Path(output_dir) if output_dir is not None else None
    if target:
        target.mkdir(parents=True, exist_ok=True)
    for i, part in enumerate(parts):
        shape = part.Shape
        if shape.isNull() or not shape.isValid() or not shape.Solids or shape.Volume <= EPS:
            raise ValueError((part.Name, 'empty/invalid material body'))
        if part.ColorRole == 'body' and len(shape.Solids) != 1:
            raise ValueError((part.Name, 'recesses disconnected the structural shell'))
        for other in parts[i+1:]:
            volume = shape.common(other.Shape).Volume
            pairs[part.ColorRole+'/'+other.ColorRole] = round(volume, 9)
            if volume > EPS:
                raise ValueError((obj.Name, 'overlapping material interiors', part.ColorRole, other.ColorRole, volume))
        backing_missing = 0.
        if part.ColorRole != 'body':
            if shape.BoundBox.ZMin < roof-spec['inlay_depth_mm']-EPS or shape.BoundBox.ZMax > roof+EPS:
                raise ValueError((part.Name, 'inlay outside roof band'))
            bottoms = [f for f in shape.Faces if abs(f.BoundBox.ZMin-(roof-spec['inlay_depth_mm'])) < EPS
                       and abs(f.BoundBox.ZMax-f.BoundBox.ZMin) < EPS]
            probes = [f.extrude(A.Vector(0, 0, -spec['minimum_backing_mm'])) for f in bottoms]
            if not probes:
                raise ValueError((part.Name, 'no planar inlay floor'))
            backing_missing = Part.makeCompound(probes).cut(base).Volume
            if backing_missing > EPS:
                raise ValueError((part.Name, 'insufficient backing below inlay', backing_missing))
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.03, AngularDeflection=.12, Relative=False)
        if not mesh.isSolid():
            raise ValueError((part.Name, 'open material mesh'))
        name = side+'-frame-'+obj.FrameStyle+'-'+part.ColorRole
        entry = dict(role=part.ColorRole, object=part.Name, stl=name+'.stl', step=name+'.step',
                     volume_mm3=shape.Volume, connected_solids=len(shape.Solids), closed_mesh=True,
                     bounds_mm=[getattr(shape.BoundBox, k) for k in BOUNDS],
                     backing_missing_volume_mm3=backing_missing)
        if target:
            mesh.write(str(target/entry['stl']))
            shape.exportStep(str(target/entry['step']))
            entry['stl_sha256'] = hashlib.sha256((target/entry['stl']).read_bytes()).hexdigest()
            entry['step_sha256'] = hashlib.sha256((target/entry['step']).read_bytes()).hexdigest()
        material_parts.append(entry)
    roles = face_roles(obj)
    prop(obj, 'FrameFaceRoles', 'App::PropertyString', json.dumps(roles))
    return dict(object=obj.Name, source_object=smooth.Name, style=obj.FrameStyle,
                material_parts=material_parts, disjoint_interiors=True, pair_intersections_mm3=pairs,
                union_removed_volume_mm3=removed, union_added_volume_mm3=added,
                connected_solids=1, bounds_mm=[getattr(whole.BoundBox, k) for k in BOUNDS],
                roof_mm=roof, max_roof_relief_mm=whole.BoundBox.ZMax-roof,
                inlay_depth_mm=spec['inlay_depth_mm'], minimum_backing_mm=spec['minimum_backing_mm'],
                face_roles=roles, manufacturing_ready=False)


def build_styles(doc, side, smooth=None, styles=STYLES, spec=None, validate=True, output_dir=None):
    import sys
    spec = spec or load_spec()
    smooth = smooth or find_smooth(doc, side)
    recipe = Recipe(doc, side, smooth, spec)
    prior = {style: [o for o in doc.Objects if o.Name.startswith(('L_' if side == 'left' else 'R_'))
                    and o.TypeId != 'App::Link' and getattr(o, 'FrameStyle', '') == style] for style in styles}
    objects, reports = {}, {}
    for style in styles:
        sys.__stdout__.write('Flush material geometry: '+side+' / '+style+'\n')
        sys.__stdout__.flush()
        obj = recipe.build(style)
        doc.recompute()
        for old in prior[style]:
            if old.Name == obj.Name:
                continue
            for link in list(doc.Objects):
                if link.TypeId == 'App::Link' and link.LinkedObject is not None and link.LinkedObject.Name == old.Name:
                    link.setLink(obj)
            prop(old, 'FormerFrameStyle', 'App::PropertyString', style)
            old.removeProperty('FrameStyle')
            if old.ViewObject is not None:
                old.ViewObject.Visibility = False
        doc.recompute()
        if validate:
            reports[style] = validate_variant(doc, side, smooth, obj, spec, output_dir)
            sys.__stdout__.write('Flush material validation passed: '+side+' / '+style+'\n')
            sys.__stdout__.flush()
        colors = spec['styles'][style]['colors']
        for part in obj.MaterialParts:
            if part.ViewObject is not None:
                part.ViewObject.ShapeColor = rgb(colors[part.ColorRole])
        if obj.ViewObject is not None:
            obj.ViewObject.ShapeColor = rgb(colors['body'])
            obj.ViewObject.LineColor = (.13, .18, .17)
            obj.ViewObject.DiffuseColor = [rgb(colors[r]) for r in face_roles(obj)]
        objects[style] = obj
    for obj in recipe.used:
        if obj.ViewObject is not None:
            obj.ViewObject.Visibility = False
    if recipe.group.ViewObject is not None:
        recipe.group.ViewObject.Visibility = False
    return objects, reports


def apply(doc, output_dir=None):
    """Apply the current collection after stack edits; does not save the document."""
    import FreeCAD as A
    spec = load_spec()
    if float(doc.Parameters.FrameRoof.Value)+EPS < spec['inlay_depth_mm']+spec['minimum_backing_mm']:
        raise ValueError('The requested roof is too thin for these recessed materials')
    result = dict(schema=OWNER, frames={}, inlay_depth_mm=spec['inlay_depth_mm'],
                  minimum_backing_mm=spec['minimum_backing_mm'], physical_acceptance=False)
    for side, prefix in [('left', 'L_'), ('right', 'R_')]:
        assembly = doc.getObject(prefix+'Half')
        old = assembly.Placement
        try:
            assembly.Placement = A.Placement()
            doc.recompute()
            _, reports = build_styles(doc, side, spec=spec, output_dir=output_dir)
            result['frames'].update({side+'-'+style: report for style, report in reports.items()})
        finally:
            assembly.Placement = old
            doc.recompute()
    return result


def main():
    """Headless isolated-copy validation. Never overwrite the source FCStd."""
    import argparse
    import os
    import sys
    import FreeCAD as A
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT/'mechanical/revI/Flan36.FCStd')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--roof', type=float, default=14.8)
    parser.add_argument('--display-bottom', type=float, default=12.4)
    argv = sys.argv[1:]
    # run_macos passes its library and target paths before the script arguments.
    while argv and not argv[0].startswith('--'):
        argv.pop(0)
    args = parser.parse_args(argv)
    if A.GuiUp or A.listDocuments():
        raise RuntimeError('Use a new headless process for isolated validation')
    if args.output.exists():
        raise RuntimeError('Choose a new output directory')
    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    args.output.mkdir(parents=True)
    doc = A.openDocument(str(args.source))
    doc.Parameters.set(doc.Parameters.getCellFromAlias('FrameTop'), str(args.roof)+' mm')
    doc.Parameters.set(doc.Parameters.getCellFromAlias('DisplayBottom'), str(args.display_bottom)+' mm')
    doc.recompute()
    report = apply(doc, args.output/'parts')
    names = set(o.Name for o in doc.Objects)
    second = apply(doc)
    if names != set(o.Name for o in doc.Objects):
        raise ValueError('Applying the recipe twice creates extra objects')
    for key, first in report['frames'].items():
        if abs(sum(p['volume_mm3'] for p in first['material_parts'])-
               sum(p['volume_mm3'] for p in second['frames'][key]['material_parts'])) > EPS:
            raise ValueError((key, 'idempotence volume drift'))
    output = args.output/'Flan36-flush-study.FCStd'
    doc.saveAs(str(output))
    A.closeDocument(doc.Name)
    doc = A.openDocument(str(output))
    doc.recompute()
    reopened = {}
    for side, prefix in [('left', 'L_'), ('right', 'R_')]:
        assembly = doc.getObject(prefix+'Half'); old = assembly.Placement
        assembly.Placement = A.Placement(); doc.recompute()
        for style in STYLES:
            obj = doc.getObject(prefix+'FlushFrame_'+style+'_Final')
            reopened[side+'-'+style] = validate_variant(doc, side, find_smooth(doc, side), obj)
        assembly.Placement = old; doc.recompute()
    report.update(source_sha256=source_hash, saved_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  idempotence_passed=True, saved_reopened_recomputed=True, reopened_frames=len(reopened),
                  source_unchanged=hashlib.sha256(args.source.read_bytes()).hexdigest()==source_hash)
    if not report['source_unchanged']:
        raise ValueError('Source FCStd unexpectedly changed')
    (args.output/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    sys.__stdout__.write(json.dumps({k:v for k,v in report.items() if k!='frames'}, indent=2)+'\n')
    sys.__stdout__.flush()
    A.closeDocument(doc.Name)
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        os._exit(0)


if __name__ == '__main__':
    main()
