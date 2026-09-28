"""Apply the slim stack and flush frames to an isolated native candidate.

python3 tools/freecad/run_macos.py tools/freecad/install_slim_flush.py \
  --source mechanical/revI/Flan36.FCStd --output build/slim-flush/candidate/Flan36.FCStd

Preserves the source. The caller reviews the candidate and explicitly adopts its
exports. No runtime Python proxies are stored in the native file.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def args():
    values = sys.argv[1:]
    if os.environ.get('FILO_FREECAD_SUBPROCESS') == '1':
        values = values[values.index(str(Path(__file__).resolve()))+1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--export', action='store_true')
    return parser.parse_args(values)


def protected(doc, expected_reset_access=False):
    """Preserve layout and cases, allowing only the specified reset tool hole."""
    records = {}
    for obj in doc.Objects:
        if hasattr(obj, 'KeyReference'):
            records[obj.Name] = {
                'variant': obj.KeycapVariant,
                # Quaternion round trips differ by <6e-16 in rotation matrix
                # coefficients. Preserve transforms to 1e-12, not float bits.
                'placement': [round(v,12) for v in obj.Placement.toMatrix().A],
                'points': [[round(v, 7) for v in p.Vector] for p in obj.Mesh.Points],
                'facets': [list(f.PointIndices) for f in obj.Mesh.Facets],
            }
        elif hasattr(obj, 'CaseStyle'):
            shape = obj.Shape
            if expected_reset_access and getattr(obj,'CaseGroup','')=='base':
                from slim_stack import reset_access_shape
                shape=shape.cut(reset_access_shape('left' if obj.Name.startswith('L_') else 'right'))
            records[obj.Name] = {
                'volume': round(shape.Volume, 5),
                'area': round(shape.Area, 5),
                'vertices': sorted(tuple(round(v, 5) for v in p.Point) for p in shape.Vertexes),
            }
    assert len([n for n in records if '_K' in n]) == 36
    return records


def assembly_signature(doc):
    """Check the changed solids as well as the protected layout after reopening."""
    result = {}
    for obj in doc.Objects:
        if not any(hasattr(obj, field) for field in ('PartID', 'FrameStyle', 'ColorRole', 'BatteryStyle', 'BatteryLeadStyle')):
            continue
        if not hasattr(obj, 'Shape') or obj.Shape.isNull():
            continue
        shape=obj.Shape
        box=shape.optimalBoundingBox(False, False)
        result[obj.Name] = {
            'volume':round(shape.Volume, 5), 'area':round(shape.Area, 5),
            'valid':shape.isValid(), 'solids':len(shape.Solids),
            'bounds':[round(getattr(box, k), 5) for k in
                      ('XMin','YMin','ZMin','XMax','YMax','ZMax')],
            'vertices':sorted(tuple(round(v, 5) for v in p.Point) for p in shape.Vertexes),
            'linked':obj.LinkedObject.Name if obj.TypeId=='App::Link' else None,
        }
    return result


def require_stack_checks(checks):
    assert set(checks['halves']) == {'left','right'}
    for side, half in checks['halves'].items():
        assert not half['static_collisions'], (side, half['static_collisions'])
        assert not half['bottom_reset_probe_collisions'], (side, half['bottom_reset_probe_collisions'])
        assert set(half['cell_motion']) == {'adafruit-1570','301230'}
        for profile, leads in half['cell_motion'].items():
            assert len(leads) == 2
            assert all(lead['outside_attachment_overlap_mm3'] <= .001 for lead in leads), (side, profile, leads)
        assert set(half['profiles']) == {'adafruit-1570','301230'}
        for profile, result in half['profiles'].items():
            assert not result['lead_static_collisions'], (side,profile,result['lead_static_collisions'])
            assert not result['display_sled_lift_collisions'], (side,profile,result['display_sled_lift_collisions'])


def run():
    options = args()
    source, output = options.source.resolve(), options.output.resolve()
    if source == output or output.exists():
        raise ValueError('Use a new isolated output; source is never overwritten')
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        raise RuntimeError('Use the default offscreen FreeCAD helper')
    import FreeCAD as A
    import FreeCADGui as G
    import slim_stack
    import flush_frames
    from configuration import extract, apply as apply_configuration
    from preserve_document_label import preserve_document_label
    G.showMainWindow()
    G.getMainWindow().hide()
    original_hash = digest(source)
    immutable = {p: digest(ROOT/p) for p in [
        'design/layout.json', 'design/revI-profiles.json', 'design/revI-mounts.json',
        'design/revI-magnets.json', 'keycaps/catalog.json']}
    doc = A.openDocument(str(source))
    doc.recompute()
    print('Source opened; recording protected cases and key geometry', file=sys.__stdout__, flush=True)
    before = protected(doc, expected_reset_access=True)
    configuration = extract(doc)
    label = doc.Label
    report = {'scope': 'Slim electronics and flush co-print frame volumes; digital prototype',
              'source_sha256': original_hash, 'physical_acceptance': False}
    report['stack'] = slim_stack.apply(doc)
    doc.recompute()
    print('Stack applied; building and validating flush frames', file=sys.__stdout__, flush=True)
    report['frames'] = flush_frames.apply(doc)
    doc.recompute()
    apply_configuration(doc, configuration)
    report['stack_checks'] = slim_stack.validate(doc)
    require_stack_checks(report['stack_checks'])
    from check_slim_connector_service import check as check_connector_service
    report['connector_service'] = check_connector_service(doc)
    report['connector_service_checker_sha256'] = digest(ROOT/'tools/freecad/check_slim_connector_service.py')
    for side, checks in report['connector_service']['halves'].items():
        assert checks['rigid_housing_path_clear'] and checks['grip_tool_path_clear'], (side, checks)
        assert checks['conservative_choc_bounds_count'] == 18
        assert checks['conservative_cap_bounds_count'] == 18
        for contacts in checks['nominal_terminal_distances'].values():
            assert len(contacts) == 2
            assert all(c['to_plug_mm'] <= .001 and c['to_cell_mm'] <= .001 for c in contacts)
    print('Stack and connector service checks passed; checking protected geometry and saving candidate', file=sys.__stdout__, flush=True)
    assert extract(doc) == configuration, 'Active configuration changed'
    assert protected(doc) == before, 'Case changed beyond reset access, or key geometry changed'
    assert not any(o.TypeId.endswith('Python') for o in doc.Objects)
    changed_before = assembly_signature(doc)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep pre-save evidence if native save/reopen detects a discrepancy.
    # This is an ignored diagnostic checkpoint, never an acceptance receipt.
    checkpoint = {'report': report, 'protected': before, 'configuration': configuration,
                  'assembly_signature': changed_before, 'source_label': label,
                  'immutable_inputs_sha256': immutable}
    (output.parent/'pre-reopen.json').write_text(json.dumps(checkpoint, indent=2)+'\n')
    temporary = output.with_name('candidate-unlabelled.FCStd')
    doc.saveAs(str(temporary))
    A.closeDocument(doc.Name)
    preserve_document_label(temporary, output, label)
    temporary.unlink()
    with zipfile.ZipFile(output) as saved:
        assert 'GuiDocument.xml' in saved.namelist(), 'Native appearance was lost'
    doc = A.openDocument(str(output))
    doc.recompute()
    print('Candidate reopened; verifying saved geometry and configuration', file=sys.__stdout__, flush=True)
    assert doc.Label == label
    assert extract(doc) == configuration
    assert protected(doc) == before
    changed_after = assembly_signature(doc)
    (output.parent/'post-reopen.json').write_text(json.dumps(changed_after, indent=2)+'\n')
    assert changed_after == changed_before, 'Changed solids differ after save/reopen'
    assert not any('Invalid' in o.State for o in doc.Objects)
    assert digest(source) == original_hash, 'Source changed concurrently'
    assert all(digest(ROOT/p) == h for p, h in immutable.items())
    report.update(native_reopen_recompute=True, configuration_preserved=True,
                  case_change_limited_to_reset_access=True, protected_36_caps_preserved=True,
                  immutable_inputs_sha256=immutable,
                  output_sha256=digest(output))
    (output.parent/'installation.json').write_text(json.dumps(report, indent=2)+'\n')
    if options.export:
        os.environ['FLAN36_EXPORT_OUT'] = str(output.parent)
        os.environ['FLAN36_EXPORT_METADATA'] = str(output.parent/'revI.json')
        os.environ['FLAN36_EXPORT_REPORT'] = str(output.parent/'mechanical.json')
        path = ROOT/'tools/freecad/export_revI.py'
        exec(compile(path.read_text(), str(path), 'exec'), {'__file__': str(path)})
    A.closeDocument(doc.Name)
    print('PASS: isolated native candidate saved and reopened; original preserved', flush=True)


if __name__ == '__main__':
    run()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
