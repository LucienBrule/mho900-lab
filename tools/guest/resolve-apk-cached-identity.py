#!/usr/bin/env python3
"""Offline APK/ELF geometry check. Reuses the independently tested reader verifier.

Python is used for its ZIP parser and the existing ELF/maps verification controls.
This program opens local files only and never connects to a process or device.
"""
import argparse
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import zipfile

_spec = importlib.util.spec_from_file_location('cached_reader', Path(__file__).with_name('verify-cached-identity.py'))
v = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v)
APK_SHA256 = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
ENTRY = 'lib/arm64-v8a/libscope-auklet.so'


def archive_entry(data, pin=True):
    v.require(not pin or v.sha(data) == APK_SHA256, 'APK hash differs')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = [e for e in archive.infolist() if e.filename == ENTRY]
        v.require(len(entries) == 1, 'Missing or duplicate Auklet ZIP entry')
        entry = entries[0]
        v.require(entry.compress_type == 0 and entry.flag_bits & 9 == 0,
                  'Entry is compressed, encrypted or uses a data descriptor')
        v.require(entry.file_size == entry.compress_size == 12453760, 'Entry size differs')
        offset = entry.header_offset
        v.require(0 <= offset <= len(data) - 30, 'Local header out of bounds')
        h = struct.unpack_from('<4s5H3I2H', data, offset)
        sig, version, flags, method, _, _, crc, csize, size, name_len, extra_len = h
        v.require(sig == b'PK\x03\x04' and version == entry.extract_version
                  and (flags, method, crc, csize, size) ==
                  (entry.flag_bits, entry.compress_type, entry.CRC, entry.compress_size, entry.file_size),
                  'Local and central ZIP headers disagree')
        start = v.add(offset, 30 + name_len + extra_len)
        end = v.add(start, size)
        v.require(start % v.PAGE == 0 and end <= archive.start_dir <= len(data),
                  'Unaligned or out-of-bounds entry')
        v.require(data[offset + 30:offset + 30 + name_len] == ENTRY.encode(), 'Local entry name differs')
        for other in archive.infolist():
            if other is not entry:
                v.require(not offset <= other.header_offset < end, 'Overlapping local entry')
        payload = archive.read(entry)  # validates ZIP CRC as well
        v.require(payload == data[start:end] and v.sha(payload) == v.STOCK_SHA256,
                  'Embedded stock ELF differs')
        loads = v.elf_loads(payload)
        return start, len(payload), loads


def resolve_apk(rows, path, identity, start, size, loads):
    v.require(path.startswith('/') and not path.endswith(' (deleted)'), 'Invalid APK path')
    selected, other = [], []
    for row in rows:
        same = (row['major'], row['minor'], row['inode']) == identity
        if row['path'] == path or same or row['path'] == path + ' (deleted)':
            v.require(same and row['path'] == path, 'APK backing identity differs')
            file_end = v.add(row['offset'], row['end'] - row['start'])
            if row['offset'] < v.ceiling(start + size) and file_end > start:
                v.require(row['offset'] >= start and file_end <= v.ceiling(start + size),
                          'APK mapping crosses entry boundary')
                r = dict(row, offset=row['offset'] - start)
                selected.append(r)
            else:
                other.append(row)
    bias, addresses = v.resolve(loads, selected, path, identity)
    module_end = v.add(bias, v.ceiling(max(va + memsz for _, _, va, _, memsz in loads)))
    v.require(all(r['end'] <= bias or r['start'] >= module_end for r in other),
              'Other APK mapping intersects module extent')
    # Every file-backed load page must exist, with exact segment-appropriate permissions.
    for flags, offset, va, filesz, _ in loads:
        for page in range(v.floor(va), v.ceiling(va + filesz), v.PAGE):
            covering = [r for r in selected if r['start'] <= bias + page and bias + page + v.PAGE <= r['end']]
            v.require(len(covering) == 1, 'Missing or ambiguous PT_LOAD page')
            row = covering[0]
            v.require(row['perms'] in (('r-xp',) if flags == 5 else ('r--p', 'rw-p')),
                      'Unexpected PT_LOAD page permissions')
            v.require(row['offset'] + bias + page - row['start'] == v.floor(offset) + page - v.floor(va),
                      'PT_LOAD page file geometry differs')
    return bias, addresses, len(selected), len(other)


