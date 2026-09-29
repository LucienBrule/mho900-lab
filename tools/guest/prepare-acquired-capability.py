#!/usr/bin/env python3
"""Freeze reload-only acquired-input capability arms; never contact hardware."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tomllib


def helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cap = helper('prepare-capability-fixture')
base = helper('prepare-option-catalog-fixture')
SEAL = '42edff12ab565ba4b57bb8ec30fb39b3c308472b414a0ff24b0e68e14b888b41'
SEEDS = {
    'rigol/data/Key.data': 'after-rigol/data/Key.data',
    'rigol/data/FlexA.lic': 'after-rigol/data/FlexA.lic',
    'model/private.mem': 'after-model/private.mem',
    'model/crypto-FlexA.toml': 'after-model/crypto-FlexA.toml',
}


def verify_fixture(root):
    cfg = base.table(root / 'synthetic.toml')
    assert cfg['schema_version'] == 'mho900-lab.acquired-option-fixture/1'
    assert cfg['acquired_option_experiment'] is True and cfg['acquired_capability_experiment'] is True
    assert cfg['capability_experiment'] is True and cfg['physical_contact'] is False
    assert cfg['specimen_key_files_used'] is True and cfg['source_persistence_seal'] == SEAL
    assert cfg['model'] == 'MHO984' and cfg['option_type'] == 5 and cfg['option_name'] == 'FlexA'
    assert cfg['license_type'] == cfg['license_time'] == 0 and cfg['seed_options'] == []
    base.validate_catalog(cfg['seed_catalog'], [])
    assert cfg['consumer_observation_required'] is True and cfg['token_text_encoding'] == 'low-nibble-first'
    assert cfg['aes_key_ascii'].encode() == bytes.fromhex(cfg['key_field_hex'])[:32]
    assert len(bytes.fromhex(cfg['key_field_hex'])) == 130 and len(bytes.fromhex(cfg['file_keys_hex'])) == 16
    arm = cfg['capability_arm']
    assert arm in ('stock', 'derived')
    bw = 17 if arm == 'stock' else 18
    assert cfg['expected_bandwidth_enum'] == bw
    assert cfg['expected_record_offset'] == ('0x151b7a0' if bw == 17 else '0x151b850')
    ancestor = cap.read(root / 'ancestor/libscope-auklet.so')
    assert hashlib.sha256(ancestor).hexdigest() == cfg['stock_native_sha256'] == cap.STOCK
    assert ancestor[cap.PATCH_OFFSET:cap.PATCH_OFFSET + 32] == cap.ORIGINAL
    expected = ancestor if arm == 'stock' else ancestor[:cap.PATCH_OFFSET] + cap.REPLACEMENT + ancestor[cap.PATCH_OFFSET + 32:]
    assert cap.read(root / 'lib/libscope-auklet.so') == expected
    assert base.sha(root / 'lib/libscope-auklet.so') == cfg['expected_native_sha256'] == (cap.STOCK if bw == 17 else cap.DERIVED)
    for name, pin in cap.LIB_PINS.items():
        if name != 'libscope-auklet.so':
            assert base.sha(root / 'lib' / name) == pin
    assert base.sha(root / 'art/stock.apk') == cap.APK
    assert base.sha(root / 'ramdisk.img') == cap.RAMDISK
    assert sorted(item['path'] for item in cfg['seed_files']) == sorted(SEEDS)
    for item in cfg['seed_files']:
        assert base.sha(root / item['path']) == item['sha256']
    for directory in ('rigol', 'model'):
        assert base.files(root / directory) == sorted(n.split('/', 1)[1] for n in SEEDS if n.startswith(directory + '/'))
    assert (root / 'rigol/data/Key.data').read_bytes().hex() == cfg['key_ciphertext_hex']
    records = helper('verify-synthetic-entitlement').private_records((root / 'model/private.mem').read_bytes())
    assert set(records) == {2337, 16192} and records[2337].hex() == cfg['key_ciphertext_hex'] and len(records[16192]) == 8
    witness = base.table(root / 'model/crypto-FlexA.toml')
    assert witness['plaintext'] == cfg['catalog_candidate']['positive_plaintext'] == cfg['positive_plaintext']
    assert witness['padded_bytes'] == cfg['catalog_candidate']['padded_bytes'] == 48
    assert witness['option_type'] == 5 and witness['option_name'] == 'FlexA'
    helper('verify-acquired-option').ciphertext(witness)
    assert (root / 'rigol/data/FlexA.lic').read_text().strip().split('@') == ['FlexA', witness['wire_token_hex']]
    return cfg


def prepare(source, output, arm):
    assert not output.exists()
    index = source / 'sealed-sha256.txt'
    assert base.sha(index) == SEAL
    for line in index.read_text().splitlines():
        pin, name = line.split(maxsplit=1)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert base.sha(source / name) == pin
    result = base.table(source / 'result.toml')
    assert result['runner_exit'] == result['original_exit'] == 0 and result['physical_contact'] is False
    assert result['trial_mode'] == 'acquired-option' and result['stopped_phase'] == 'trial-complete'
    assert (source / 'initial-boot-id.txt').read_bytes() != (source / 'reboot-boot-id.txt').read_bytes()
    acquired = helper('prepare-acquired-option')
    acquired.verify_fixture(source / 'fixture')
    hashes = {}
    for label, phase in [('install', 'positive'), ('process-reload', 'reload'), ('reboot-reload', 'reload')]:
        p = source / 'phases' / label
        verifier = helper('verify-acquired-option')
        verifier.verify(p, base.table(source / 'source/synthetic.toml'), phase)
        for target, origin in SEEDS.items():
            digest = base.sha(p / origin)
            assert target not in hashes or hashes[target] == digest
            hashes[target] = digest
    cfg = base.table(source / 'source/synthetic.toml')
    cfg.update(acquired_capability_experiment=True, capability_experiment=True,
               capability_arm=arm, source_persistence_seal=SEAL,
               expected_native_sha256=cap.STOCK if arm == 'stock' else cap.DERIVED,
               expected_bandwidth_enum=17 if arm == 'stock' else 18,
               expected_record_offset='0x151b7a0' if arm == 'stock' else '0x151b850')
    cfg['seed_files'] = [dict(path=target, sha256=hashes[target]) for target in SEEDS]
    output.mkdir(parents=True, mode=0o700)
    for name in ('lib', 'art'):
        shutil.copytree(source / 'fixture' / name, output / name)
    shutil.copy2(source / 'fixture/ramdisk.img', output / 'ramdisk.img')
    (output / 'ancestor').mkdir()
    native = cap.read(output / 'lib/libscope-auklet.so')
    (output / 'ancestor/libscope-auklet.so').write_bytes(native)
    if arm == 'derived':
        target = output / 'lib/libscope-auklet.so'
        target.chmod(0o600)
        target.write_bytes(native[:cap.PATCH_OFFSET] + cap.REPLACEMENT + native[cap.PATCH_OFFSET + 32:])
    for target, origin in SEEDS.items():
        dest = output / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'phases/install' / origin, dest)
    (output / 'synthetic.toml').write_text(base.dump_config(cfg))
    verify_fixture(output)
    parts = ['entitlement-private-store.js', 'entitlement-acquired-consumer.js', 'entitlement-capability.js',
             'entitlement-art.js', 'entitlement-acquired-option.js', 'entitlement-baseline.js']
    (output / 'template.js').write_text('\n'.join((Path(__file__).parent / name).read_text() for name in parts))
    changed = sum(a != b for a, b in zip(native, cap.read(output / 'lib/libscope-auklet.so')))
    (output / 'preparation.toml').write_text(
        f'source_seal = "{SEAL}"\narm = "{arm}"\nchanged_native_bytes = {changed}\nphysical_contact = false\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--arm', choices=('stock', 'derived'))
    p.add_argument('--verify-fixture', type=Path)
    a = p.parse_args()
    if a.verify_fixture:
        verify_fixture(a.verify_fixture)
        print('verification = "accepted"')
    else:
        assert a.source and a.output and a.arm
        prepare(a.source, a.output, a.arm)
        print('preparation = "complete"')


if __name__ == '__main__':
    main()
