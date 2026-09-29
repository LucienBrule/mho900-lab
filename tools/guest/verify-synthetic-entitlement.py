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



def verify_consumers(events, config, phase, cipher_hex, installer_bounds=None):
    """Check original consumer bytes and call nesting, independently of verdict labels."""
    observer = [event for event in events if event['kind'] == 'consumer-observer-installed']
    require(len(observer) == 1 and observer[0].get('stock_call_sites_guarded') is True
            and observer[0].get('observational_only') is True
            and observer[0].get('acquired_material') is False
            and observer[0].get('physical_contact') is False, 'Guarded consumer observer missing')
    relevant_call = 'CApiLicense::init' if phase == 'reload' else 'ApiLicense_SetLicenseInstall'
    groups = {}
    for event in events:
        if event['kind'] not in ('consumer-verify-enter', 'consumer-verify-return', 'consumer-hex-decoded',
                                 'consumer-aes-key', 'consumer-aes-block'):
            continue
        require(event.get('observational_only') is True
                and event.get('encoding') == 'conventional-byte-hex', 'Nonobservational consumer event')
        ident = event['consumer_invocation']
        require(type(ident) is int and ident > 0, 'Invalid consumer invocation')
        groups.setdefault(ident, []).append(event)
    selected = []
    for group in groups.values():
        enters = [event for event in group if event['kind'] == 'consumer-verify-enter']
        returns = [event for event in group if event['kind'] == 'consumer-verify-return']
        require(len(enters) == len(returns) == 1, 'Incomplete consumer invocation')
        entry, returned = enters[0], returns[0]
        require(entry['sequence'] < returned['sequence'], 'Consumer return before entry')
        require(all(event['thread_id'] == entry['thread_id']
                    and event['consumer_call'] == entry['consumer_call']
                    and event['option_type'] == entry['option_type']
                    and entry['sequence'] <= event['sequence'] <= returned['sequence'] for event in group),
                'Consumer invocation fields or bounds differ')
        if entry['consumer_call'] == relevant_call and entry['option_type'] == config['option_type']:
            selected.append((group, entry, returned))
    require(len(selected) == 1, 'Expected exactly one target stock consumer invocation')
    group, entry, returned = selected[0]
    if installer_bounds is None:
        starts = [event for event in events if event['kind'] == 'call-enter'
                  and event.get('function') == relevant_call]
        ends = [event for event in events if event['kind'] == 'call-return'
                and event.get('function') == relevant_call]
        require(len(starts) == len(ends) == 1, 'Missing initialization bounds')
        lower, upper = starts[0]['sequence'], ends[0]['sequence']
    else:
        lower, upper = installer_bounds
    require(lower < entry['sequence'] < returned['sequence'] < upper,
            'Consumer is outside the actual stock call')
    def one(kind):
        values = [event for event in group if event['kind'] == kind]
        require(len(values) == 1, 'Expected one target ' + kind)
        return values[0]
    decoded, aes_key = one('consumer-hex-decoded'), one('consumer-aes-key')
    blocks = [event for event in group if event['kind'] == 'consumer-aes-block']
    require(decoded['byte_count'] == 32 and decoded['ciphertext_hex'] == cipher_hex,
            'Stock decoder consumed bytes other than producer AES ciphertext')
    require(aes_key['bits'] == 256 and aes_key['result'] == 0
            and aes_key['key_hex'] == config['aes_key_ascii'].encode('ascii').hex(),
            'Actual stock consumer key differs from declared synthetic key')
    require(len(blocks) == returned['decrypt_blocks'] == 2
            and [event['block_index'] for event in blocks] == [0, 1], 'Stock AES block count/order differs')
    require(all(event['byte_count'] == 16 and event['schedule_matches_key'] is True for event in blocks),
            'Stock AES schedule/block mismatch')
    require(entry['sequence'] < decoded['sequence'] < aes_key['sequence']
            < blocks[0]['sequence'] < blocks[1]['sequence'] < returned['sequence'],
            'Stock consumer operation ordering differs')
    require(''.join(event['ciphertext_hex'] for event in blocks) == cipher_hex,
            'Actual AES input differs from decoded producer ciphertext')
    plain = config['negative_plaintext' if phase == 'negative' else 'positive_plaintext'].encode('ascii')
    require(len(plain) <= config['token_padded_bytes'] == 32, 'Unexpected fixture plaintext length')
    padded = plain.ljust(32, b'\0')
    require(''.join(event['plaintext_hex'] for event in blocks) == padded.hex(),
            'Actual stock decrypted plaintext differs from declared fixture')
    require(returned['valid'] is (phase != 'negative'), 'Actual stock consumer verdict differs')
    return len(selected)


