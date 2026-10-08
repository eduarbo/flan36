#!/usr/bin/env python3
"""Exercise lossless receipt serialization and reject altered evidence.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import audit_receipt_format as formatter


def rejected(operation, label):
    try:
        operation()
    except AssertionError:
        return
    raise AssertionError(f'{label}: invalid receipt was accepted')


def fixture(field):
    # Nonalphabetical insertion order and unrelated nested values are intentional.
    return {'source_sha256': 'c' * 64, 'nested': {'unicode': 'm\u00e1s', 'values': [None, True, 1.25]},
            field: {'z-first.stl': 'a' * 64, 'a-second.stl': 'b' * 64}, 'passed': True}


def run():
    count = 0
    for name, fields in formatter.FIELDS.items():
        field = fields[0]
        original_value = fixture(field)
        original = formatter.encode(original_value)
        converted = formatter.format_receipt(original, name)
        result = formatter.decode(converted)
        assert [entry['path'] for entry in result[field]] == ['z-first.stl', 'a-second.stl']
        assert formatter.recover_original(converted, name) == original
        assert formatter.format_receipt(converted, name) == converted
        assert result[formatter.PROVENANCE]['original_sha256'] == formatter.digest(original)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / name
            path.write_bytes(converted)
            public, semantic = formatter.load_verified_receipt(path)
            assert public == result and semantic == original_value
        count += 1
        changes = {
            'altered_digest': lambda d: d[field][0].update(sha256='d' * 64),
            'altered_path': lambda d: d[field][0].update(path='different.stl'),
            'altered_other_value': lambda d: d['nested'].update(unicode='changed'),
            'duplicate_path': lambda d: d[field].append(copy.deepcopy(d[field][0])),
            'missing_record': lambda d: d[field].pop(),
            'reordered_records': lambda d: d[field].reverse(),
            'missing_field': lambda d: d.pop(field),
            'missing_provenance': lambda d: d.pop(formatter.PROVENANCE),
            'extra_record_property': lambda d: d[field][0].update(extra=True),
            'invalid_digest': lambda d: d[field][0].update(sha256='invalid'),
            'wrong_field_inventory': lambda d: d[formatter.PROVENANCE].update(fields=['other']),
            'missing_provenance_hash': lambda d: d[formatter.PROVENANCE].pop('original_sha256'),
            'wrong_original_hash': lambda d: d[formatter.PROVENANCE].update(original_sha256='e' * 64),
            'wrong_transformer_hash': lambda d: d[formatter.PROVENANCE].update(transformer_sha256='f' * 64),
            'wrong_schema': lambda d: d[formatter.PROVENANCE].update(schema='other'),
            'extra_provenance': lambda d: d[formatter.PROVENANCE].update(extra=True),
        }
        for label, change in changes.items():
            altered = copy.deepcopy(result)
            change(altered)
            rejected(lambda: formatter.recover_original(formatter.encode(altered), name), label)
            count += 1
        missing = copy.deepcopy(original_value)
        missing.pop(field)
        rejected(lambda: formatter.format_receipt(formatter.encode(missing), name), 'missing producer field')
        duplicate = b'{\n  "passed": true,\n  "passed": false\n}\n'
        rejected(lambda: formatter.format_receipt(duplicate, name), 'duplicate JSON key')
        rejected(lambda: formatter.format_receipt(json.dumps(original_value).encode(), name), 'noncanonical input')
        count += 3
        print('PASS:', name, 'exact roundtrip, ordered entries, idempotency and 19 negative controls')

    # A failed second preflight must not leave the first real-looking target changed.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        directory = root / 'validation'
        directory.mkdir()
        names = list(formatter.FIELDS)
        for name in names:
            (directory / name).write_bytes(formatter.encode(fixture(formatter.FIELDS[name][0])))
        first = directory / names[0]
        before = first.read_bytes()
        (directory / names[1]).write_bytes(formatter.encode({'missing': True}))
        with patch.object(formatter, 'ROOT', root), patch.object(sys, 'argv', ['audit_receipt_format.py']):
            rejected(formatter.main, 'all-target preflight')
        assert first.read_bytes() == before
    print(f'PASS: {count + 1} receipt format controls; no canonical or raw reports modified')


if __name__ == '__main__':
    run()
