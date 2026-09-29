#!/usr/bin/env python3
"""Offline audit of the separate, fixed APK-backed bandwidth reader control.

No process/device commands are issued. The frozen independent Python geometry
oracle is reused with this verifier's two explicit bandwidth ranges in memory;
neither the frozen oracle files nor the preceding identity verifier are edited.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tomllib

sys.dont_write_bytecode = True
SCHEMA = 'mho900-lab.apk-bandwidth-reader/1'
RANGES = ((0xbbcce4, 4, 0xbbbce4), (0xbbcce8, 4, 0xbbbce8))
SAMPLE = bytes.fromhex('1011121320212223')
APK_SHA256 = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
ELF_SHA256 = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_toml(path):
    return tomllib.loads(path.read_text())


def frozen_key(path):
    return str(path).replace('/', '_').replace('.', '_').replace('-', '_')


def audit(run):
    result = read_toml(run / 'result.toml')
    require(result['result'] == 'accepted' and result['physical_access'] is False,
            'Runner did not accept an offline control')
    frozen = read_toml(run / 'frozen-inputs.toml')
    seen = set()
    for folder in ('source', 'inputs'):
        for path in (run / folder).iterdir():
            require(not path.is_symlink(), 'Frozen input is a symlink')
            if not path.is_file():
                continue
            key = frozen_key(path.relative_to(run))
            require(key not in seen and frozen.get(key) == sha(path.read_bytes()),
                    'Frozen input hash absent, ambiguous or changed: ' + str(path.name))
            seen.add(key)
    require(seen == set(frozen), 'Frozen inventory has missing or extra entries')

    spec = importlib.util.spec_from_file_location(
        'bandwidth_apk_geometry', run / 'source/resolve-apk-cached-identity.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    verifier = oracle.v
    require(oracle.APK_SHA256 == APK_SHA256 and verifier.STOCK_SHA256 == ELF_SHA256,
            'Geometry oracle stock pins differ')
    # This separate profile changes only the ranges examined by the independent
    # ELF/maps algorithm; the stock container and PT_LOAD checks remain intact.
    verifier.RANGES = RANGES

    build = read_toml(run / 'inputs/build.toml')
    require(build.get('profile') == 'cached-bandwidth-4-4' and
            build.get('maximum_memory_bytes') == 16, 'Frozen build is not the bandwidth profile')
    for name in ('read-apk-cached-identity', 'apk-cached-mapping-fixture',
                 'read-apk-cached-identity.c'):
        entries = [item for item in build['files'] if item['path'] == name]
        require(len(entries) == 1 and entries[0]['sha256'] ==
                sha((run / 'inputs' / name).read_bytes()), 'Build pin differs: ' + name)
    for name in ('stock.apk', 'read-apk-cached-identity', 'apk-cached-mapping-fixture'):
        require((run / ('roundtrip-' + name)).read_bytes() ==
                (run / 'inputs' / name).read_bytes(), 'Guest roundtrip differs: ' + name)

    apk = (run / 'inputs/stock.apk').read_bytes()
    entry, size, loads = oracle.archive_entry(apk)
    require(entry == 0xf05000 and size == 12453760, 'Unexpected embedded ELF geometry')
    expected = read_toml(run / 'fixture-identity.toml')
    require(expected['expected_sample_hex'] == SAMPLE.hex(), 'Declared bandwidth fixture differs')

    def unique_artifact(suffix, extension='stdout'):
        candidates = list(run.glob('*-' + suffix + '.' + extension))
        require(len(candidates) == 1, 'Missing or ambiguous artifact: ' + suffix)
        return candidates[0]

    def check_common(manifest, mode):
        require(manifest['schema_version'] == SCHEMA and manifest['mode'] == mode,
                'Wrong reader profile or mode')
        require(manifest['pid'] == expected['pid'] and
                manifest['expected_boot_id'] == expected['boot_id'] and
                manifest['library_path'] == expected['path'], 'Fixture target identity differs')
        require(manifest['maximum_memory_bytes'] == 16 and
                manifest['raw_band_size'] == manifest['effective_band_size'] == 4,
                'Bandwidth read extent differs')
        require(verifier.number(manifest['validation_raw_band_virtual_address']) ==
                (0 if mode == 'unmapped-range' else RANGES[0][0]), 'Wrong validated raw-band range')
        for field in ('target_attached', 'target_calls', 'target_writes'):
            require(manifest[field] is False, 'Unexpected target intervention: ' + field)

    for mode, stage in (('wrong-starttime', 'process-identity'),
                        ('wrong-pin', 'library-hash'), ('unmapped-range', 'target-ranges')):
        directory = run / mode
        manifest = read_toml(directory / 'manifest.toml')
        check_common(manifest, mode)
        require(manifest['result'] == 'rejected' and manifest['stage'] == stage and
                manifest['error_number'] == 0, 'Negative did not reach its intended gate: ' + mode)
        require(read_toml(unique_artifact('reader-' + mode, 'toml'))['returncode'] == 3,
                'Negative reader exit differs')
        require(all(manifest[field] == 0 for field in
                    ('mem_open_count', 'memory_read_calls', 'bytes_read',
                     'memory_bytes_requested', 'sample_count')),
                'Negative touched target memory')
        require(manifest['read_results'] == manifest['read_requested'] == [],
                'Negative attempted a memory read')
        require(not list(directory.glob('sample-*')), 'Negative retained unexpected sample files')
        require(verifier.number(manifest['expected_starttime']) ==
                int(expected['starttime']) + (mode == 'wrong-starttime'),
                'Wrong negative starttime request')
        if mode == 'wrong-starttime':
            require(verifier.number(manifest['observed_starttime_before']) == int(expected['starttime']),
                    'Stale-identity control did not observe the declared process')
        else:
            require(manifest['library_sha256'] == ELF_SHA256, 'Negative backing ELF differs')
            require(manifest['expected_library_sha256'] ==
                    ('0' * 64 if mode == 'wrong-pin' else ELF_SHA256), 'Wrong negative pin request')

    directory = run / 'positive'
    manifest = read_toml(directory / 'manifest.toml')
    check_common(manifest, 'positive')
    require(manifest['result'] == 'accepted' and manifest['stage'] == 'complete' and
            manifest['error_number'] == 0, 'Positive reader did not complete')
    require(read_toml(unique_artifact('reader-positive', 'toml'))['returncode'] == 0,
            'Positive reader exit differs')
    require(verifier.number(manifest['expected_starttime']) == int(expected['starttime']),
            'Positive expected starttime differs')
    require(manifest['backing_apk_sha256'] == APK_SHA256 and
            manifest['library_sha256'] == manifest['expected_library_sha256'] == ELF_SHA256,
            'Positive stock pins differ')
    require(manifest['embedded_elf_offset'] == entry and manifest['embedded_elf_size'] == size,
            'Positive container geometry differs')
    for field in ('device', 'inode', 'mode', 'size', 'mtime', 'mtime_nsec', 'ctime', 'ctime_nsec'):
        require(manifest['library_' + field + '_before'] == manifest['library_' + field + '_after'],
                'Backing metadata changed: ' + field)
    require(verifier.number(manifest['library_size_before']) == len(apk) and
            verifier.number(manifest['library_mode_before']) & 0o170000 == 0o100000,
            'Backing file is not the complete regular APK')
    identity = verifier.device_identity(verifier.number(manifest['library_device_before']),
                                        verifier.number(manifest['library_inode_before']))
    raw, resolutions, selected = [], [], []
    for moment in ('before', 'armed', 'between', 'after'):
        require(verifier.proc_identity((directory / ('stat-' + moment + '.txt')).read_text()) ==
                (expected['pid'], int(expected['starttime'])), 'Process identity changed: ' + moment)
        require((directory / ('boot-' + moment + '.txt')).read_text().strip() == expected['boot_id'],
                'Boot identity changed: ' + moment)
        data = (directory / ('maps-' + moment + '.txt')).read_bytes()
        raw.append(data)
        rows = verifier.maps_rows(data.decode())
        resolutions.append(oracle.resolve_apk(rows, expected['path'], identity, entry, size, loads))
        selected.append([row for row in rows if row['path'] == expected['path']])
    require(all(item == resolutions[0] for item in resolutions) and
            all(item == selected[0] for item in selected), 'Relevant APK mappings changed')
    bias, addresses, _, _ = resolutions[0]
    require(bias == verifier.number(manifest['load_bias']) and addresses ==
            [verifier.number(manifest['raw_band_address']),
             verifier.number(manifest['effective_band_address'])], 'Independent bandwidth addressing differs')
    require(manifest['full_maps_changed'] is any(item != raw[0] for item in raw[1:]),
            'Full-map change reporting differs')
    require(manifest['mem_open_count'] == 1 and manifest['mem_open_flags'] == 0 and
            manifest['memory_read_calls'] == 4 and manifest['sample_count'] == 2,
            'Positive read descriptor/call/sample counts differ')
    require(manifest['memory_bytes_requested'] == manifest['bytes_read'] == 16 and
            manifest['read_requested'] == manifest['read_results'] == [4, 4, 4, 4],
            'Positive read sizes differ')
    for field in ('repeat_equal', 'identity_stable', 'maps_stable', 'file_stable'):
        require(manifest[field] is True, 'Positive stability check failed: ' + field)
    for index in (1, 2):
        data = (directory / f'sample-{index}.bin').read_bytes()
        require(data == SAMPLE and sha(data) == manifest[f'sample_{index}_sha256'],
                'Independent synthetic sample comparison failed')

    network = read_toml(run / 'network-control.toml')
    require(network['result'] == 'pass' and network['external_destination_contacted'] is False,
            'Host confinement control failed')
    for field in ('allowed_loopback_tcp', 'denied_other_loopback_tcp',
                  'denied_other_loopback_udp', 'fork_setsid_inheritance'):
        require(network[field] is True, 'Host confinement witness missing: ' + field)
    require(unique_artifact('policy-before').read_bytes() ==
            unique_artifact('policy-after').read_bytes() == b'Enforcing\n',
            'Guest enforcement state changed')
    policy_before = unique_artifact('policy-bytes-before').read_bytes()
    policy_after = unique_artifact('policy-bytes-after').read_bytes()
    require(bool(policy_before) and policy_before == policy_after and
            sha(policy_before) == sha(policy_after), 'Guest policy bytes absent or changed')
    system_before = unique_artifact('system-server-before').read_bytes()
    require(system_before.strip().isdigit() and system_before ==
            unique_artifact('system-server-after').read_bytes(), 'Guest system_server changed')
    return dict(schema_version='mho900-lab.apk-bandwidth-control-verification/1', result='accepted',
                negative_controls=3, process_bytes_read=16, samples_match_synthetic_fixture=True,
                independent_apk_geometry=True, raw_band_virtual_address=hex(RANGES[0][0]),
                effective_band_virtual_address=hex(RANGES[1][0]), enforcement_state_unchanged=True,
                policy_bytes_unchanged=True, guest_policy_sha256=sha(policy_before),
                system_server_unchanged=True, host_confinement_control_passed=True,
                physical_access=False, atomic_snapshot_claimed=False,
                verifier_sha256=sha(Path(__file__).read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output already exists')
    values = audit(args.run)
    with args.output.open('x') as output:
        output.write(''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in values.items()))
    print(json.dumps(values))


if __name__ == '__main__':
    main()