def verify_capability(events, config):
    """Bind selected row and real cached-state getter calls to one stock policy call."""
    arm = config['capability_arm']
    expected = config['expected_bandwidth_enum']
    offset = config['expected_record_offset']

    def one(kind):
        values = [event for event in events if event['kind'] == kind]
        require(len(values) == 1, 'Expected exactly one ' + kind)
        return values[0]

    def call_bounds(label, expected_result):
        starts = [event for event in events if event['kind'] == 'call-enter'
                  and event.get('function') == label]
        ends = [event for event in events if event['kind'] == 'call-return'
                and event.get('function') == label]
        require(len(starts) == len(ends) == 1
                and starts[0]['sequence'] < ends[0]['sequence']
                and ends[0]['result'] == expected_result, 'Missing or failed stock call: ' + label)
        return starts[0]['sequence'], ends[0]['sequence']

    parser = one('capability-parser-return')
    selected = one('capability-selected-record')
    require(parser.get('behavior_replaced') is False
            and parser.get('return_value_copied') is True
            and parser['observed_in'] == 'ApiUtility_SetModel'
            and parser['arm'] == selected['arm'] == arm
            and parser['selected_record_offset'] == selected['selected_record_offset'] == offset,
            'Capability selection lacks original parser witness')
    require(selected['selected_record_name'] == ('MHO984' if arm == 'stock' else 'MHO984D')
            and selected['selected_record_bandwidth_enum'] == expected
            and selected['channels'] == 4 and selected['domain'] == 8 and selected['series'] == 900,
            'Selected capability record differs from recovered contract')
    setter_entries = [event for event in events if event['kind'] == 'call-enter'
                      and event.get('function') == 'ApiUtility_SetModel']
    setter_returns = [event for event in events if event['kind'] == 'call-return'
                      and event.get('function') == 'ApiUtility_SetModel']
    require(len(setter_entries) == len(setter_returns) == 1
            and setter_entries[0]['sequence'] < parser['sequence'] < setter_returns[0]['sequence']
            < selected['sequence'], 'Parser observation lies outside actual model setter')
    observations = [event for event in events if event['kind'] == 'capability-observation']
    require(len(observations) == 2
            and [event['stage'] for event in observations]
                == ['before-option-policy', 'after-option-policy'], 'Capability getter checkpoints differ')
    for event in observations:
        require(event['arm'] == arm and event['model'] == 'MHO984'
                and event['raw_bandwidth_enum'] == event['effective_bandwidth_enum'] == expected
                and event['selected_record_offset'] == offset
                and event['model_status'] == event['raw_status'] == event['effective_status'] == 0,
                'Stock capability getter output differs')
        previous_return = selected['sequence']
        for name in ('GetModel', 'GetModelBw', 'GetBw'):
            start, end = call_bounds('capability:' + name + ':' + event['stage'], '0')
            require(previous_return < start < end < event['sequence'],
                    'Capability getter order differs from actual query checkpoint')
            previous_return = end
    policy_enter = one('capability-option-policy-enter')
    policy_return = one('capability-option-policy-return')
    parse_start, parse_end = call_bounds('capability:ApiUtility_ParseOption', None)
    require(policy_enter['arm'] == policy_return['arm'] == arm
            and policy_enter.get('actual_stock') is True and policy_return.get('returned') is True
            and policy_return.get('return_type') == 'void'
            and observations[0]['sequence'] < policy_enter['sequence'] < parse_start < parse_end
            < policy_return['sequence'] < observations[1]['sequence'],
            'Actual stock option-policy call not bounded by getter observations')
    for name in ('GetModel', 'GetModelBw', 'GetBw'):
        require(call_bounds('capability:' + name + ':before-option-policy', '0')[1]
                < policy_enter['sequence']
                and call_bounds('capability:' + name + ':after-option-policy', '0')[0]
                > policy_return['sequence'], 'Getter executed on wrong side of option policy')
    evaluation = one('capability-evaluation')
    require(evaluation['arm'] == arm
            and evaluation['before'] == {key: value for key, value in observations[0].items()
                                         if key not in ('kind', 'sequence', 'call')}
            and evaluation['after'] == {key: value for key, value in observations[1].items()
                                        if key not in ('kind', 'sequence', 'call')}
            and all(value is True for value in evaluation['expected_checks'].values()),
            'Capability evaluation differs from getter evidence')
    required_guards = {'0x429cbc', '0x429b40', '0x429b10', '0x429b70'}
    require(required_guards <= {event.get('elf_va') for event in events
                                if event['kind'] == 'stock-helper-verified'},
            'Stock getter/policy instruction guards missing')
    return {'capability_experiment': True, 'capability_arm': arm,
            'selected_record_offset': offset, 'selected_record_name': selected['selected_record_name'],
            'raw_bandwidth_enum': expected, 'effective_bandwidth_enum': expected,
            'identity_preserved': True, 'option_policy_executed': True,
            'seed_bytes_preserved': True, 'seed_catalog_preserved': True}


