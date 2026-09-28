"""Historical additive-roof installer; its command is retired.

The current seven-style flush/stack recipe intentionally changes the original
frame geometry and therefore cannot satisfy this tool's append-only contract.
Use install_slim_flush.py. Snapshot helpers remain available to existing imports.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import math
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extra_frames import (OWNER, STYLES, build_for_half, digest, find_smooth,
                          fingerprint, load_spec, validate_variant)
from preserve_document_label import preserve_document_label


def snapshot(doc, names=None):
    """Record unchanged native geometry, transforms, links and visible material.

    Construction-group membership is deliberately omitted: the new owned group
    must be added there. Existing group members are checked separately.
    """
    result = {}
    for obj in doc.Objects:
        if names is not None and obj.Name not in names:
            continue
        item = dict(type=obj.TypeId, label=obj.Label,
                    expressions=[list(pair) for pair in getattr(obj, 'ExpressionEngine', [])])
        if hasattr(obj, 'Placement'):
            item['placement'] = list(obj.Placement.toMatrix().A)
        if hasattr(obj, 'Shape') and not obj.Shape.isNull():
            brep = obj.Shape.exportBrepToString()
            item['shape'] = hashlib.sha256(brep.encode('utf-8')).hexdigest()
            # Retain the immutable serialized before-shape, not an OCC object
            # that later booleans could update internally through shared caches.
            item['_shape_brep'] = brep
            item['shape_geometry'] = shape_signature(obj.Shape)
        if obj.TypeId == 'App::Link':
            item['linked_object'] = obj.LinkedObject.Name if obj.LinkedObject else None
        view = obj.ViewObject
        if view is not None:
            item['view'] = {}
            for attr in ('Visibility', 'ShapeColor', 'LineColor', 'DiffuseColor', 'Transparency', 'OverrideMaterial'):
                if hasattr(view, attr):
                    value = getattr(view, attr)
                    # Convert FreeCAD's vector/list-like material values to JSON.
                    if attr == 'DiffuseColor':
                        value = [list(c) for c in value]
                    elif attr in ('ShapeColor', 'LineColor'):
                        value = list(value)
                    item['view'][attr] = value
        result[obj.Name] = item
    return result



def shape_signature(shape):
    """Geometry metrics kept separately from the serialized BREP identity."""
    return {
        'shape_type': shape.ShapeType,
        'counts': {name: len(getattr(shape, name)) for name in
                   ('Solids', 'Shells', 'Faces', 'Wires', 'Edges', 'Vertexes')},
        'bounds_mm': [getattr(shape.BoundBox, name) for name in
                      ('XMin', 'YMin', 'ZMin', 'XMax', 'YMax', 'ZMax')],
        'volume_mm3': shape.Volume, 'area_mm2': shape.Area, 'length_mm': shape.Length,
        'vertices_mm': [[vertex.Point.x, vertex.Point.y, vertex.Point.z]
                        for vertex in shape.Vertexes],
    }


# Preserve identical geometric acceptance without compound-vs-compound explosion.
from shape_equivalence import shape_equivalence

def snapshot_changes(before, after, equivalent_hash_changes=None):
    """Keep exact nongeometric comparisons; prove geometry if BREP bytes differ."""
    changes = {}
    for name, expected in before.items():
        actual = after.get(name)
        if actual is None:
            changes[name] = {'missing_object': True}
            continue
        fields = {}
        if 'shape' in expected and (expected['shape'] != actual.get('shape') or
                expected.get('shape_geometry') != actual.get('shape_geometry')):
            try:
                sys.__stdout__.write('Comparing changed BREP '+name+'\n');sys.__stdout__.flush()
                equivalence = shape_equivalence(expected, actual)
                if equivalent_hash_changes is not None:
                    equivalent_hash_changes[name] = equivalence
            except Exception as error:
                fields['shape'] = {'before_brep_sha256': expected['shape'],
                                   'after_brep_sha256': actual.get('shape'),
                                   'equivalence_error': str(error)}
        for key in expected:
            if key in ('shape', '_shape_brep', 'shape_geometry') or expected[key] == actual.get(key):
                continue
            if key == 'view':
                fields['view'] = {attr: {'before': value, 'after': actual.get('view', {}).get(attr)}
                                  for attr, value in expected['view'].items()
                                  if value != actual.get('view', {}).get(attr)}
            else:
                fields[key] = {'before': expected[key], 'after': actual.get(key)}
        if fields:
            changes[name] = fields
    return changes


def restore_original_views(doc, before):
    """Restore original appearance only, after the final recompute.

    Native boolean view providers can hide their source/tools during recompute.
    Restoring Visibility before recompute is too early. Do not write any geometry,
    expression, link or placement here; their exact comparisons remain unchanged.
    """
    for name, original in before.items():
        view = doc.getObject(name).ViewObject
        if view is None:
            continue
        values = original.get('view', {})
        # ShapeColor may reset a DiffuseColor array, so restore per-face colors
        # afterward. Visibility goes last, after all material notifications.
        for attr in ('ShapeColor', 'LineColor', 'Transparency', 'OverrideMaterial', 'DiffuseColor', 'Visibility'):
            if attr not in values:
                continue
            expected = values[attr]
            current = getattr(view, attr)
            if attr == 'DiffuseColor':
                current = [list(c) for c in current]
            elif attr in ('ShapeColor', 'LineColor'):
                current = list(current)
            if current != expected:
                setattr(view, attr, [tuple(c) for c in expected] if attr == 'DiffuseColor'
                        else tuple(expected) if attr in ('ShapeColor', 'LineColor') else expected)


def install(doc, root, spec=None):
    """Transactional in-memory installation; the caller owns persistence.

    May run App-only for diagnostic validation, but save_verified requires GUI
    data. Existing extension objects update in place; all unowned objects survive.
    """
    import FreeCAD as A
    spec = spec or load_spec(root)
    doc.recompute()
    # Normalize only assembly display offsets while calculating local interfaces.
    offsets = {p: doc.getObject(p+'Half').Placement for p in ('L_', 'R_')}
    for prefix in offsets:
        doc.getObject(prefix+'Half').Placement = A.Placement()
    doc.recompute()
    unowned = {o.Name for o in doc.Objects if getattr(o, 'FrameExtensionOwner', '') != OWNER}
    before = snapshot(doc, unowned)
    members = {o.Name: {c.Name for c in o.Group} for o in doc.Objects
               if o.Name in unowned and 'Group' in o.PropertiesList}
    existing_count = len(doc.Objects)
    views = {o.Name: o.ViewObject.Visibility for o in doc.Objects if o.ViewObject is not None}
    report = dict(schema=OWNER, manufacturing_ready=False, status='prepared', halves={})
    doc.openTransaction('Install four additive frame variants')
    try:
        for side in ('left', 'right'):
            smooth = find_smooth(doc, side)
            variants = build_for_half(doc, side, smooth=smooth, spec=spec, validate=False)
            report['halves'][side] = {style: validate_variant(doc, side, smooth, obj, spec)
                                      for style, obj in variants.items()}
        # Recompute first: native booleans may hide their sources/tools there.
        # Restore exact original appearance afterward, then compare everything.
        doc.recompute()
        for name, visible in views.items():
            doc.getObject(name).ViewObject.Visibility = visible
        restore_original_views(doc, before)
        after = snapshot(doc, unowned)
        equivalent_hash_changes = {}
        changes = snapshot_changes(before, after, equivalent_hash_changes)
        report['construction_brep_hash_changes'] = equivalent_hash_changes
        if changes:
            raise ValueError(('Original geometry, placement, link or appearance changed', changes))
        for name, children in members.items():
            if not children.issubset({c.Name for c in doc.getObject(name).Group}):
                raise ValueError(('Existing group lost members', name))
        added = [o for o in doc.Objects if o.Name not in before]
        for obj in added:
            if getattr(obj, 'FrameExtensionOwner', '') != OWNER:
                raise ValueError(('Unowned added object', obj.Name))
            if obj.TypeId.endswith('Python'):
                raise ValueError(('Runtime Python proxy is prohibited', obj.Name))
        report.update(status='validated_in_memory', original_objects_preserved=len(unowned),
                      original_geometry_appearance_unchanged=True,
                      object_count_before=existing_count, object_count_after=len(doc.Objects),
                      extension_objects=len(added), styles=list(STYLES))
        doc.commitTransaction()
    except BaseException:
        doc.abortTransaction()
        raise
    finally:
        for prefix, placement in offsets.items():
            doc.getObject(prefix+'Half').Placement = placement
        doc.recompute()
        restore_original_views(doc, before)
    return report


def script_args():
    # run_macos.py uses runpy and leaves its lib/target positional arguments in
    # sys.argv; ordinary FreeCAD Python invocation has only script arguments.
    args = sys.argv[1:]
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        for i, arg in enumerate(args):
            if arg == str(Path(__file__).resolve()):
                return args[i+1:]
    return args


def main():
    raise SystemExit('Historical additive-roof installer retired. Use tools/freecad/install_slim_flush.py for the current slim, flush-material recipe. To reproduce the old append-only study, use its recorded historical commit.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--backup-dir', type=Path)
    parser.add_argument('--spec-root', type=Path, help='Optional root containing design/frame-extensions.json')
    args = parser.parse_args(script_args())
    source, output = args.source.resolve(), args.output.resolve()
    spec_root = args.spec_root.resolve() if args.spec_root else Path(__file__).resolve().parents[2]
    root = spec_root
    if source == output and args.backup_dir is None:
        raise ValueError('In-place replacement requires --backup-dir for a content-hashed recoverable original')
    if output.exists() and output != source:
        raise ValueError('Refusing to overwrite a different output; use a fresh path or make it the --source')
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        raise RuntimeError('Use run_macos.py with its default offscreen Qt platform; no visible GUI launch is allowed')
    import FreeCAD as A
    import FreeCADGui as G
    # App-only saves drop GUI state in some FreeCAD versions. Offscreen GUI is
    # mandatory for this CLI: it retains existing appearance and adds face colors.
    G.showMainWindow()
    G.getMainWindow().hide()
    if not A.GuiUp:
        raise RuntimeError('GUI support unavailable; refusing a save that could lose GuiDocument')
    source_hash = digest(source)
    spec = load_spec(spec_root)
    inputs = {str(source): source_hash,
              str(spec_root/'design/frame-extensions.json'): digest(spec_root/'design/frame-extensions.json'),
              str(Path(__file__).resolve()): digest(__file__),
              str(Path(__file__).with_name('preserve_document_label.py').resolve()): digest(Path(__file__).with_name('preserve_document_label.py')),
              str(Path(__file__).with_name('extra_frames.py').resolve()): digest(Path(__file__).with_name('extra_frames.py'))}
    backup = None
    if source == output:
        args.backup_dir.mkdir(parents=True, exist_ok=True)
        backup = args.backup_dir / ('Flan36-before-extra-' + source_hash[:16] + '.FCStd')
        if not backup.exists():
            shutil.copy2(source, backup)
        if digest(backup) != source_hash:
            raise ValueError('Backup integrity mismatch')
    doc = A.openDocument(str(source))
    original_document_label = doc.Label
    tmp = None
    try:
        report = install(doc, root, spec=spec)
        # Capture every original object after placement restoration for reopen.
        original_names = {o.Name for o in doc.Objects if getattr(o, 'FrameExtensionOwner', '') != OWNER}
        original = snapshot(doc, original_names)
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.flan36-extra-', suffix='.FCStd', dir=output.parent)
        os.close(fd)
        tmp = Path(name)
        doc.saveAs(str(tmp))
        A.closeDocument(doc.Name)
        doc = None
        # saveAs can substitute the temporary filename for the document label.
        # Restore only that XML value after close; retain all CAD and GUI bytes.
        with tempfile.TemporaryDirectory(prefix='.flan36-label-', dir=output.parent) as label_dir:
            labeled = Path(label_dir)/'Flan36.FCStd'
            report['document_label_preservation'] = preserve_document_label(tmp, labeled, original_document_label)
            os.replace(labeled, tmp)
        with zipfile.ZipFile(tmp) as saved:
            if 'GuiDocument.xml' not in saved.namelist():
                raise ValueError('Saved file lost GuiDocument')
        # Native-only reopen and recompute are part of acceptance before replace.
        reopened = A.openDocument(str(tmp))
        try:
            if reopened.Label != original_document_label:
                raise ValueError('Document label changed on save/reopen')
            reopened.recompute()
            equivalent_hash_changes = {}
            changes = snapshot_changes(original, snapshot(reopened, original_names), equivalent_hash_changes)
            report['reopen_brep_hash_changes'] = equivalent_hash_changes
            if changes:
                raise ValueError(('Original object appearance/geometry changed on save/reopen', changes))
            for side, prefix in [('left','L_'),('right','R_')]:
                half = reopened.getObject(prefix+'Half')
                placement = half.Placement
                half.Placement = A.Placement()
                reopened.recompute()
                smooth = find_smooth(reopened, side)
                for style in STYLES:
                    validate_variant(reopened, side, smooth,
                                     reopened.getObject(prefix+'ExtraFrame_'+style+'_Final'), spec)
                half.Placement = placement
            report['native_reopen_recompute_passed'] = True
            report['gui_document_preserved'] = True
        finally:
            A.closeDocument(reopened.Name)
        if digest(source) != source_hash:
            raise ValueError('Source changed concurrently; refusing to publish candidate')
        os.replace(tmp, output)
        tmp = None
        report.update(status='saved_and_reopened', inputs_sha256=inputs,
                      output=str(output), output_sha256=digest(output),
                      source_backup=str(backup) if backup else None,
                      source_preserved_as=str(backup if backup else source),
                      physical_fit='unqualified; digital geometry only')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print('PASS: four native variants per half; original objects preserved; saved/reopened; physical fit unqualified', flush=True)
    finally:
        if doc is not None:
            A.closeDocument(doc.Name)
        if tmp is not None and tmp.exists():
            tmp.unlink()


if __name__ == '__main__':
    main()
    # All validation, file publication, receipt writing and document cleanup
    # succeeded before this point. Avoid the known bundled-CAD teardown crash;
    # failures never reach this success-only process exit.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
