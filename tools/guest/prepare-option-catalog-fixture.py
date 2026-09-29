#!/usr/bin/env python3
"""Prepare bounded cumulative option fixtures from successful synthetic guest evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib

STOCK = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
APK = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
RAMDISK = '98b4925f73aa77cd21a6d4e2a3f384056dba8b2d379162ad2c02f55f3a071398'
LIBS = {'libscope-auklet.so': STOCK,
        'libc++_shared.so': '28e7a3a306d7fc222c62abe08741cfcba38c3f336216c4563726bf985ae3cfd6',
        'libfftw3f.so': '52600ef8e0f4c10a97605f8f16c0fb3836b7ac20bcc2a3442647d62426c5ba9c'}
ORDER = ['BWU05T08', 'AFG100', 'AFG50', 'AUDIOA', 'AUTOA', 'AEROA', 'RLU05', 'BWU03T05', 'BWU03T08']
CATALOG = {0: 'BND', 1: 'EMBD', 2: 'COMP', 3: 'AUTO', 4: 'AUTOA', 5: 'FlexA',
           6: 'AUDIOA', 7: 'AEROA', 19: 'RLU05', 30: 'AFG50', 29: 'AFG100',
           22: 'BWU03T05', 23: 'BWU03T08', 24: 'BWU05T08'}
TYPES = {name: ident for ident, name in CATALOG.items()}


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


def files(root):
    result = []
    for path in root.rglob('*'):
        require(not path.is_symlink() and (path.is_dir() or path.is_file()), 'Link or special file in fixture')
        if path.is_file():
            result.append(path.relative_to(root).as_posix())
    return sorted(result)


def check_runtime(root):
    require(files(root / 'lib') == sorted(LIBS), 'Unexpected library inventory')
    for name, pin in LIBS.items():
        require(sha(root / 'lib' / name) == pin, 'Stock library pin mismatch')
    require(files(root / 'art') == ['host-build.toml', 'host.jar', 'stock.apk'], 'Unexpected ART inventory')
    require(sha(root / 'art/stock.apk') == APK and sha(root / 'ramdisk.img') == RAMDISK,
            'Stock APK or ramdisk pin mismatch')
    require(sha(root / 'art/host.jar') == table(root / 'art/host-build.toml')['host_sha256'], 'ART host pin mismatch')


def candidate(name):
    require(name in ORDER, 'Unknown catalog candidate')
    positive = 'MHO984#SYNTH01#' + name + '#guest#0#0'
    padded = 32 if len(positive) <= 32 else 48
    require(len(positive) <= padded, 'Candidate exceeds bounded token size')
    return {'name': name, 'type': TYPES[name], 'padded_bytes': padded,
            'positive_plaintext': positive, 'negative_plaintext': 'MHO984#SYNTH01#Wrong#guest#0#0'}


def validate_catalog(catalog, installed):
    require(len(catalog) == 14 and {x['option_type']: x['option_name'] for x in catalog} == CATALOG,
            'Full catalog membership differs')
    expected = {'EMBD', 'COMP', 'AUTO', *installed}
    require(all(type(x['valid']) is bool and x['status'] == 0 and x['valid'] == (x['option_name'] in expected)
                for x in catalog), 'Seed catalog contains an unexpected enabled/disabled state')


def option_from_witness(root, name):
    relative = 'model/crypto-witness.toml' if name == 'FlexA' else 'model/crypto-' + name + '.toml'
    witness = table(root / relative)
    require(witness['phase'] == 'positive', 'Rejected witness cannot seed a catalog trial')
    if name == 'FlexA':
        require(witness['schema_version'] == 2, 'Expected original FlexA witness schema2')
        plain, padded = 'MHO984#SYNTH01#FlexA#guest#0#0', 32
        require(bytes.fromhex(witness['key_ciphertext_hex']) == read(root / 'rigol/data/Key.data'),
                'Original FlexA witness/key mismatch')
    else:
        expected = candidate(name)
        require(witness['schema_version'] == 3 and witness['option_name'] == name
                and witness['option_type'] == TYPES[name] and witness['plaintext'] == expected['positive_plaintext']
                and witness['padded_bytes'] == expected['padded_bytes'], 'Option witness metadata differs')
        plain, padded = witness['plaintext'], witness['padded_bytes']
    cipher, wire = witness['token_ciphertext_hex'], witness['wire_token_hex']
    require(len(bytes.fromhex(cipher)) == padded and len(cipher) == 2 * padded,
            'Witness ciphertext size differs')
    require(wire == ''.join(cipher[i + 1] + cipher[i] for i in range(0, len(cipher), 2)),
            'Witness wire encoding differs')
    require(read(root / ('rigol/data/' + name + '.lic')).decode('ascii').strip() == name + '@' + wire,
            'Stock license bytes differ from witness')
    return {'name': name, 'type': TYPES[name], 'wire_token_hex': wire,
            'token_ciphertext_hex': cipher, 'plaintext': plain, 'padded_bytes': padded}


def dump_config(cfg):
    lines = []
    for key, value in cfg.items():
        if not isinstance(value, dict) and not (isinstance(value, list) and value and isinstance(value[0], dict)):
            lines.append(key + ' = ' + json.dumps(value))
    for key, value in cfg.items():
        if isinstance(value, dict):
            lines += ['', '[' + key + ']'] + [k + ' = ' + json.dumps(v) for k, v in value.items()]
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                lines += ['', '[[' + key + ']]'] + [k + ' = ' + json.dumps(v) for k, v in item.items()]
    return '\n'.join(lines) + '\n'


def verify_fixture(root):
    cfg = table(root / 'synthetic.toml')
    require(cfg['schema_version'] == 'mho900-lab.synthetic-entitlement-fixture/1'
            and cfg.get('catalog_experiment') is True and not cfg.get('capability_experiment', False)
            and cfg['physical_contact'] is False and cfg['specimen_key_files_used'] is False,
            'Not an offline stock catalog fixture')
    require(cfg['stock_native_sha256'] == cfg['expected_native_sha256'] == STOCK and cfg['model'] == 'MHO984' and cfg['serial'] == 'SYNTH01'
            and cfg['aes_key_ascii'] == '0123456789abcdef0123456789abcdef'
            and cfg['token_text_encoding'] == 'low-nibble-first' and cfg['consumer_observation_required'] is True,
            'Synthetic personality changed')
    check_runtime(root)
    wanted = candidate(cfg['catalog_candidate']['name'])
    require(cfg['catalog_candidate'] == wanted and cfg['catalog_order'] == ORDER, 'Candidate contract differs')
    require(cfg['option_name'] == wanted['name'] and cfg['option_type'] == wanted['type']
            and cfg['token_padded_bytes'] == wanted['padded_bytes']
            and cfg['positive_plaintext'] == wanted['positive_plaintext']
            and cfg['negative_plaintext'] == wanted['negative_plaintext'], 'Top-level candidate aliases differ')
    index = ORDER.index(wanted['name'])
    require(cfg['catalog_mode'] in ('negative48', 'positive')
            and cfg['catalog_arm'] == cfg['catalog_mode'], 'Unknown or inconsistent catalog arm')
    require(cfg['catalog_mode'] != 'negative48' or index == 0, 'Negative48 must use first candidate')
    installed = ['FlexA', *ORDER[:index]]
    validate_catalog(cfg['seed_catalog'], installed)
    wanted_files = ['rigol/data/Key.data', 'model/private.mem', 'model/crypto-witness.toml']
    wanted_files += ['rigol/data/' + name + '.lic' for name in installed]
    wanted_files += ['model/crypto-' + name + '.toml' for name in ORDER[:index]]
    require(sorted(x['path'] for x in cfg['seed_files']) == sorted(wanted_files), 'Seed manifest membership differs')
    actual_files = ['rigol/' + p for p in files(root / 'rigol')] + ['model/' + p for p in files(root / 'model')]
    require(sorted(actual_files) == sorted(wanted_files), 'Seed contains undeclared files')
    for item in cfg['seed_files']:
        require(sha(root / item['path']) == item['sha256'], 'Seed bytes differ from source manifest')
    require(cfg['seed_options'] == [option_from_witness(root, name) for name in installed],
            'Installed option metadata differs from preserved witness')
    return cfg


def source_state(source, mode, name):
    result = table(source / 'result.toml')
    require(result['runner_exit'] == 0 and result['original_exit'] == 0 and result['stopped_phase'] == 'trial-complete'
            and result['physical_contact'] is False, 'Source trial failed or incomplete')
    require(read(source / 'fixture-before.toml') == read(source / 'fixture-final.toml'), 'Source fixture changed')
    cfg = table(source / 'source/synthetic.toml')
    require(not cfg.get('capability_experiment', False), 'Derived/capability trial cannot seed catalog')
    index = ORDER.index(name)
    if cfg.get('catalog_experiment', False):
        require(mode == 'positive' and result['trial_mode'] in ('catalog-positive', 'catalog-final')
                and cfg['catalog_mode'] == 'positive', 'Negative catalog trial cannot seed positive state')
        require(index > 0 and cfg['catalog_candidate']['name'] == ORDER[index - 1], 'Wrong predecessor candidate')
        labels = [('install', 'positive')]
    else:
        require(index == 0 and result['trial_mode'] == 'positive', 'First candidate requires verified FlexA run')
        labels = [('install', 'positive'), ('process-reload', 'reload'), ('reboot-reload', 'reload')]
        require(read(source / 'initial-boot-id.txt').strip() != read(source / 'reboot-boot-id.txt').strip(),
                'Initial FlexA guest reboot not proven')
    expected_installed = ['FlexA', *ORDER[:index]]
    catalogs = []
    previous = None
    for label, phase in labels:
        p = source / 'phases' / label
        summary = table(p / 'trial-verification.toml')
        require(summary['verification'] == 'accepted' and summary['phase'] == phase
                and summary['ordinary_install_calls'] == (1 if phase == 'positive' else 0)
                and summary['physical_contact'] is False, 'Source phase not accepted')
        require(table(p / 'result.toml')['controller_exit'] == 0, 'Source controller failed')
        events = [json.loads(line) for line in read(p / 'guest-events.jsonl').splitlines()]
        after = [e['options'] for e in events if e['kind'] == 'option-catalog' and e['checkpoint'] == 'after']
        require(len(after) == 1, 'Missing source catalog')
        validate_catalog(after[0], expected_installed)
        catalogs.append(after[0])
        # Initial source persistence must preserve every canonical seed byte across its three phases.
        names = ['after-rigol/data/Key.data', 'after-model/private.mem', 'after-model/crypto-witness.toml']
        names += ['after-rigol/data/' + item + '.lic' for item in expected_installed]
        names += ['after-model/crypto-' + item + '.toml' for item in ORDER[:index]]
        hashes = {rel: sha(p / rel) for rel in names}
        require(previous is None or previous == hashes, 'Source seed changed across reloads')
        previous = hashes
    require(all(item == catalogs[0] for item in catalogs), 'Source catalog changed across reloads')
    return cfg, catalogs[0]


def prepare(source, output, mode, name):
    require(mode in ('negative48', 'positive') and name in ORDER, 'Invalid mode/candidate')
    require(mode != 'negative48' or name == 'BWU05T08', 'Negative48 is bounded to BWU05T08')
    cfg, catalog = source_state(source, mode, name)
    check_runtime(source / 'fixture')
    phase = source / 'phases/install'
    index = ORDER.index(name)
    installed = ['FlexA', *ORDER[:index]]
    selected = ['rigol/data/Key.data', 'model/private.mem', 'model/crypto-witness.toml']
    selected += ['rigol/data/' + item + '.lic' for item in installed]
    selected += ['model/crypto-' + item + '.toml' for item in ORDER[:index]]
    # No acquired files or historical private snapshot copies enter the next guest.
    output.mkdir(parents=True, exist_ok=False)
    for directory in ('lib', 'art'):
        shutil.copytree(source / 'fixture' / directory, output / directory)
    shutil.copy2(source / 'fixture/ramdisk.img', output / 'ramdisk.img')
    for relative in selected:
        origin = phase / ('after-' + relative)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)
    metadata = candidate(name)
    for key in list(cfg):
        if key.startswith('seed_') or key.startswith('catalog_') or key in ('expected_native_sha256', 'capability_arm'):
            cfg.pop(key)
    cfg.update(catalog_experiment=True, capability_experiment=False, catalog_mode=mode, catalog_arm=mode,
               expected_native_sha256=STOCK,
               catalog_order=ORDER, catalog_candidate=metadata, option_name=name, option_type=TYPES[name],
               token_padded_bytes=metadata['padded_bytes'], positive_plaintext=metadata['positive_plaintext'],
               negative_plaintext=metadata['negative_plaintext'], seed_catalog=catalog,
               seed_files=[{'path': rel, 'sha256': sha(output / rel)} for rel in sorted(selected)],
               seed_options=[option_from_witness(output, item) for item in installed])
    (output / 'synthetic.toml').write_text(dump_config(cfg))
    manifest = {'schema_version': 'mho900-lab.option-catalog-preparation/1', 'source_run_id': source.name,
                'source_phase': 'install', 'mode': mode, 'candidate': name,
                'source_result_sha256': sha(source / 'result.toml'),
                'source_verification_sha256': sha(phase / 'trial-verification.toml'),
                'source_journal_sha256': sha(phase / 'guest-events.jsonl'),
                'source_config_sha256': sha(source / 'source/synthetic.toml'),
                'source_native_sha256': STOCK, 'source_apk_sha256': APK,
                'stock_native_unchanged': True, 'acquired_material': False, 'physical_contact': False}
    (output / 'catalog-preparation.toml').write_text(dump_config(manifest))
    verify_fixture(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_run', type=Path, nargs='?')
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('mode', choices=('negative48', 'positive'), nargs='?')
    parser.add_argument('candidate', choices=ORDER, nargs='?', default='BWU05T08')
    parser.add_argument('--verify-fixture', type=Path)
    args = parser.parse_args()
    if args.verify_fixture is not None:
        require(args.source_run is None and args.output is None and args.mode is None, 'Mixed invocation')
        cfg = verify_fixture(args.verify_fixture)
        print('verification = "accepted"\ncandidate = ' + json.dumps(cfg['option_name']))
    else:
        require(args.source_run is not None and args.output is not None and args.mode is not None,
                'Pass SOURCE_RUN OUT negative48|positive [CANDIDATE]')
        prepare(args.source_run, args.output, args.mode, args.candidate)
        print('preparation = "complete"\ncandidate = ' + json.dumps(args.candidate))


if __name__ == '__main__':
    main()
