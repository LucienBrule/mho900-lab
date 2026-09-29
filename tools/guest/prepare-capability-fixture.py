#!/usr/bin/env python3
"""Derive an isolated capability fixture from a completed synthetic persistence run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib

STOCK = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
DERIVED = '09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e'
APK = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
PATCH_OFFSET = 0x42949c
ORIGINAL = bytes.fromhex('ea0740f94801088b0b1940b9e80f40f90b0100b9e81780b9287d089b4801088b')
REPLACEMENT = bytes.fromhex('1f010bf10bc102916801889aea0740f94801088b0b1940b9e90f40f92b0100b9')
SEEDS = {'key': ('rigol/data/Key.data', 'after-rigol/data/Key.data'),
         'license': ('rigol/data/FlexA.lic', 'after-rigol/data/FlexA.lic'),
         'private': ('model/private.mem', 'after-model/private.mem'),
         'crypto_witness': ('model/crypto-witness.toml', 'after-model/crypto-witness.toml')}
LIB_PINS = {'libscope-auklet.so': STOCK,
            'libc++_shared.so': '28e7a3a306d7fc222c62abe08741cfcba38c3f336216c4563726bf985ae3cfd6',
            'libfftw3f.so': '52600ef8e0f4c10a97605f8f16c0fb3836b7ac20bcc2a3442647d62426c5ba9c'}
RAMDISK = '98b4925f73aa77cd21a6d4e2a3f384056dba8b2d379162ad2c02f55f3a071398'


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    require(path.is_file() and not path.is_symlink(), 'Expected regular input: ' + path.name)
    return path.read_bytes()


def sha(path):
    return hashlib.sha256(read(path)).hexdigest()


def table(path):
    return tomllib.loads(read(path).decode())


def verify_fixture(root):
    cfg = table(root / 'synthetic.toml')
    arm = cfg['capability_arm']
    require(arm in ('stock', 'derived') and cfg['capability_experiment'] is True, 'Wrong capability arm')
    require(cfg['stock_native_sha256'] == STOCK and cfg['specimen_key_files_used'] is False
            and cfg['physical_contact'] is False, 'Wrong stock ancestry or research boundary')
    require(cfg['expected_bandwidth_enum'] == (17 if arm == 'stock' else 18)
            and cfg['expected_record_offset'] == ('0x151b7a0' if arm == 'stock' else '0x151b850'),
            'Wrong arm capability expectation')
    ancestor = read(root / 'ancestor/libscope-auklet.so')
    require(hashlib.sha256(ancestor).hexdigest() == STOCK, 'Stock ancestor mismatch')
    require(ancestor[PATCH_OFFSET:PATCH_OFFSET + 32] == ORIGINAL, 'Patch precondition mismatch')
    expected = ancestor if arm == 'stock' else ancestor[:PATCH_OFFSET] + REPLACEMENT + ancestor[PATCH_OFFSET + 32:]
    native = read(root / 'lib/libscope-auklet.so')
    pin = STOCK if arm == 'stock' else DERIVED
    require(cfg['expected_native_sha256'] == pin and hashlib.sha256(native).hexdigest() == pin
            and native == expected, 'Native bytes exceed the admitted transformation')
    for name, pin in LIB_PINS.items():
        if name != 'libscope-auklet.so':
            require(sha(root / 'lib' / name) == pin, 'Companion library mismatch')
    require(sha(root / 'art/stock.apk') == APK and sha(root / 'ramdisk.img') == RAMDISK, 'Stock APK/ramdisk mismatch')
    for name, (target, _) in SEEDS.items():
        require(sha(root / target) == cfg['seed_' + name + '_sha256'], 'Capability seed differs: ' + name)
    for directory in ('rigol', 'model'):
        actual = sorted(p.relative_to(root).as_posix() for p in (root / directory).rglob('*') if p.is_file())
        expected_files = sorted(target for target, _ in SEEDS.values() if target.startswith(directory + '/'))
        require(actual == expected_files, 'Unexpected preseeded files')
    require(len(cfg['seed_catalog']) == 14, 'Incomplete seed catalog')
    return cfg


def prepare(source, output, arm):
    result = table(source / 'result.toml')
    require(result['runner_exit'] == 0 and result['original_exit'] == 0 and result['trial_mode'] == 'positive'
            and result['stopped_phase'] == 'trial-complete' and result['physical_contact'] is False,
            'Source is not a completed offline positive persistence run')
    require(read(source / 'initial-boot-id.txt').strip() != read(source / 'reboot-boot-id.txt').strip(),
            'Source guest reboot not proven')
    require(read(source / 'fixture-before.toml') == read(source / 'fixture-final.toml'),
            'Source fixture changed during the positive run')
    config_text = read(source / 'source/synthetic.toml').decode()
    cfg = tomllib.loads(config_text)
    require(cfg['stock_native_sha256'] == STOCK and cfg['physical_contact'] is False
            and cfg['specimen_key_files_used'] is False and not cfg.get('capability_experiment', False),
            'Source fixture is not the ordinary synthetic control')
    hashes, catalogs = {}, []
    for label, phase in [('install', 'positive'), ('process-reload', 'reload'), ('reboot-reload', 'reload')]:
        directory = source / 'phases' / label
        verification = table(directory / 'trial-verification.toml')
        require(verification['verification'] == 'accepted' and verification['phase'] == phase
                and verification['option_after'] is True and verification['physical_contact'] is False
                and verification['ordinary_install_calls'] == (1 if phase == 'positive' else 0),
                'Source phase was not verified: ' + label)
        require(table(directory / 'result.toml')['controller_exit'] == 0, 'Source controller failed')
        events = [json.loads(line) for line in read(directory / 'guest-events.jsonl').splitlines()]
        after = [e['options'] for e in events if e['kind'] == 'option-catalog' and e['checkpoint'] == 'after']
        require(len(after) == 1 and len(after[0]) == 14, 'Source catalog missing')
        catalogs.append(after[0])
        for name, (_, origin) in SEEDS.items():
            digest = sha(directory / origin)
            require(name not in hashes or hashes[name] == digest, 'Source seed changed across reloads: ' + name)
            hashes[name] = digest
            if name != 'crypto_witness':
                require(verification[name + '_sha256'] == digest, 'Source verification hash differs')
    require(catalogs[0] == catalogs[1] == catalogs[2], 'Source option catalog changed across reloads')
    for name, pin in LIB_PINS.items():
        require(sha(source / 'fixture/lib' / name) == pin, 'Source library pin differs')
    require(sha(source / 'fixture/art/stock.apk') == APK and sha(source / 'fixture/ramdisk.img') == RAMDISK,
            'Source APK/ramdisk pin differs')
    native = read(source / 'fixture/lib/libscope-auklet.so')
    require(native[PATCH_OFFSET:PATCH_OFFSET + 32] == ORIGINAL, 'Source patch bytes mismatch')
    prepared_native = native if arm == 'stock' else native[:PATCH_OFFSET] + REPLACEMENT + native[PATCH_OFFSET + 32:]
    require(hashlib.sha256(prepared_native).hexdigest() == (STOCK if arm == 'stock' else DERIVED),
            'Derived full-file pin mismatch')
    output.mkdir(parents=True, exist_ok=False)
    for name in LIB_PINS:
        target = output / 'lib' / name; target.parent.mkdir(exist_ok=True)
        target.write_bytes(prepared_native if name == 'libscope-auklet.so' else read(source / 'fixture/lib' / name))
    (output / 'ancestor').mkdir()
    (output / 'ancestor/libscope-auklet.so').write_bytes(native)
    (output / 'art').mkdir()
    for name in ('host.jar', 'stock.apk', 'host-build.toml'):
        shutil.copy2(source / 'fixture/art' / name, output / 'art' / name)
    shutil.copy2(source / 'fixture/ramdisk.img', output / 'ramdisk.img')
    for name, (target, origin) in SEEDS.items():
        dest = output / target; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'phases/install' / origin, dest)
    additions = {'capability_experiment': True, 'capability_arm': arm,
                 'expected_bandwidth_enum': 17 if arm == 'stock' else 18,
                 'expected_record_offset': '0x151b7a0' if arm == 'stock' else '0x151b850',
                 'expected_native_sha256': STOCK if arm == 'stock' else DERIVED,
                 **{'seed_' + name + '_sha256': digest for name, digest in hashes.items()}}
    lines = [config_text.rstrip(), '', '# Capability arm derived from a verified synthetic persistence seed.']
    lines += [key + ' = ' + json.dumps(value) for key, value in additions.items()]
    for item in catalogs[0]:
        lines += ['', '[[seed_catalog]]'] + [key + ' = ' + json.dumps(value) for key, value in item.items()]
    (output / 'synthetic.toml').write_text('\n'.join(lines) + '\n')
    changed = [i for i, pair in enumerate(zip(native, prepared_native)) if pair[0] != pair[1]]
    manifest = {'schema_version': 'mho900-lab.capability-fixture-preparation/1', 'arm': arm,
                'source_run_id': source.name, 'source_result_sha256': sha(source / 'result.toml'),
                'source_apk_sha256': APK, 'source_native_sha256': STOCK,
                'prepared_native_sha256': hashlib.sha256(prepared_native).hexdigest(),
                'patch_extent_offset': PATCH_OFFSET, 'patch_extent_bytes': 32 if arm == 'derived' else 0,
                'changed_byte_count': len(changed), 'changed_offsets': changed,
                'native_bytes_outside_extent_changed': False, 'physical_contact': False}
    (output / 'capability-preparation.toml').write_text('\n'.join(key + ' = ' + json.dumps(value) for key, value in manifest.items()) + '\n')
    verify_fixture(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_positive_run', nargs='?', type=Path)
    parser.add_argument('output', nargs='?', type=Path)
    parser.add_argument('arm', nargs='?', choices=('stock', 'derived'))
    parser.add_argument('--verify-fixture', type=Path)
    args = parser.parse_args()
    if args.verify_fixture is not None:
        require(args.source_positive_run is None and args.output is None and args.arm is None, 'Mixed invocation')
        cfg = verify_fixture(args.verify_fixture)
        print('verification = "accepted"\narm = ' + json.dumps(cfg['capability_arm']))
    else:
        require(args.source_positive_run is not None and args.output is not None and args.arm is not None,
                'Pass SOURCE_POSITIVE_RUN OUT stock|derived')
        prepare(args.source_positive_run, args.output, args.arm)
        print('preparation = "complete"\narm = ' + json.dumps(args.arm))


if __name__ == '__main__':
    main()