def controls(data, rows, path, identity, start, size, loads):
    passed = []
    def rejects(name, action):
        try:
            action()
        except (ValueError, zipfile.BadZipFile, struct.error):
            passed.append(name)
            return
        raise ValueError('Negative control accepted: ' + name)
    changed = bytearray(data); changed[-1] ^= 1
    rejects('wrong-apk-pin', lambda: archive_entry(bytes(changed)))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        e = z.getinfo(ENTRY); h = e.header_offset
    for name, index in [('local-method-mismatch', h + 8), ('local-name-mismatch', h + 30),
                        ('local-size-mismatch', h + 22), ('payload-corruption', start + 64)]:
        changed = bytearray(data); changed[index] ^= 1
        rejects(name, lambda b=bytes(changed): archive_entry(b, pin=False))
    rejects('truncated-archive', lambda: archive_entry(data[:start + size - 1], pin=False))
    rejects('wrong-device-identity', lambda: resolve_apk(rows, path, (identity[0]+1, *identity[1:]), start, size, loads))
    rejects('wrong-entry-offset', lambda: resolve_apk(rows, path, identity, start+v.PAGE, size, loads))
    indices = [i for i,r in enumerate(rows) if r['path'] == path and start <= r['offset'] < start+size]
    for name, key, value in [('writable-executable', 'perms', 'rwxp'), ('shared-text', 'perms', 'r-xs'),
                             ('wrong-inode', 'inode', identity[2]+1), ('deleted-file', 'path', path+' (deleted)')]:
        changed = copy.deepcopy(rows); changed[indices[0]][key] = value
        rejects(name, lambda rr=changed: resolve_apk(rr, path, identity, start, size, loads))
    changed = copy.deepcopy(rows); changed[indices[-1]]['offset'] += v.PAGE
    rejects('inconsistent-data-offset', lambda: resolve_apk(changed, path, identity, start, size, loads))
    changed = copy.deepcopy(rows); changed[indices[-1]]['perms'] = 'r--p'
    rejects('cached-range-not-writable', lambda: resolve_apk(changed, path, identity, start, size, loads))
    changed = copy.deepcopy(rows); changed.pop(indices[0])
    rejects('missing-executable-segment', lambda: resolve_apk(changed, path, identity, start, size, loads))
    changed = copy.deepcopy(rows)
    for i in indices:
        row = dict(rows[i]); row['start'] += 0x100000000; row['end'] += 0x100000000; changed.append(row)
    changed.sort(key=lambda r:r['start'])
    rejects('duplicate-loaded-module', lambda: resolve_apk(changed, path, identity, start, size, loads))
    return passed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk', type=Path, required=True)
    p.add_argument('--maps', type=Path, required=True)
    p.add_argument('--mapped-path', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    v.require(not a.output.exists(), 'Output already exists')
    data = a.apk.read_bytes(); maps = a.maps.read_bytes()
    start, size, loads = archive_entry(data)
    rows = v.maps_rows(maps.decode())
    ids = {(r['major'], r['minor'], r['inode']) for r in rows if r['path'] == a.mapped_path}
    v.require(len(ids) == 1, 'APK backing identity missing or ambiguous')
    identity = next(iter(ids))
    bias, addresses, selected, other = resolve_apk(rows, a.mapped_path, identity, start, size, loads)
    negatives = controls(data, rows, a.mapped_path, identity, start, size, loads)
    result = dict(schema_version=1, apk_sha256=v.sha(data), maps_sha256=v.sha(maps),
                  source_sha256=v.sha(Path(__file__).read_bytes()),
                  shared_verifier_sha256=v.sha(Path(v.__file__).read_bytes()),
                  entry_offset=hex(start), entry_size=size, embedded_elf_sha256=v.STOCK_SHA256,
                  predicted_load_bias=hex(bias), predicted_dna_address=hex(addresses[0]),
                  predicted_file_keys_address=hex(addresses[1]), selected_rows=selected, other_apk_rows=other,
                  negative_controls=negatives, memory_read=False, fresh_specimen_apk_hash_verified=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        for k,val in result.items(): f.write(k + ' = ' + json.dumps(val) + '\n')
    print('Offline APK geometry accepted; negative controls:',len(negatives))


if __name__ == '__main__':
    main()
