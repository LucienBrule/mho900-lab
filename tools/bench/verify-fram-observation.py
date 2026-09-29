#!/usr/bin/env python3
"""Independently reconcile a complete paired FRAM journal and cache comparison."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tomllib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'guest'))
from private_cache_snapshot import private_stream

def verify(run):
    root = run / 'reader/fram'
    manifest = tomllib.loads((root / 'manifest.toml').read_text())
    assert manifest['result'] == 'accepted' and manifest['stage'] == 'complete'
    assert manifest['transactions'] == manifest['maximum_transactions'] == 1024
    assert manifest['completed_1'] == manifest['completed_2'] == manifest['image_bytes'] == 8192
    assert manifest['page_bytes'] == 16 and manifest['slave_address'] == 80
    assert manifest['images_equal'] and not manifest['evidence_error']
    assert manifest['retry_count'] == 0
    assert not any(manifest[k] for k in ('force_slave', 'fram_data_writes', 'atomic_snapshot_proven'))
    binding = tomllib.loads((run / 'adapter-binding.toml').read_text())
    assert manifest['expected_major'] == binding['major'] == 89
    assert manifest['expected_minor'] == binding['minor']
    rdev = manifest['observed_rdev']
    major = ((rdev >> 8) & 0xfff) | ((rdev >> 32) & 0xfffff000)
    minor = (rdev & 0xff) | ((rdev >> 12) & 0xffffff00)
    assert (major, minor) == (binding['major'], binding['minor'])
    assert manifest['observed_mode'] & 0xf000 == 0x2000
    raw = (root / 'transactions.bin').read_bytes()
    assert len(raw) == 1024 * 64
    images = [(root / f'image-{i}.bin').read_bytes() for i in (1, 2)]
    assert images[0] == images[1] and len(images[0]) == 8192
    for index in range(1024):
        record = raw[index*64:(index+1)*64]
        round_, offset, returned, error = struct.unpack_from('<QQqQ', record)
        assert (round_, offset, returned, error) == (index//512, (index%512)*16, 2, 0)
        assert record[32:34] == offset.to_bytes(2, 'big')
        assert record[34:50] == images[round_][offset:offset+16]
        assert record[50:] == bytes(14)
    stream, records = private_stream(images[0][0x100:0x800])
    cache, cache_records = private_stream((run / 'reader/observation/work-1.bin').read_bytes())
    def payloads(data):
        result = {}; offset = 8
        while offset < len(data):
            ident, _, length, _, _ = struct.unpack_from('<IIIII', data, offset)
            result[ident] = data[offset+20:offset+20+length]
            offset += 20+length
        return result
    actual, previous = payloads(stream), payloads(cache)
    assert 2337 in actual and 2337 in previous
    assert actual[2337] == previous[2337], 'stored key-backup payload differs from cache'
    return dict(schema_version=1, result='accepted', image_bytes=8192,
                image_sha256=hashlib.sha256(images[0]).hexdigest(),
                journal_sha256=hashlib.sha256(raw).hexdigest(),
                completed_transactions=1024, images_equal=True,
                private_stream_equal_to_cache=stream==cache,
                private_records=[list(x) for x in records],
                cache_records=[list(x) for x in cache_records],
                key_backup_payload_equal_to_cache=True, atomic_snapshot_proven=False,
                physical_power_loss_durability_proven=False)

def verify_binding(run):
    """Join authored binding to raw owner, node, adapter and epoch evidence."""
    binding = tomllib.loads((run / 'adapter-binding.toml').read_text())
    spec = importlib.util.spec_from_file_location('cache_audit', Path(__file__).with_name('verify-private-cache-observation.py'))
    auditor = importlib.util.module_from_spec(spec); spec.loader.exec_module(auditor)
    for phase, label in [('observation', 'before'), ('observation-after', 'after')]:
        root = run / 'reader' / phase
        m = tomllib.loads((root / 'manifest.toml').read_text())
        independent = tomllib.loads((run / f'independent-cache-{label}.toml').read_text())
        assert independent['result'] == 'accepted'
        actual = auditor.audit(root, run/'metadata/loaded-Sparrow.apk')
        assert actual == independent, 'cached verification report differs from raw re-audit'
        assert m['pid'] == binding['pid']
        assert str(m['expected_starttime']) == binding['starttime']
        assert m['expected_boot_id'] == binding['boot_id']
        owner = int(m['owner_complete'], 16)
        headers = [(root / x['file']).read_bytes() for x in m['reads']
                   if int(x['address'], 16) == owner and x['requested'] == 160]
        assert len(headers) == 4 and all(x == headers[0] for x in headers)
        assert struct.unpack_from('<iii', headers[0], 0x58) == (binding['descriptor'], 80, 8192)
    metadata = run / 'metadata'
    for name in ('fram-fd-link', 'fram-fd-link-pre-read', 'fram-fd-link-after'):
        assert (metadata / (name+'.stdout')).read_text().strip() == binding['node']
    stat_values = []
    for name in ('fram-node-stat', 'fram-fd-stat', 'fram-node-stat-pre-read', 'fram-node-stat-after', 'fram-fd-stat-after'):
        raw = (metadata / (name+'.stdout')).read_text().strip()
        stat_values.append(raw)
        value = tomllib.loads(raw)
        assert set(value) == {'mode','major','minor','inode','device'}
        assert all(type(x) == int and x >= 0 for x in value.values())
        assert value['mode'] & 0xf000 == 0x2000
        assert (value['major'], value['minor'], value['inode']) == (binding['major'], binding['minor'], binding['inode'])
    assert len(set(stat_values)) == 1
    for name, key in [('fram-adapter-dev', None), ('fram-adapter-name', 'adapter_name'), ('fram-adapter-path', 'adapter_path')]:
        expected = str(binding['major'])+':'+str(binding['minor']) if key is None else binding[key]
        for suffix in ('', '-after'):
            assert (metadata / (name+suffix+'.stdout')).read_text().strip() == expected
    boot = (metadata/'target-boot-after-fram.stdout').read_text().strip()
    stat = (metadata/'target-stat-after-fram.stdout').read_text()
    assert boot == binding['boot_id'] and stat[stat.rindex(')')+2:].split()[19] == binding['starttime']
    expected = tomllib.loads((run/'control/fram-pin.toml').read_text())['sha256']
    assert expected == 'aff567c13fbd996cd71fd402a39966f35d2856f2b37f4b6a6b68bc2f19660d82'
    for file in (run/'control/read-fram', metadata/'fram-helper-roundtrip'):
        assert hashlib.sha256(file.read_bytes()).hexdigest() == expected
    statpin = tomllib.loads((run/'control/stat-pin.toml').read_text())['sha256']
    for file in (run/'control/stat-node', metadata/'stat-helper-roundtrip'):
        assert hashlib.sha256(file.read_bytes()).hexdigest() == statpin
    return True

def main():
    run = Path(sys.argv[1])
    result = verify(run)
    result["raw_binding_reconciled"] = verify_binding(run)
    with (run / 'independent-fram.toml').open('x') as f:
        for key, value in result.items(): f.write(key+' = '+json.dumps(value)+'\n')
    print('Paired images, exact completion journal and key-backup cache comparison accepted')
if __name__ == '__main__': main()
