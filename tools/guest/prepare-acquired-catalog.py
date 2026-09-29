#!/usr/bin/env python3
"""Prepare sealed cumulative acquired-input fixtures, without contacting a device."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess


def helper(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = helper('prepare-option-catalog-fixture')
require = base.require
FIRST_SEAL = '42edff12ab565ba4b57bb8ec30fb39b3c308472b414a0ff24b0e68e14b888b41'
PARTS = ['entitlement-private-store.js', 'entitlement-acquired-catalog-consumer.js',
         'entitlement-capability.js', 'entitlement-art.js', 'entitlement-acquired-catalog.js',
         'entitlement-baseline.js']
IDENTITY = ('model', 'serial', 'key_left', 'dna_hex', 'file_keys_hex', 'key_field_hex',
            'key_ciphertext_hex', 'aes_key_ascii', 'source_baseline_seal')


def candidate(cfg, name):
    require(name in base.ORDER, 'Candidate outside bounded catalog')
    positive = cfg['model'] + '#' + cfg['serial'] + '#' + name + '#guest#0#0'
    negative = cfg['model'] + '#' + cfg['serial'] + '#Wrong#guest#0#0'
    require(len(positive.encode('ascii')) < 48 and len(negative.encode('ascii')) < 48,
            'Acquired candidate exceeds48byte contract')
    return dict(type=base.TYPES[name], name=name, padded_bytes=48,
                positive_plaintext=positive, negative_plaintext=negative)


def seed_paths(installed):
    return sorted(['rigol/data/Key.data', 'model/private.mem']
                  + ['rigol/data/' + name + '.lic' for name in installed]
                  + ['model/crypto-' + name + '.toml' for name in installed])


def option_from_witness(root, cfg, name):
    witness = base.table(root / ('model/crypto-' + name + '.toml'))
    plain = cfg['model'] + '#' + cfg['serial'] + '#' + name + '#guest#0#0'
    require(witness['schema_version'] == 3 and witness['phase'] == 'positive'
            and witness['option_type'] == base.TYPES[name] and witness['option_name'] == name
            and witness['plaintext'] == plain and witness['padded_bytes'] == 48,
            'Acquired positive witness metadata differs')
    cipher, wire, _ = helper('verify-acquired-option').ciphertext(witness)
    require(base.read(root / ('rigol/data/' + name + '.lic')).decode('ascii').strip() == name + '@' + wire,
            'License differs from stock consumer witness')
    return dict(name=name, type=base.TYPES[name], plaintext=plain, padded_bytes=48,
                token_ciphertext_hex=cipher, wire_token_hex=wire)


def verify_fixture(root):
    cfg = base.table(root / 'synthetic.toml')
    require(cfg['schema_version'] == 'mho900-lab.acquired-option-fixture/1'
            and cfg.get('acquired_option_experiment') is True
            and cfg.get('acquired_catalog_experiment') is True
            and cfg.get('physical_contact') is False and cfg.get('specimen_key_files_used') is True
            and not cfg.get('capability_experiment', False)
            and not cfg.get('acquired_capability_experiment', False), 'Invalid acquired catalog scope')
    require(cfg['stock_native_sha256'] == cfg['expected_native_sha256'] == base.STOCK
            and cfg['model'] == 'MHO984' and cfg['license_type'] == cfg['license_time'] == 0
            and cfg['installer_family'] == 'MHO900' and cfg['token_text_encoding'] == 'low-nibble-first'
            and cfg['consumer_observation_required'] is True, 'Acquired personality differs')
    require(cfg['aes_key_ascii'].encode('ascii') == bytes.fromhex(cfg['key_field_hex'])[:32]
            and len(bytes.fromhex(cfg['key_field_hex'])) == 130
            and len(bytes.fromhex(cfg['file_keys_hex'])) == 16 and cfg['key_left'] and cfg['serial'],
            'Acquired key metadata differs')
    wanted = candidate(cfg, cfg['option_name'])
    require(cfg['catalog_candidate'] == wanted and cfg['catalog_order'] == base.ORDER
            and cfg['option_type'] == wanted['type'] and cfg['token_padded_bytes'] == 48
            and cfg['positive_plaintext'] == wanted['positive_plaintext']
            and cfg['negative_plaintext'] == wanted['negative_plaintext'], 'Candidate contract differs')
    require(cfg['catalog_arm'] in ('negative48', 'positive') and cfg['catalog_mode'] == cfg['catalog_arm'],
            'Invalid catalog arm')
    index = base.ORDER.index(wanted['name'])
    require(cfg['catalog_arm'] != 'negative48' or index == 0, 'Negative control limited to first candidate')
    require(re.fullmatch('[0-9a-f]{64}', cfg['source_catalog_seal']) is not None
            and cfg['source_persistence_seal'] == FIRST_SEAL, 'Missing acquired lineage seal')
    require(index != 0 or cfg['source_catalog_seal'] == FIRST_SEAL, 'First candidate source seal differs')
    installed = ['FlexA', *base.ORDER[:index]]
    base.validate_catalog(cfg['seed_catalog'], installed)
    paths = seed_paths(installed)
    require(sorted(item['path'] for item in cfg['seed_files']) == paths, 'Seed manifest differs')
    require(sorted(['rigol/' + p for p in base.files(root / 'rigol')]
                   + ['model/' + p for p in base.files(root / 'model')]) == paths, 'Unexpected seed file')
    for item in cfg['seed_files']:
        require(base.sha(root / item['path']) == item['sha256'], 'Seed hash differs')
    require(base.read(root / 'rigol/data/Key.data').hex() == cfg['key_ciphertext_hex'], 'Original acquired key changed')
    records = helper('verify-synthetic-entitlement').private_records(base.read(root / 'model/private.mem'))
    require(set(records) == {2337, 16192} and records[2337].hex() == cfg['key_ciphertext_hex']
            and len(records[16192]) == 8, 'Private key/saved-time contract differs')
    require(cfg['seed_options'] == [option_from_witness(root, cfg, name) for name in installed],
            'Cumulative acquired seed metadata differs')
    base.check_runtime(root)
    return cfg


def verify_seal(source, pin):
    index = source / 'sealed-sha256.txt'
    require(re.fullmatch('[0-9a-f]{64}', pin) is not None and base.sha(index) == pin, 'Source seal mismatch')
    members = set()
    for line in base.read(index).decode('ascii').splitlines():
        digest, relative = line.split(maxsplit=1)
        path = Path(relative)
        require(not path.is_absolute() and '..' not in path.parts and relative not in members
                and path.as_posix() == relative and relative != 'sealed-sha256.txt', 'Invalid seal member')
        require(all(not p.is_symlink() for p in (source / path).parents if p != source.parent),
                'Symlink in source ancestry')
        require(base.sha(source / relative) == digest, 'Source seal member mismatch')
        members.add(relative)
    # Every input that can affect fixture state or verification must be sealed.
    for directory in ('source', 'fixture', 'phases'):
        require(all(directory + '/' + name in members for name in base.files(source / directory)),
                'Unsealed source input')
    require({'result.toml', 'fixture-before.toml', 'fixture-final.toml',
             'initial-boot-id.txt', 'reboot-boot-id.txt'} <= members, 'Incomplete source seal')


def source_state(source, name, pin):
    verify_seal(source, pin)
    result = base.table(source / 'result.toml')
    require(result['runner_exit'] == result['original_exit'] == 0
            and result['physical_contact'] is False and result['stopped_phase'] == 'trial-complete',
            'Source trial incomplete')
    require(base.read(source / 'fixture-before.toml') == base.read(source / 'fixture-final.toml'),
            'Source fixture changed')
    require(base.read(source / 'initial-boot-id.txt').strip() != base.read(source / 'reboot-boot-id.txt').strip(),
            'Source guest reboot missing')
    cfg = base.table(source / 'source/synthetic.toml')
    require(base.read(source / 'source/synthetic.toml') == base.read(source / 'fixture/synthetic.toml'),
            'Source configuration differs from fixture')
    index = base.ORDER.index(name)
    if index == 0:
        require(pin == FIRST_SEAL and result['trial_mode'] == 'acquired-option', 'First candidate requires sealed FlexA source')
        helper('prepare-acquired-option').verify_fixture(source / 'fixture')
        verifier = helper('verify-acquired-option')
    else:
        require(result['trial_mode'] == 'acquired-catalog-positive'
                and cfg['catalog_arm'] == 'positive' and cfg['option_name'] == base.ORDER[index - 1],
                'Cumulative source is not immediate positive predecessor')
        verify_fixture(source / 'fixture')
        verifier = helper('verify-acquired-catalog')
    installed = ['FlexA', *base.ORDER[:index]]
    previous = None
    catalog = None
    for label, phase in [('install', 'positive'), ('process-reload', 'reload'), ('reboot-reload', 'reload')]:
        directory = source / 'phases' / label
        verdict = verifier.verify(directory, cfg, phase)
        require(verdict['verification'] == 'accepted', 'Independent source verifier rejected phase')
        events = [json.loads(line) for line in base.read(directory / 'guest-events.jsonl').splitlines()]
        after = [e['options'] for e in events if e['kind'] == 'option-catalog' and e['checkpoint'] == 'after']
        require(len(after) == 1, 'Source catalog missing')
        base.validate_catalog(after[0], installed)
        require(catalog is None or catalog == after[0], 'Source catalog changed across reloads')
        catalog = after[0]
        hashes = {path: base.sha(directory / ('after-' + path)) for path in seed_paths(installed)}
        require(previous is None or previous == hashes, 'Source canonical seed changed across reloads')
        previous = hashes
    return cfg, catalog


def prepare(source, output, arm, name, source_seal=None):
    require(not output.exists(), 'Output already exists')
    require(arm in ('negative48', 'positive') and name in base.ORDER, 'Invalid arm/candidate')
    require(arm != 'negative48' or name == base.ORDER[0], 'Negative control limited to first candidate')
    require(source_seal is not None or name == base.ORDER[0], 'Cumulative source requires explicit --source-seal')
    seal = source_seal or FIRST_SEAL
    cfg, catalog = source_state(source, name, seal)
    ignored = subprocess.run(['git', 'check-ignore', '--quiet', '--', str(output.resolve())],
                             cwd=Path(__file__).resolve().parents[2], check=False)
    require(ignored.returncode == 0, 'Private fixture output must be ignored by Git')
    installed = ['FlexA', *base.ORDER[:base.ORDER.index(name)]]
    paths = seed_paths(installed)
    metadata = candidate(cfg, name)
    source_identity = {key: cfg[key] for key in IDENTITY}
    cfg.update(acquired_catalog_experiment=True, catalog_arm=arm, catalog_mode=arm,
               catalog_order=base.ORDER, catalog_candidate=metadata, option_name=name,
               option_type=metadata['type'], token_padded_bytes=48,
               positive_plaintext=metadata['positive_plaintext'], negative_plaintext=metadata['negative_plaintext'],
               source_persistence_seal=FIRST_SEAL, source_catalog_seal=seal, seed_catalog=catalog)
    template = '\n'.join(base.read(Path(__file__).parent / name).decode() for name in PARTS)
    output.mkdir(parents=True, mode=0o700)
    for directory in ('lib', 'art'):
        shutil.copytree(source / 'fixture' / directory, output / directory)
    shutil.copy2(source / 'fixture/ramdisk.img', output / 'ramdisk.img')
    for relative in paths:
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'phases/reboot-reload' / ('after-' + relative), dest)
    cfg['seed_files'] = [dict(path=relative, sha256=base.sha(output / relative)) for relative in paths]
    cfg['seed_options'] = [option_from_witness(output, cfg, item) for item in installed]
    require({key: cfg[key] for key in IDENTITY} == source_identity, 'Acquired identity changed')
    (output / 'synthetic.toml').write_text(base.dump_config(cfg))
    (output / 'template.js').write_text(template)
    (output / 'preparation.toml').write_text(base.dump_config(dict(
        schema_version='mho900-lab.acquired-catalog-preparation/1', source_run_id=source.name,
        source_seal=seal, source_phase='reboot-reload', candidate=name, arm=arm,
        source_config_sha256=base.sha(source / 'source/synthetic.toml'),
        source_journal_sha256=base.sha(source / 'phases/reboot-reload/guest-events.jsonl'),
        source_native_sha256=base.STOCK, source_apk_sha256=base.APK,
        token_generated=False, physical_contact=False)))
    verify_fixture(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--source-seal')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--candidate', choices=base.ORDER)
    parser.add_argument('--arm', choices=('negative48', 'positive'))
    parser.add_argument('--verify-fixture', type=Path)
    args = parser.parse_args()
    if args.verify_fixture:
        require(not any((args.source, args.source_seal, args.output, args.candidate, args.arm)), 'Mixed invocation')
        cfg = verify_fixture(args.verify_fixture)
        print('verification = "accepted"\ncandidate = ' + json.dumps(cfg['option_name']))
    else:
        require(all((args.source, args.output, args.candidate, args.arm)), 'Pass --source --output --candidate --arm')
        prepare(args.source, args.output, args.arm, args.candidate, args.source_seal)
        print('preparation = "complete"\nphysical_contact = false\ncandidate = ' + json.dumps(args.candidate))


if __name__ == '__main__':
    main()
