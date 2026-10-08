#!/usr/bin/env python3
"""Losslessly serialize two audit digest maps as explicit path/SHA-256 records.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    'revI-audit-delivery.json': ['inputs_sha256'],
    'revI-mechanical.json': ['exported_files'],
}
PROVENANCE = 'receipt_serialization'
SCHEMA = 'flan36-audit-receipt-path-digests-v1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode('utf-8')


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, f'Duplicate JSON key: {key}'
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=unique)
    assert isinstance(value, dict), 'Receipt must be an object'
    assert encode(value) == data, 'Receipt must use its original indent=2, newline serialization'
    return value


def validate_entry(path, checksum):
    assert isinstance(path, str) and path, 'Digest path must be a nonempty string'
    assert isinstance(checksum, str) and re.fullmatch(r'[0-9a-f]{64}', checksum), 'Invalid SHA-256'


def recover_original(data, name):
    """Verify provenance and recover the exact original producer bytes."""
    assert name in FIELDS, 'Unsupported receipt'
    value = decode(data)
    assert PROVENANCE in value, 'Missing serialization provenance'
    provenance = value.pop(PROVENANCE)
    assert isinstance(provenance, dict) and set(provenance) == {
        'schema', 'original_sha256', 'transformer_sha256', 'fields'}, 'Invalid serialization provenance'
    assert provenance['schema'] == SCHEMA, 'Unknown serialization schema'
    assert provenance['transformer_sha256'] == digest(Path(__file__).read_bytes()), 'Transformer has changed'
    assert provenance['fields'] == FIELDS[name], 'Converted field inventory differs'
    for field in FIELDS[name]:
        assert field in value and isinstance(value[field], list), f'Missing converted list: {field}'
        restored = {}
        for entry in value[field]:
            assert isinstance(entry, dict) and list(entry) == ['path', 'sha256'], 'Invalid digest record'
            path, checksum = entry['path'], entry['sha256']
            validate_entry(path, checksum)
            assert path not in restored, f'Duplicate digest path: {path}'
            restored[path] = checksum
        value[field] = restored
    original = encode(value)
    assert digest(original) == provenance['original_sha256'], 'Original receipt integrity mismatch'
    return original


def format_receipt(data, name):
    assert name in FIELDS, 'Unsupported receipt'
    value = decode(data)
    if PROVENANCE in value:
        recover_original(data, name)
        return data
    for field in FIELDS[name]:
        assert field in value and isinstance(value[field], dict), f'Missing producer digest map: {field}'
        for path, checksum in value[field].items():
            validate_entry(path, checksum)
        value[field] = [{'path': path, 'sha256': checksum} for path, checksum in value[field].items()]
    value[PROVENANCE] = {'schema': SCHEMA, 'original_sha256': digest(data),
                         'transformer_sha256': digest(Path(__file__).read_bytes()),
                         'fields': FIELDS[name]}
    formatted = encode(value)
    assert recover_original(formatted, name) == data, 'Lossless conversion failed'
    return formatted


def load_verified_receipt(path):
    """Return publishable records and original semantics after exact recovery."""
    path = Path(path)
    data = path.read_bytes()
    original = recover_original(data, path.name)
    return decode(data), decode(original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify formatted receipts without writing')
    args = parser.parse_args()
    # Preflight both receipts before changing either; generating reports stay untouched.
    prepared = []
    for name in FIELDS:
        path = ROOT / 'validation' / name
        before = path.read_bytes()
        if args.check:
            recover_original(before, name)
        else:
            prepared.append((path, before, format_receipt(before, name)))
    for path, before, formatted in prepared:
        assert path.read_bytes() == before, f'Concurrent receipt change: {path.name}'
        if formatted != before:
            path.write_bytes(formatted)
        assert path.read_bytes() == formatted
        recover_original(formatted, path.name)
    print('PASS: two lossless audit receipt serializations verified')


if __name__ == '__main__':
    main()
