#!/usr/bin/env python3
"""Verify cumulative synthetic option trials from native witnesses and retained bytes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tomllib

STOCK_SHA256 = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
CATALOG = {0: 'BND', 1: 'EMBD', 2: 'COMP', 3: 'AUTO', 4: 'AUTOA', 5: 'FlexA',
           6: 'AUDIOA', 7: 'AEROA', 19: 'RLU05', 30: 'AFG50', 29: 'AFG100',
           22: 'BWU03T05', 23: 'BWU03T08', 24: 'BWU05T08'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def helper(filename, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_map(directory):
    require(directory.is_dir(), 'Missing retained directory: ' + directory.name)
    result = {}
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), 'Evidence contains symlink')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = path.read_bytes()
        else:
            require(path.is_dir(), 'Evidence contains special file')
    return result


def validate_catalog(values):
    require(isinstance(values, list) and len(values) == 14
            and {item['option_type']: item['option_name'] for item in values} == CATALOG
            and all(type(item['valid']) is bool and type(item['status']) is int
                    and item['status'] == 0 for item in values), 'Invalid full option catalog')
    return {item['option_type']: item['valid'] for item in values}


def ciphertext(witness):
    text = witness['plaintext'].encode('ascii')
    padded = witness['padded_bytes']
    require(padded in (32, 48) and len(text) < padded, 'Unsupported padded plaintext')
    cipher = witness['token_ciphertext_hex']
    require(len(cipher) == padded * 2 and len(bytes.fromhex(cipher)) == padded,
            'Ciphertext length differs from padding')
    wire = ''.join(cipher[i + 1] + cipher[i] for i in range(0, len(cipher), 2))
    require(witness['wire_token_hex'] == wire, 'Incorrect low-nibble-first token representation')
    return cipher, wire, text.ljust(padded, b'\0').hex()


def verify_consumer(group, witness, cfg, valid):
    def one(kind):
        values = [event for event in group if event['kind'] == kind]
        require(len(values) == 1, 'Expected one consumer ' + kind)
        return values[0]
    entry, returned = one('consumer-verify-enter'), one('consumer-verify-return')
    require(entry['sequence'] < returned['sequence']
            and all(event['consumer_invocation'] == entry['consumer_invocation']
                    and event['thread_id'] == entry['thread_id']
                    and event['consumer_call'] == entry['consumer_call']
                    and event['option_type'] == entry['option_type']
                    and event.get('encoding') == 'conventional-byte-hex'
                    and event.get('observational_only') is True
                    and entry['sequence'] <= event['sequence'] <= returned['sequence'] for event in group),
            'Consumer invocation correlation differs')
    require(entry['option_type'] == witness['option_type'], 'Consumer option differs')
    cipher, _, plaintext = ciphertext(witness)
    decoded, key = one('consumer-hex-decoded'), one('consumer-aes-key')
    blocks = [event for event in group if event['kind'] == 'consumer-aes-block']
    count = witness['padded_bytes'] // 16
    require(decoded['ciphertext_hex'] == cipher and decoded['byte_count'] == witness['padded_bytes'],
            'Stock hex decoder bytes differ')
    require(key['bits'] == 256 and key['result'] == 0
            and key['key_hex'] == cfg['aes_key_ascii'].encode('ascii').hex(), 'Stock consumer AES key differs')
    require(len(blocks) == returned['decrypt_blocks'] == count
            and [event['block_index'] for event in blocks] == list(range(count))
            and all(event['byte_count'] == 16 and event['schedule_matches_key'] is True for event in blocks),
            'Stock AES block count or order differs')
    order = [entry['sequence'], decoded['sequence'], key['sequence']]
    order += [event['sequence'] for event in blocks] + [returned['sequence']]
    require(order == sorted(set(order)), 'Consumer crypto operation sequence differs')
    require(''.join(event['ciphertext_hex'] for event in blocks) == cipher
            and ''.join(event['plaintext_hex'] for event in blocks) == plaintext,
            'Actual stock decryption differs from declared fixture')
    require(returned['valid'] is valid, 'Stock consumer verdict differs')
    return entry['sequence'], returned['sequence']


def verify(root, cfg, phase):
    journal = helper('verify-entitlement-journal.py', 'catalog_journal')
    common = helper('verify-synthetic-entitlement.py', 'catalog_common')
    require(cfg.get('catalog_experiment') is True and cfg.get('physical_contact') is False
            and cfg.get('specimen_key_files_used') is False
            and cfg.get('stock_native_sha256') == STOCK_SHA256
            and cfg.get('token_text_encoding') == 'low-nibble-first'
            and cfg.get('consumer_observation_required') is True, 'Catalog fixture contract missing')
    candidate = cfg['catalog_candidate']
    candidate_id, candidate_name = candidate['type'], candidate['name']
    require(candidate_id in CATALOG and CATALOG[candidate_id] == candidate_name
            and candidate_id not in (0, 1, 2, 3, 5), 'Candidate is not an admitted nonbundle catalog option')
    require(cfg['option_type'] == candidate_id and cfg['option_name'] == candidate_name,
            'Top-level candidate fields disagree')
    baseline = validate_catalog(cfg['seed_catalog'])
    require(baseline[5] and not baseline[candidate_id], 'Seed is not FlexA-enabled/candidate-disabled')
    seed_options = cfg['seed_options']
    require(len({item['type'] for item in seed_options}) == len(seed_options)
            and any(item['type'] == 5 for item in seed_options), 'Seed option inventory is invalid')
    seed_witnesses = {}
    for item in seed_options:
        require(item['type'] in CATALOG and item['name'] == CATALOG[item['type']]
                and item['type'] != candidate_id and baseline[item['type']], 'Seed option catalog mismatch')
        witness = dict(item, option_type=item['type'], option_name=item['name'])
        ciphertext(witness)
        seed_witnesses[item['type']] = witness
    events = journal.records(root / 'guest-events.jsonl')
    reconciliation = journal.validate(events, journal.records(root / 'controller.stdout'), 'stock')
    require(reconciliation['terminal_delivered'] and reconciliation['terminal_acknowledged']
            and reconciliation['missing_delivery_records'] == 0, 'Incomplete durable journal delivery')
    by_kind = lambda kind: [event for event in events if event['kind'] == kind]
    def one(kind):
        values = by_kind(kind)
        require(len(values) == 1, 'Expected one ' + kind)
        return values[0]
    def bounds(label):
        starts = [event for event in by_kind('call-enter') if event.get('function') == label]
        ends = [event for event in by_kind('call-return') if event.get('function') == label]
        require(len(starts) == len(ends) == 1 and starts[0]['sequence'] < ends[0]['sequence'],
                'Missing actual call boundaries: ' + label)
        return starts[0]['sequence'], ends[0]['sequence']
    terminal = one('dependency-stop')
    require(terminal['reason'] == 'option-catalog-phase-complete' and terminal['phase'] == phase
            and terminal['exit_code'] == 77 and terminal.get('physical_contact') is False
            and terminal.get('persistence_backend') == 'stock-memfile-harness-directed-file',
            'Wrong terminal result')
    required_checks = {'started_false', 'catalog_complete', 'seed_catalog_matches', 'seed_inputs_preserved',
                       'private_reloaded', 'catalog_delta_exact', 'candidate_file_matches'}
    required_checks |= ({'reload_persisted', 'no_installer', 'no_token_regeneration'} if phase == 'reload'
                        else {'token_roundtrip', 'wire_codec_roundtrip', 'baseline_candidate_disabled'})
    if phase == 'negative':
        required_checks |= {'negative_rejected', 'negative_no_license_file'}
    elif phase == 'positive':
        required_checks |= {'positive_accepted', 'positive_license_file'}
    require(required_checks <= set(terminal['expected_checks'])
            and all(value is True for value in terminal['expected_checks'].values()), 'Guest checks failed')
    require(tomllib.loads((root / 'result.toml').read_text())['controller_exit'] == 0, 'Controller failed')
    require(digest((root / 'native-libscope-auklet.so').read_bytes()) == STOCK_SHA256,
            'Retained guest native library differs from stock')
    health = (root / 'health-before.txt').read_bytes()
    require(health == (root / 'health-after.txt').read_bytes() and b'Enforcing' in health, 'Guest health changed')
    for label in ('API_GetStarted:preflight', 'API_GetStarted:final'):
        returns = [event for event in by_kind('call-return') if event.get('function') == label]
        require(len(returns) == 1 and returns[0]['result'] in ('false', '0'), 'Started gate differs')
    identity = one('synthetic-identity-confirmed')
    require(all(identity[field] == cfg[field] for field in ('model', 'serial', 'dna_hex'))
            and identity['model'] == 'MHO984' and identity.get('acquired_material') is False,
            'Synthetic identity differs')
    require(one('service-inventory-complete')['count'] == 49, 'Factory inventory differs')
    require(one('synthetic-dna-response')['dna_hex'] == cfg['dna_hex'], 'DNA fixture differs')
    capability = one('synthetic-model-capability')
    require(capability['model'] == 'MHO984'
            and capability['raw_bandwidth_enum'] == capability['system_bandwidth_enum'] == 17,
            'Stock capability baseline differs')
    common.verify_capability(events, dict(cfg, capability_arm='stock', expected_bandwidth_enum=17,
                                         expected_record_offset='0x151b7a0'))
    catalogs = by_kind('option-catalog')
    require(len(catalogs) == 2 and [event['checkpoint'] for event in catalogs] == ['before', 'after'],
            'Catalog checkpoints differ')
    before, after = [validate_catalog(event['options']) for event in catalogs]
    expected_before = dict(baseline)
    expected_after = dict(baseline)
    if phase == 'reload':
        expected_before[candidate_id] = True
    if phase != 'negative':
        expected_after[candidate_id] = True
    require(before == expected_before and after == expected_after, 'Unexpected cumulative catalog change')
    for event in catalogs:
        require(event['phase'] == phase and event['options'] == terminal['catalog_' + event['checkpoint']],
                'Terminal catalog differs from actual query evidence')
        previous = 0
        for item in event['options']:
            label = 'GetLicenseValid:' + event['checkpoint'] + ':' + item['option_name']
            start, end = bounds(label)
            returned = [value for value in by_kind('call-return') if value.get('function') == label][0]
            require(previous < start < end < event['sequence'] and returned['result'] == '0',
                    'Catalog query lacks actual stock getter boundaries')
            previous = end

    before_rigol, after_rigol = file_map(root / 'before-rigol'), file_map(root / 'after-rigol')
    before_model, after_model = file_map(root / 'before-model'), file_map(root / 'after-model')
    expected_before_files = {'data/Key.data'} | {'data/' + item['name'] + '.lic' for item in seed_options}
    candidate_file = 'data/' + candidate_name + '.lic'
    if phase == 'reload':
        expected_before_files.add(candidate_file)
    expected_after_files = expected_before_files | ({candidate_file} if phase == 'positive' else set())
    require(set(before_rigol) == expected_before_files and set(after_rigol) == expected_after_files,
            'Unexpected seeded or resulting instrument files')
    require(all(after_rigol[path] == data for path, data in before_rigol.items()), 'Prior key/license bytes changed')
    seed_files = cfg['seed_files']
    require(len({item['path'] for item in seed_files}) == len(seed_files), 'Duplicate seed file path')
    for item in seed_files:
        path = item['path']
        require(path.startswith(('rigol/', 'model/')) and '..' not in Path(path).parts,
                'Invalid seed file path')
        directory, relative = path.split('/', 1)
        files = before_rigol if directory == 'rigol' else before_model
        require(relative in files, 'Seed file missing from before snapshot')
        if not (phase == 'reload' and path == 'model/private.mem'):
            require(digest(files[relative]) == item['sha256'], 'Seed file hash differs: ' + path)
    require(any(item['path'] == 'rigol/data/Key.data' for item in seed_files)
            and any(item['path'] == 'model/private.mem' for item in seed_files), 'Seed hashes incomplete')
    require(all(any(item['path'] == 'rigol/data/' + option['name'] + '.lic' for item in seed_files)
                for option in seed_options), 'Seed license hashes incomplete')
    seed_event = one('catalog-seed-inputs')
    require(seed_event['options'] == seed_options
            and seed_event['private_backend'] == 'stock-memfile-harness-directed-file', 'Seed event differs')
    expected_seed_event = []
    for item in seed_files:
        directory, relative = item['path'].split('/', 1)
        files = before_rigol if directory == 'rigol' else before_model
        expected_seed_event.append({'path': item['path'], 'size': len(files[relative]),
                                    'sha256_expected': item['sha256']})
    require(seed_event['files'] == expected_seed_event, 'Seed event file inventory differs')

    witness_name = 'crypto-' + candidate_name + ('-negative' if phase == 'negative' else '') + '.toml'
    witness = tomllib.loads(after_model[witness_name].decode())
    require(witness['schema_version'] == 3 and witness['phase'] == ('negative' if phase == 'negative' else 'positive')
            and witness['option_type'] == candidate_id and witness['option_name'] == candidate_name
            and witness['padded_bytes'] == candidate['padded_bytes']
            and witness['plaintext'] == candidate['negative_plaintext' if phase == 'negative' else 'positive_plaintext'],
            'Candidate witness differs from frozen fixture')
    cipher, wire, _ = ciphertext(witness)
    witness_event = one('catalog-candidate-witness')
    for field in ('phase', 'option_type', 'option_name', 'padded_bytes', 'plaintext', 'token_ciphertext_hex', 'wire_token_hex'):
        require(witness_event[field] == witness[field], 'Candidate event differs from retained witness')
    require(Path(witness_event['witness_path']).name == witness_name, 'Candidate witness path differs')
    for item in seed_options:
        fields = before_rigol['data/' + item['name'] + '.lic'].decode('ascii').strip().split('@')
        require(fields == [item['name'], item['wire_token_hex']], 'Seed license differs from declared token')
    if phase != 'negative':
        require(after_rigol[candidate_file].decode('ascii').strip().split('@') == [candidate_name, wire],
                'Candidate license differs from submitted token')

    installer_entries = [event for event in by_kind('call-enter')
                         if event.get('function') == 'ApiLicense_SetLicenseInstall']
    require(len(installer_entries) == (0 if phase == 'reload' else 1), 'Installer call count differs')
    active = by_kind('stock-active-return')
    if phase == 'reload':
        require(not active and not by_kind('ordinary-installer-enter') and not by_kind('ordinary-installer-return'),
                'Reload invoked installer')
        require(witness_name in before_model and before_model[witness_name] == after_model[witness_name]
                and witness_event.get('loaded') is True and witness_event.get('crypto_regenerated') is False,
                'Reload regenerated candidate witness')
        require(not by_kind('synthetic-crypto-roundtrip') and not by_kind('synthetic-wire-codec-control'),
                'Reload ran producer controls')
    else:
        lower, upper = bounds('ApiLicense_SetLicenseInstall')
        require(len(active) == 1 and active[0]['option_type'] == candidate_id
                and lower < active[0]['sequence'] < upper, 'Activation is not bound to actual installer')
        result = active[0]['result']
        require(result == (24527 if phase == 'negative' else 24531),
                'Actual activation result differs')
        require(any(event['stock_code'] == result and lower < event['sequence'] < upper
                    for event in by_kind('stock-sync-error')), 'Missing activation notification')
        entry = one('ordinary-installer-enter')
        require(entry['option_type'] == candidate_id and entry['wire_token_hex'] == wire
                and entry['token_ciphertext_hex'] == cipher, 'Actual installer token differs')
        producer = one('synthetic-crypto-roundtrip')
        require(producer['token_roundtrip'] is True and producer['wire_codec_roundtrip'] is True,
                'Producer controls missing')
        controls = by_kind('synthetic-wire-codec-control')
        require(len(controls) == 2, 'Expected two stock wire codec controls')
        directions = {event['input_encoding']: event for event in controls}
        require(set(directions) == {'conventional-high-first', 'stock-low-first'}, 'Codec control directions differ')
        for encoding, text, decoded, matches in (
                ('conventional-high-first', cipher, wire, False), ('stock-low-first', wire, cipher, True)):
            event = directions[encoding]
            require(event['input_text'] == text and event['decoded_hex'] == decoded
                    and event['decoded_length'] == witness['padded_bytes']
                    and event['expected_hex'] == cipher and event['matches_expected'] is matches
                    and event['predicted_decoded_hex'] == decoded and event['matches_prediction'] is True
                    and event['sequence'] < lower, 'Stock codec control differs from independent prediction')
        require(cipher != wire, 'Wire control is nondiscriminating')
    require(not any(event.get('function', '').startswith('CXXTEA::') for event in by_kind('call-enter')),
            'Catalog phase regenerated key material')
    if phase == 'reload':
        require(not any(event.get('function', '').startswith(('AES_encrypt:', 'AES_decrypt:roundtrip'))
                        or event.get('function') in ('AES_set_encrypt_key', 'AES_set_decrypt_key')
                        for event in by_kind('call-enter')), 'Reload invoked crypto producer')

    observer = one('consumer-observer-installed')
    require(observer.get('stock_call_sites_guarded') is True and observer.get('observational_only') is True
            and observer.get('physical_contact') is False and observer.get('acquired_material') is False,
            'Consumer observer contract missing')
    groups = {}
    consumer_kinds = {'consumer-verify-enter', 'consumer-verify-return', 'consumer-hex-decoded',
                      'consumer-aes-key', 'consumer-aes-block'}
    for event in events:
        if event['kind'] in consumer_kinds:
            groups.setdefault(event['consumer_invocation'], []).append(event)
    initialization = bounds('CApiLicense::init')
    expected_init = dict(seed_witnesses)
    if phase == 'reload':
        expected_init[candidate_id] = witness
    checked = set()
    init_ids = set()
    installer_consumers = 0
    for group in groups.values():
        starts = [event for event in group if event['kind'] == 'consumer-verify-enter']
        ends = [event for event in group if event['kind'] == 'consumer-verify-return']
        require(len(starts) == len(ends) == 1, 'Incomplete consumer invocation')
        start, end = starts[0], ends[0]
        if start['consumer_call'] == 'CApiLicense::init':
            require(initialization[0] < start['sequence'] < end['sequence'] < initialization[1],
                    'Consumer lies outside License.init')
            option = start['option_type']
            require(option in CATALOG and option not in init_ids, 'Unexpected or duplicate init consumer')
            init_ids.add(option)
            if option in expected_init:
                require(option not in checked, 'Duplicate seeded option validation')
                verify_consumer(group, expected_init[option], cfg, True)
                checked.add(option)
            else:
                require(len(group) == 2 and end['valid'] is False and end['decrypt_blocks'] == 0,
                        'Unexpected unseeded license validation')
        elif start['consumer_call'] == 'ApiLicense_SetLicenseInstall':
            require(phase != 'reload' and lower < start['sequence'] < end['sequence'] < upper,
                    'Unexpected installer consumer')
            verify_consumer(group, witness, cfg, phase != 'negative')
            installer_consumers += 1
        else:
            raise ValueError('Unexpected stock validation caller')
    require(init_ids == set(CATALOG) and checked == set(expected_init) and installer_consumers == (0 if phase == 'reload' else 1),
            'Not all prior and candidate stock consumers were verified')

    preflight = one('private-store-directory-preflight')
    require(preflight['flags'] == 0x84000 and all(preflight[field] is True
            for field in ('directory_open', 'directory_fsync', 'directory_close')), 'Private directory preflight failed')
    private_init = one('private-store-initialized')
    require(private_init['mode'] == 'reload' and private_init['roundtrip_exact'] is True
            and private_init['stock_crc_validation'] is True, 'Seeded private store was not stock-decoded')
    require(not any(event.get('function') == 'private-store:CApiSetup.formatPrivateSetup' for event in events),
            'Catalog phase formatted private storage')
    require(private_init['sequence'] < initialization[0], 'Private reload occurred after License.init')
    common.private_records(before_model['private.mem'])
    snapshots = by_kind('private-store-snapshot')
    require(len(snapshots) == 2, 'Private snapshots incomplete')
    snapshot_names = set()
    snapshot_records = []
    for event in snapshots:
        name = Path(event['path']).name
        snapshot_names.add(name)
        data = after_model[name]
        records = common.private_records(data)
        snapshot_records.append(records)
        require(event['fsync_completed'] is True and event['readback_exact'] is True
                and len(data) == event['size'] and len(records) == event['record_count']
                and [{'id': key, 'length': len(value)} for key, value in records.items()] == event['records'],
                'Private snapshot differs from file')
    private_before, private_after = snapshot_records
    private_changes = sorted(key for key in set(private_before) | set(private_after)
                             if private_before.get(key) != private_after.get(key))
    candidate_record = 2304 + candidate_id
    if phase == 'negative':
        require(candidate_record not in private_before and candidate_record in private_changes
                and set(private_changes) <= {candidate_record, 16192},
                'Rejection changed private state beyond candidate attempt and saved system time')
        payload = private_after[candidate_record]
        require(len(payload) == 4, 'Candidate attempt record width differs')
        word = int.from_bytes(payload, 'little')
        require((word & 0xffff) == 2160 and ((word >> 16) & 15) == 0 and (word >> 24) == 1,
                'Rejected candidate runtime/install/attempt fields differ')
        require(private_after.get(2337) == private_before.get(2337)
                and private_after.get(2336) == private_before.get(2336),
                'Rejection changed key backup or global installation count')
    require(after_model['private.mem'] == after_model[Path(snapshots[-1]['path']).name],
            'Canonical private state differs from final snapshot')
    require(all(after_model.get(path) == value for path, value in before_model.items() if path != 'private.mem'),
            'Prior model artifact changed')
    allowed_new = snapshot_names | ({witness_name} if phase != 'reload' else set())
    require(set(after_model) - set(before_model) == allowed_new, 'Unexpected model artifacts created')
    if phase == 'reload':
        require(all(after_model[name] == before_model['private.mem'] for name in snapshot_names | {'private.mem'}),
                'Reload changed private bytes')
    return {'schema_version': 'mho900-lab.option-catalog-verification/1', 'verification': 'accepted',
            'phase': phase, 'option_type': candidate_id, 'option_name': candidate_name,
            'option_before': before[candidate_id], 'option_after': after[candidate_id],
            'ordinary_install_calls': len(installer_entries), 'prior_consumers_verified': len(checked),
            'candidate_installer_consumers_verified': installer_consumers,
            'private_changed_record_ids': private_changes,
            'private_saved_time_before_hex': private_before.get(16192, b'').hex(),
            'private_saved_time_after_hex': private_after.get(16192, b'').hex(),
            'key_sha256': digest(after_rigol['data/Key.data']),
            'private_sha256': digest(after_model['private.mem']),
            'catalog_unchanged_except_candidate': True, 'stock_native_sha256': STOCK_SHA256,
            'raw_bandwidth_enum': 17, 'effective_bandwidth_enum': 17,
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
