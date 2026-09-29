#!/usr/bin/env python3
"""Reconcile native event witnesses with retained synthetic files, not success labels alone."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tomllib

CATALOG = {0: 'BND', 1: 'EMBD', 2: 'COMP', 3: 'AUTO', 4: 'AUTOA', 5: 'FlexA',
           6: 'AUDIOA', 7: 'AEROA', 19: 'RLU05', 30: 'AFG50', 29: 'AFG100',
           22: 'BWU03T05', 23: 'BWU03T08', 24: 'BWU05T08'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_records(data):
    require(8 <= len(data) < 1792, 'Private stream size outside contract')
    total, negative = struct.unpack_from('<ii', data)
    require(total == len(data) and negative == -total, 'Private stream header mismatch')
    cursor, records = 8, {}
    while cursor < total:
        require(cursor + 20 <= total, 'Truncated private record')
        ident, minus_ident, length, minus_length, crc = struct.unpack_from('<iiiiI', data, cursor)
        require(ident == -minus_ident and length == -minus_length and length > 0,
                'Private record pair mismatch')
        require(cursor + 20 + length <= total and ident not in records, 'Invalid private record bounds')
        records[ident] = data[cursor + 20:cursor + 20 + length]
        cursor += 20 + length
    require(cursor == total, 'Private record end mismatch')
    return records


def verify(root, config, phase):
    spec = importlib.util.spec_from_file_location('journal', Path(__file__).with_name('verify-entitlement-journal.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    events = module.records(root / 'guest-events.jsonl')
    result = module.validate(events, module.records(root / 'controller.stdout'), 'stock')
    require(result['terminal_delivered'] and result['terminal_acknowledged'], 'Terminal delivery incomplete')
    require(result['missing_delivery_records'] == 0, 'Not all durable events delivered')
    by_kind = lambda kind: [event for event in events if event['kind'] == kind]
    def one(kind):
        values = by_kind(kind)
        require(len(values) == 1, 'Expected one ' + kind)
        return values[0]
    terminal = one('dependency-stop')
    require(terminal['reason'] == 'entitlement-phase-complete' and terminal['phase'] == phase,
            'Wrong terminal or phase')
    require(terminal.get('physical_contact') is False, 'Physical boundary missing')
    require(terminal.get('persistence_backend') == 'stock-memfile-harness-directed-file', 'Wrong persistence model')
    require(all(value is True for value in terminal['expected_checks'].values()), 'Guest expectation failed')
    required_checks = {'started_false', 'catalog_complete'} | ({
        'reload_persisted', 'positive_license_file', 'key_matches_saved_witness', 'license_matches_saved_witness'
    } if phase == 'reload' else {'key_roundtrip', 'token_roundtrip', 'baseline_candidate_disabled'} | ({
        'negative_rejected', 'negative_no_license_file'
    } if phase == 'negative' else {'positive_accepted', 'positive_license_file'}))
    require(required_checks <= terminal['expected_checks'].keys(), 'Missing phase checks')
    for label in ('API_GetStarted:preflight', 'API_GetStarted:final'):
        returns = [x for x in by_kind('call-return') if x.get('function') == label]
        require(len(returns) == 1 and returns[0]['result'] in ('false', '0'), 'Started gate not false')
    directory = one('private-store-directory-preflight')
    require(all(directory[key] is True for key in ('directory_open', 'directory_fsync', 'directory_close'))
            and directory['flags'] == 0x84000, 'Directory persistence preflight failed')
    require(tomllib.loads((root / 'result.toml').read_text())['controller_exit'] == 0, 'Controller failed')
    health = (root / 'health-before.txt').read_bytes()
    require(health == (root / 'health-after.txt').read_bytes() and b'Enforcing' in health, 'Guest health changed')
    identity = one('synthetic-identity-confirmed')
    require(all(identity[name] == config[name] for name in ('model', 'serial', 'dna_hex')),
            'Synthetic identity differs from frozen fixture')
    require(identity['acquired_material'] is False, 'Acquired unit material present')
    capability = one('synthetic-model-capability')
    require(capability['model'] == 'MHO984' and capability['raw_bandwidth_enum'] == 17
            and capability['system_bandwidth_enum'] == 17, 'Stock model capability differs')
    require(one('synthetic-dna-response')['dna_hex'] == config['dna_hex'], 'DNA response differs')
    require(one('service-inventory-complete')['count'] == 49, 'Factory inventory incomplete')
    catalogs = by_kind('option-catalog')
    require(len(catalogs) == 2, 'Expected two catalog snapshots')
    state = {}
    for event in catalogs:
        require(event['phase'] == phase and event['checkpoint'] not in state, 'Catalog phase mismatch')
        values = event['options']
        require(len(values) == 14 and {x['option_type']: x['option_name'] for x in values} == CATALOG,
                'Catalog membership differs')
        require(all(x['status'] == 0 and type(x['valid']) is bool for x in values), 'Invalid stock query')
        state[event['checkpoint']] = {x['option_type']: x['valid'] for x in values}
        require(values == terminal['catalog_' + event['checkpoint']], 'Terminal catalog differs from witness')
    require(set(state) == {'before', 'after'}, 'Missing catalog checkpoint')
    before, after = state['before'], state['after']
    require(all(before[key] == after[key] for key in CATALOG if key != 5), 'Unrelated option changed')
    active = by_kind('stock-active-return')
    validators = by_kind('stock-verify-return')
    errors = [x['stock_code'] for x in by_kind('stock-sync-error')]
    notifications = by_kind('stock-result-notification')
    require(all(x['original_retained'] is True for x in notifications), 'Notification substitution')
    installs = by_kind('ordinary-installer-return')
    entries = [x for x in by_kind('call-enter') if x.get('function') == 'ApiLicense_SetLicenseInstall']
    require(len(installs) == len(entries) == (0 if phase == 'reload' else 1), 'Installer invocation count differs')
    rigol = root / 'after-rigol'
    files = sorted(p.relative_to(rigol).as_posix() for p in rigol.rglob('*') if p.is_file())
    expected_files = ['data/Key.data'] if phase == 'negative' else ['data/FlexA.lic', 'data/Key.data']
    require(files == expected_files, 'Unexpected synthetic filesystem files')
    key = (rigol / 'data/Key.data').read_bytes()
    require(len(key) == 40 and key != config['key_file_plaintext'].encode(), 'Invalid encrypted key file')
    witness = tomllib.loads((root / 'after-model/crypto-witness.toml').read_text())
    require(witness['phase'] == ('positive' if phase == 'reload' else phase), 'Crypto witness phase differs')
    require(bytes.fromhex(witness['key_ciphertext_hex']) == key, 'Retained key differs from crypto witness')
    if phase == 'reload':
        crypto = one('synthetic-persisted-inputs-read')
        require(crypto['crypto_regenerated'] is False and crypto['inputs_overwritten'] is False,
                'Reload regenerated its inputs')
        require(not by_kind('synthetic-crypto-roundtrip'), 'Reload executed crypto producer')
    else:
        crypto = one('synthetic-crypto-roundtrip')
        require(crypto['key_roundtrip'] and crypto['token_roundtrip'] and crypto['synthetic_only'],
                'Fresh crypto roundtrip missing')
        installer = one('ordinary-installer-enter')
        require(installer['token_hex'] == witness['token_ciphertext_hex'] and installer['option_type'] == 5,
                'Installer input differs from frozen witness')
    require(crypto['key_ciphertext_hex'] == witness['key_ciphertext_hex']
            and crypto['token_ciphertext_hex'] == witness['token_ciphertext_hex'], 'Crypto event/file mismatch')
    lic = None
    if phase == 'negative':
        require(not before[5] and not after[5], 'Negative option enabled')
        require(len(active) == 1 and active[0]['option_type'] == 5 and 24518 <= active[0]['result'] <= 24528,
                'Wrong rejection result')
        require(any(x['valid'] is False for x in validators) and not any(x['valid'] is True for x in validators),
                'Negative validator witness inconsistent')
        require(active[0]['result'] in errors and 24531 not in errors, 'Negative result notification differs')
    else:
        require(after[5] and before[5] == (phase == 'reload'), 'Positive/reload option state differs')
        require(any(x['valid'] is True for x in validators), 'Missing stock validation success')
        if phase == 'positive':
            require(len(active) == 1 and active[0]['option_type'] == 5 and active[0]['result'] == 24531,
                    'Stock activation did not succeed')
            require(24531 in errors and any(x['stock_code'] == 24531 for x in notifications),
                    'Missing success notification')
        else:
            require(not active and not entries, 'Reload reinstalled the option')
        lic = (rigol / 'data/FlexA.lic').read_bytes()
        token = lic.decode('ascii').strip().split('@')
        require(len(token) == 2 and token[0] == 'FlexA' and len(token[1]) == 64,
                'Stock license file format differs')
        bytes.fromhex(token[1])
        require(token[1] == witness['token_ciphertext_hex'], 'Stock license differs from submitted token')
    init = one('private-store-initialized')
    require(init['mode'] == ('reload' if phase == 'reload' else 'fresh'), 'Private store initialization differs')
    if phase == 'reload':
        require(init['roundtrip_exact'] and init['stock_crc_validation'], 'Reload stock decode not witnessed')
        require(not any(x.get('function') == 'private-store:CApiSetup.formatPrivateSetup' for x in events),
                'Reload formatted private storage')
    else:
        require(init['record_count'] == 0 and init['size'] == 8, 'Fresh private storage was not empty')
    snapshots = by_kind('private-store-snapshot')
    require(len(snapshots) == 2, 'Expected before/after private snapshots')
    snapshot_records = []
    for snap in snapshots:
        require(snap['fsync_completed'] and snap['readback_exact'], 'Private persistence incomplete')
        data = (root / 'after-model' / Path(snap['path']).name).read_bytes()
        records = private_records(data)
        require(len(data) == snap['size'] and len(records) == snap['record_count'], 'Snapshot size differs')
        require([{'id': key, 'length': len(value)} for key, value in records.items()] == snap['records'],
                'Private inventory differs from file')
        snapshot_records.append(records)
    canonical = (root / 'after-model/private.mem').read_bytes()
    require(canonical == (root / 'after-model' / Path(snapshots[-1]['path']).name).read_bytes(),
            'Canonical private bytes differ from final snapshot')
    private_before, private_after = snapshot_records
    counter_before = int.from_bytes(private_before.get(2336, b'\0' * 4), 'little')
    counter_after = int.from_bytes(private_after.get(2336, b'\0' * 4), 'little')
    return {'schema_version': 'mho900-lab.synthetic-entitlement-verification/1',
            'phase': phase, 'verification': 'accepted', 'journal_records': len(events),
            'option_before': before[5], 'option_after': after[5], 'ordinary_install_calls': len(entries),
            'key_sha256': digest(key), 'license_sha256': digest(lic) if lic is not None else '',
            'private_sha256': digest(canonical), 'counter_before': counter_before, 'counter_after': counter_after,
            'persistence': 'harness-directed-stock-MemFile', 'automatic_fram_persistence_proven': False,
            'physical_contact': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase_dir', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('--phase', choices=('negative', 'positive', 'reload'), required=True)
    args = parser.parse_args()
    for key, value in verify(args.phase_dir, tomllib.loads(args.config.read_text()), args.phase).items():
        print(f'{key} = {json.dumps(value)}')


if __name__ == '__main__':
    main()
