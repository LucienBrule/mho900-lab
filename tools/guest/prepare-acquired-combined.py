#!/usr/bin/env python3
"""Freeze complete acquired ordinary catalogs for reload-only capability comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import importlib.util


def helper(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


catalog = helper('prepare-acquired-catalog')
base = catalog.base
cap = helper('prepare-capability-fixture')
require = base.require
SEAL = '0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781'
INSTALLED = ['FlexA', *base.ORDER]
PATHS = catalog.seed_paths(INSTALLED)
PARTS = ['entitlement-private-store.js', 'entitlement-acquired-combined-consumer.js',
         'entitlement-capability.js', 'entitlement-art.js', 'entitlement-acquired-combined.js', 'entitlement-baseline.js']
REMOVED = {'acquired_catalog_experiment', 'acquired_capability_experiment', 'catalog_experiment',
           'option_type', 'option_name', 'positive_plaintext', 'negative_plaintext', 'token_padded_bytes'}


def verify_fixture(root):
    cfg = base.table(root / 'synthetic.toml')
    require(cfg['schema_version'] == 'mho900-lab.acquired-option-fixture/1'
            and cfg.get('acquired_combined_experiment') is True and cfg.get('acquired_option_experiment') is True
            and cfg.get('capability_experiment') is True and cfg.get('physical_contact') is False
            and cfg.get('specimen_key_files_used') is True and cfg.get('source_combined_seal') == SEAL,
            'Combined acquired scope differs')
    require(not any(key in REMOVED or key.startswith('catalog_') for key in cfg), 'Old candidate/profile fields remain')
    arm = cfg['capability_arm']
    require(arm in ('stock', 'derived') and cfg['stock_native_sha256'] == base.STOCK
            and cfg['expected_native_sha256'] == (base.STOCK if arm == 'stock' else cap.DERIVED)
            and cfg['expected_bandwidth_enum'] == (17 if arm == 'stock' else 18)
            and cfg['expected_record_offset'] == ('0x151b7a0' if arm == 'stock' else '0x151b850'),
            'Combined capability arm differs')
    require(cfg['model'] == 'MHO984' and cfg['license_type'] == cfg['license_time'] == 0
            and cfg['installer_family'] == 'MHO900' and cfg['token_text_encoding'] == 'low-nibble-first'
            and cfg['consumer_observation_required'] is True
            and cfg['source_persistence_seal'] == catalog.FIRST_SEAL, 'Acquired identity contract differs')
    require(cfg['aes_key_ascii'].encode('ascii') == bytes.fromhex(cfg['key_field_hex'])[:32]
            and len(bytes.fromhex(cfg['key_field_hex'])) == 130 and len(bytes.fromhex(cfg['file_keys_hex'])) == 16
            and cfg['key_left'] and cfg['serial'], 'Acquired key metadata differs')
    base.validate_catalog(cfg['seed_catalog'], INSTALLED)
    require(sorted(item['path'] for item in cfg['seed_files']) == PATHS and len(PATHS) == 22,
            'Combined seed manifest differs')
    require(sorted(['rigol/' + name for name in base.files(root / 'rigol')]
                   + ['model/' + name for name in base.files(root / 'model')]) == PATHS, 'Combined inventory differs')
    for item in cfg['seed_files']:
        require(base.sha(root / item['path']) == item['sha256'], 'Combined seed bytes differ')
    require(base.read(root / 'rigol/data/Key.data').hex() == cfg['key_ciphertext_hex'], 'Original key changed')
    records = helper('verify-synthetic-entitlement').private_records(base.read(root / 'model/private.mem'))
    require(set(records) == {2337, 16192} and records[2337].hex() == cfg['key_ciphertext_hex']
            and len(records[16192]) == 8, 'Combined private record contract differs')
    require(cfg['seed_options'] == [catalog.option_from_witness(root, cfg, name) for name in INSTALLED],
            'Combined positive witnesses differ')
    require(base.files(root / 'ancestor') == ['libscope-auklet.so'] and base.files(root / 'lib') == sorted(base.LIBS),
            'Native inventory differs')
    ancestor = base.read(root / 'ancestor/libscope-auklet.so')
    require(hashlib.sha256(ancestor).hexdigest() == base.STOCK
            and ancestor[cap.PATCH_OFFSET:cap.PATCH_OFFSET + 32] == cap.ORIGINAL, 'Stock ancestor differs')
    native = base.read(root / 'lib/libscope-auklet.so')
    expected = ancestor if arm == 'stock' else ancestor[:cap.PATCH_OFFSET] + cap.REPLACEMENT + ancestor[cap.PATCH_OFFSET + 32:]
    require(native == expected and hashlib.sha256(native).hexdigest() == cfg['expected_native_sha256'],
            'Native exceeds pinned transformation')
    require(sum(a != b for a,b in zip(native, ancestor)) == (0 if arm == 'stock' else 27), 'Changed byte count differs')
    for name,pin in base.LIBS.items():
        if name != 'libscope-auklet.so':
            require(base.sha(root / 'lib' / name) == pin, 'Companion library differs')
    require(base.files(root / 'art') == ['host-build.toml','host.jar','stock.apk']
            and base.sha(root / 'art/stock.apk') == base.APK and base.sha(root / 'ramdisk.img') == base.RAMDISK
            and base.sha(root / 'art/host.jar') == base.table(root / 'art/host-build.toml')['host_sha256'],
            'ART or ramdisk differs')
    return cfg


def source_state(source):
    catalog.verify_seal(source, SEAL)
    result = base.table(source / 'result.toml')
    require(result['runner_exit'] == result['original_exit'] == 0 and result['physical_contact'] is False
            and result['trial_mode'] == 'acquired-catalog-positive' and result['stopped_phase'] == 'trial-complete',
            'Final acquired catalog source incomplete')
    require(base.read(source / 'fixture-before.toml') == base.read(source / 'fixture-final.toml')
            and base.read(source / 'source/synthetic.toml') == base.read(source / 'fixture/synthetic.toml'),
            'Final acquired source changed')
    require(base.read(source / 'initial-boot-id.txt').strip() != base.read(source / 'reboot-boot-id.txt').strip(),
            'Final acquired guest reboot missing')
    cfg = catalog.verify_fixture(source / 'fixture')
    require(cfg['catalog_arm'] == 'positive' and cfg['option_name'] == base.ORDER[-1], 'Source not final catalog candidate')
    verifier = helper('verify-acquired-catalog')
    previous, final = None, None
    for label, phase in [('install','positive'),('process-reload','reload'),('reboot-reload','reload')]:
        directory = source / 'phases' / label
        verdict = verifier.verify(directory, cfg, phase)
        require(verdict['verification'] == 'accepted', 'Independent source verification failed')
        events = [json.loads(line) for line in base.read(directory / 'guest-events.jsonl').splitlines()]
        options = [event['options'] for event in events if event['kind'] == 'option-catalog' and event['checkpoint'] == 'after']
        require(len(options) == 1, 'Final source catalog missing')
        base.validate_catalog(options[0], INSTALLED)
        hashes = {name: base.sha(directory / ('after-' + name)) for name in PATHS}
        require(previous is None or previous == hashes, 'Final source canonical bytes changed across reloads')
        require(final is None or final == options[0], 'Final source catalog changed across reloads')
        previous, final = hashes, options[0]
    return cfg, final


def prepare(source, output, arm):
    require(not output.exists() and arm in ('stock','derived'), 'Invalid output or arm')
    cfg, options = source_state(source)
    ignored = subprocess.run(['git','check-ignore','--quiet','--',str(output.resolve())],
                             cwd=Path(__file__).resolve().parents[2], check=False)
    require(ignored.returncode == 0, 'Private fixture must be Git ignored')
    template = '\n'.join(base.read(Path(__file__).parent / name).decode() for name in PARTS)
    for key in list(cfg):
        if key in REMOVED or key.startswith('catalog_'):
            del cfg[key]
    cfg.update(acquired_combined_experiment=True, capability_experiment=True, capability_arm=arm,
               source_combined_seal=SEAL, expected_native_sha256=base.STOCK if arm == 'stock' else cap.DERIVED,
               expected_bandwidth_enum=17 if arm == 'stock' else 18,
               expected_record_offset='0x151b7a0' if arm == 'stock' else '0x151b850', seed_catalog=options)
    output.mkdir(parents=True, mode=0o700)
    for directory in ('lib','art'):
        shutil.copytree(source / 'fixture' / directory, output / directory)
    shutil.copy2(source / 'fixture/ramdisk.img', output / 'ramdisk.img')
    (output / 'ancestor').mkdir()
    native = base.read(output / 'lib/libscope-auklet.so')
    (output / 'ancestor/libscope-auklet.so').write_bytes(native)
    if arm == 'derived':
        target = output / 'lib/libscope-auklet.so'
        target.chmod(0o600)
        target.write_bytes(native[:cap.PATCH_OFFSET] + cap.REPLACEMENT + native[cap.PATCH_OFFSET + 32:])
    for name in PATHS:
        dest = output / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'phases/reboot-reload' / ('after-' + name), dest)
    cfg['seed_files'] = [dict(path=name, sha256=base.sha(output / name)) for name in PATHS]
    cfg['seed_options'] = [catalog.option_from_witness(output, cfg, name) for name in INSTALLED]
    (output / 'synthetic.toml').write_text(base.dump_config(cfg))
    (output / 'template.js').write_text(template)
    (output / 'preparation.toml').write_text(base.dump_config(dict(
        schema_version='mho900-lab.acquired-combined-preparation/1', source_combined_seal=SEAL,
        source_phase='reboot-reload', arm=arm, ordinary_seed_count=10, canonical_seed_files=22,
        changed_native_bytes=0 if arm == 'stock' else 27, changed_native_extent=0 if arm == 'stock' else 32,
        source_config_sha256=base.sha(source / 'source/synthetic.toml'), physical_contact=False, token_generated=False)))
    verify_fixture(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--arm',choices=('stock','derived'))
    parser.add_argument('--verify-fixture',type=Path)
    args=parser.parse_args()
    if args.verify_fixture:
        require(not any((args.source,args.output,args.arm)), 'Mixed invocation')
        cfg=verify_fixture(args.verify_fixture)
        print('verification = "accepted"\narm = '+json.dumps(cfg['capability_arm']))
    else:
        require(all((args.source,args.output,args.arm)), 'Pass --source --output --arm')
        prepare(args.source,args.output,args.arm)
        print('preparation = "complete"\nphysical_contact = false\nordinary_seed_count = 10')


if __name__ == '__main__':
    main()