def verify(root, config, phase):
    capability_mode = config.get('capability_experiment') is True
    expected_bandwidth = 17
    if capability_mode:
        arm = config.get('capability_arm')
        require(phase == 'reload' and arm in ('stock', 'derived'), 'Capability trial must reload one known arm')
        expected_bandwidth, expected_record = {
            'stock': (17, '0x151b7a0'), 'derived': (18, '0x151b850')
        }[arm]
        require(config.get('model') == 'MHO984'
                and config.get('expected_bandwidth_enum') == expected_bandwidth
                and config.get('expected_record_offset') == expected_record
                and config.get('expected_native_sha256') == {
                    'stock': '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e',
                    'derived': '09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e'
                }[arm],
                'Capability arm expectation differs from recovered contract')
    spec = importlib.util.spec_from_file_location('journal', Path(__file__).with_name('verify-entitlement-journal.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    events = module.records(root / 'guest-events.jsonl')
    result = module.validate(events, module.records(root / 'controller.stdout'), 'stock')
    require(config.get('token_text_encoding') == 'low-nibble-first'
            and config.get('consumer_observation_required') is True, 'Wire fixture contract missing')
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
    } if phase == 'reload' else {'key_roundtrip', 'token_roundtrip', 'wire_codec_roundtrip', 'baseline_candidate_disabled'} | ({
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
    require(capability['model'] == 'MHO984' and capability['raw_bandwidth_enum'] == expected_bandwidth
            and capability['system_bandwidth_enum'] == expected_bandwidth, 'Model capability differs')
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
    if capability_mode:
        seed_catalog = config.get('seed_catalog')
        require(isinstance(seed_catalog, list) and len(seed_catalog) == 14,
                'Capability seed lacks full catalog')
        require({item['option_type']: item['option_name'] for item in seed_catalog} == CATALOG
                and all(type(item['valid']) is bool and item['status'] == 0 for item in seed_catalog),
                'Capability seed catalog is invalid')
        require(all(event['options'] == seed_catalog for event in catalogs),
                'Capability arm changed saved positive catalog')
    active = by_kind('stock-active-return')
    validators = by_kind('stock-verify-return')
    errors = [x['stock_code'] for x in by_kind('stock-sync-error')]
    notifications = by_kind('stock-result-notification')
    require(all(x['original_retained'] is True for x in notifications), 'Notification substitution')
    installs = by_kind('ordinary-installer-return')
    entries = [x for x in by_kind('call-enter') if x.get('function') == 'ApiLicense_SetLicenseInstall']
    require(len(installs) == len(entries) == (0 if phase == 'reload' else 1), 'Installer invocation count differs')
    installer_returns = [x for x in by_kind('call-return') if x.get('function') == 'ApiLicense_SetLicenseInstall']
    require(len(installer_returns) == len(entries), 'Installer return count differs')
    if phase != 'reload':
        install_start, install_end = entries[0]['sequence'], installer_returns[0]['sequence']
        require(install_start < install_end, 'Installer boundaries reversed')
        validators = [x for x in validators if install_start < x['sequence'] < install_end]
        active = [x for x in active if install_start < x['sequence'] < install_end]
        require(validators, 'No stock validator return within actual installer')
    else:
        require(not by_kind('ordinary-installer-enter'), 'Reload emitted installer entry')
    rigol = root / 'after-rigol'
    files = sorted(p.relative_to(rigol).as_posix() for p in rigol.rglob('*') if p.is_file())
    expected_files = ['data/Key.data'] if phase == 'negative' else ['data/FlexA.lic', 'data/Key.data']
    require(files == expected_files, 'Unexpected synthetic filesystem files')
    key = (rigol / 'data/Key.data').read_bytes()
    require(len(key) == 40 and key != config['key_file_plaintext'].encode(), 'Invalid encrypted key file')
    witness = tomllib.loads((root / 'after-model/crypto-witness.toml').read_text())
    require(witness['schema_version'] == 2, 'Expected explicit wire/cipher witness schema')
    require(witness['phase'] == ('positive' if phase == 'reload' else phase), 'Crypto witness phase differs')
    require(bytes.fromhex(witness['key_ciphertext_hex']) == key, 'Retained key differs from crypto witness')
    cipher_hex = witness['token_ciphertext_hex']
    wire_hex = witness['wire_token_hex']
    require(len(cipher_hex) == 64 and len(bytes.fromhex(cipher_hex)) == 32, 'Wrong AES ciphertext length')
    swapped_hex = ''.join(cipher_hex[i + 1] + cipher_hex[i] for i in range(0, len(cipher_hex), 2))
    require(wire_hex == swapped_hex, 'Wire token is not low-nibble-first encoding')
    controls = by_kind('synthetic-wire-codec-control')
    if phase == 'reload':
        require(not controls, 'Reload ran producer codec controls')
        crypto = one('synthetic-persisted-inputs-read')
        require(crypto['crypto_regenerated'] is False and crypto['inputs_overwritten'] is False,
                'Reload regenerated its inputs')
        require(not by_kind('synthetic-crypto-roundtrip'), 'Reload executed crypto producer')
        require(not any(event.get('function', '').startswith(('CXXTEA::', 'AES_encrypt:', 'AES_decrypt:roundtrip'))
                        or event.get('function') in ('AES_set_encrypt_key', 'AES_set_decrypt_key')
                        for event in by_kind('call-enter')), 'Reload invoked producer/roundtrip calls')
    else:
        crypto = one('synthetic-crypto-roundtrip')
        require(crypto['key_roundtrip'] is True and crypto['token_roundtrip'] is True
                and crypto['wire_codec_roundtrip'] is True and crypto['synthetic_only'] is True,
                'Fresh crypto roundtrip missing')
        installer = one('ordinary-installer-enter')
        require(installer['token_hex'] == installer['wire_token_hex'] == wire_hex
                and installer['token_ciphertext_hex'] == cipher_hex and installer['option_type'] == 5,
                'Installer input differs from frozen witness')
        require(len(controls) == 2, 'Expected exactly two stock decoder controls')
        control_map = {item['input_encoding']: item for item in controls}
        require(set(control_map) == {'conventional-high-first', 'stock-low-first'}, 'Missing codec control direction')
        for encoding, input_text, decoded_hex, matches in (
                ('conventional-high-first', cipher_hex, swapped_hex, False),
                ('stock-low-first', wire_hex, cipher_hex, True)):
            item = control_map[encoding]
            require(item['input_text'] == input_text and item['decoded_hex'] == decoded_hex
                    and item['decoded_length'] == 32 and item['expected_hex'] == cipher_hex
                    and item['matches_expected'] is matches and item['matches_prediction'] is True
                    and item['predicted_decoded_hex'] == decoded_hex,
                    'Stock wire codec control does not match independent nibble calculation')
            require(item['sequence'] < installer['sequence'], 'Decoder control ran after installer')
        require(cipher_hex != swapped_hex, 'Conventional decoder control is not discriminating')
    consumer_count = verify_consumers(events, config, phase, cipher_hex,
                                      None if phase == 'reload' else (install_start, install_end))
    require(crypto['key_ciphertext_hex'] == witness['key_ciphertext_hex']
            and crypto['token_ciphertext_hex'] == cipher_hex and crypto['wire_token_hex'] == wire_hex,
            'Crypto event/file mismatch')
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
        require(token[1] == wire_hex, 'Stock license differs from submitted wire token')
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
    capability_result = {}
    if capability_mode:
        require(digest(key) == config.get('seed_key_sha256')
                and lic is not None and digest(lic) == config.get('seed_license_sha256')
                and digest(canonical) == config.get('seed_private_sha256')
                and digest((root / 'after-model/crypto-witness.toml').read_bytes())
                    == config.get('seed_crypto_witness_sha256'),
                'Capability arm changed seeded key/license/private/crypto bytes')
        require(all(digest((root / 'after-model' / Path(snap['path']).name).read_bytes())
                    == config['seed_private_sha256'] for snap in snapshots),
                'Capability private before/after differ from seed')
        capability_result = verify_capability(events, config)
    return {'schema_version': 'mho900-lab.synthetic-entitlement-verification/1',
            'phase': phase, 'verification': 'accepted', 'journal_records': len(events),
            'actual_consumer_invocations_verified': consumer_count,
            'option_before': before[5], 'option_after': after[5], 'ordinary_install_calls': len(entries),
            'key_sha256': digest(key), 'license_sha256': digest(lic) if lic is not None else '',
            'private_sha256': digest(canonical), 'counter_before': counter_before, 'counter_after': counter_after,
            'persistence': 'harness-directed-stock-MemFile', 'automatic_fram_persistence_proven': False,
            'physical_contact': False, **capability_result}


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
