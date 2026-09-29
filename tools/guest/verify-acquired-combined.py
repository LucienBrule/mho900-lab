#!/usr/bin/env python3
"""Independently verify reload-only acquired all-options capability evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tomllib

sys.dont_write_bytecode = True
STOCK = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
DERIVED = '09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e'
APK = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
SOURCE_SEAL = '0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781'
ORDER = ['FlexA', 'BWU05T08', 'AFG100', 'AFG50', 'AUDIOA', 'AUTOA', 'AEROA',
         'RLU05', 'BWU03T05', 'BWU03T08']
PATCH_OFFSET = 0x42949c
ORIGINAL = bytes.fromhex('ea0740f94801088b0b1940b9e80f40f90b0100b9e81780b9287d089b4801088b')
REPLACEMENT = bytes.fromhex('1f010bf10bc102916801889aea0740f94801088b0b1940b9e90f40f92b0100b9')
POLICY_BEFORE = {'d42d4591e6a44551d969db387403b751aef0bb1bb0654f8e05ae7c9a10d224bc',
                 '9fc3a821a681116e425f87b9a4eeb73f62b1e299e025709e6f566236761b2181'}
POLICY_AFTER = '9fc3a821a681116e425f87b9a4eeb73f62b1e299e025709e6f566236761b2181'


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


def verify(root, cfg, phase):
    require(phase == 'reload' and cfg.get('schema_version') == 'mho900-lab.acquired-option-fixture/1'
            and cfg.get('acquired_combined_experiment') is True
            and cfg.get('acquired_option_experiment') is True and cfg.get('capability_experiment') is True
            and cfg.get('acquired_catalog_experiment') is not True
            and cfg.get('acquired_capability_experiment') is not True
            and cfg.get('physical_contact') is False and cfg.get('specimen_key_files_used') is True
            and cfg.get('source_combined_seal') == SOURCE_SEAL,
            'Not the admitted reload-only acquired combined profile')
    forbidden_cfg = {'catalog_candidate', 'catalog_arm', 'catalog_order', 'catalog_mode',
                     'option_type', 'option_name', 'positive_plaintext', 'negative_plaintext',
                     'token_padded_bytes'}
    require(not forbidden_cfg.intersection(cfg), 'Combined profile retains installer/candidate aliases')
    require(cfg.get('model') == 'MHO984' and cfg.get('license_type') == cfg.get('license_time') == 0
            and cfg.get('stock_native_sha256') == STOCK
            and cfg.get('token_text_encoding') == 'low-nibble-first'
            and cfg.get('consumer_observation_required') is True
            and cfg.get('installer_family') == 'MHO900', 'Acquired identity/license contract differs')
    require(len(bytes.fromhex(cfg['key_field_hex'])) == 130
            and cfg['aes_key_ascii'].encode('ascii') == bytes.fromhex(cfg['key_field_hex'])[:32]
            and len(bytes.fromhex(cfg['file_keys_hex'])) == 16
            and bool(cfg['key_left']) and bool(cfg['serial']), 'Acquired key semantics differ')
    arm = cfg.get('capability_arm')
    require(arm in ('stock', 'derived'), 'Unknown capability arm')
    expected_bw = 17 if arm == 'stock' else 18
    expected_pin = STOCK if arm == 'stock' else DERIVED
    expected_row = '0x151b7a0' if arm == 'stock' else '0x151b850'
    require(cfg.get('expected_native_sha256') == expected_pin
            and cfg.get('expected_bandwidth_enum') == expected_bw
            and cfg.get('expected_record_offset') == expected_row, 'Capability expectations differ')

    option = helper('verify-acquired-option.py', 'combined_option_helpers')
    common = helper('verify-synthetic-entitlement.py', 'combined_common')
    journal = helper('verify-entitlement-journal.py', 'combined_journal')
    seed_options = cfg['seed_options']
    require([item['name'] for item in seed_options] == ORDER
            and len({item['type'] for item in seed_options}) == 10, 'Not the complete ten-option seed')
    expected_types = {key for key in option.CATALOG if key not in (0, 1, 2, 3)}
    require({item['type'] for item in seed_options} == expected_types
            and all(option.CATALOG[item['type']] == item['name'] for item in seed_options),
            'Seed option names/types differ')
    baseline = option.validate_catalog(cfg['seed_catalog'])
    require({key for key, value in baseline.items() if value} == set(option.CATALOG) - {0},
            'Combined seed catalog is not thirteen true/BND false')
    witnesses = {}
    for item in seed_options:
        witness = dict(item, option_type=item['type'], option_name=item['name'])
        require(witness['padded_bytes'] == 48 and witness['plaintext'] ==
                cfg['model'] + '#' + cfg['serial'] + '#' + item['name'] + '#guest#0#0',
                'Seed witness identity/type/time differs')
        option.ciphertext(witness)
        witnesses[item['type']] = witness

    # The file copied from the guest is checked against both the fixed whole-file
    # digest and the original stock ancestor. This is independent of a JS assertion.
    root = Path(root)
    run = root.parents[1]
    fixture = run / 'fixture'
    ancestor = (fixture / 'ancestor/libscope-auklet.so').read_bytes()
    native = (root / 'native-libscope-auklet.so').read_bytes()
    require(digest(ancestor) == STOCK and ancestor[PATCH_OFFSET:PATCH_OFFSET + 32] == ORIGINAL,
            'Stock ancestor differs')
    wanted = ancestor if arm == 'stock' else (
        ancestor[:PATCH_OFFSET] + REPLACEMENT + ancestor[PATCH_OFFSET + 32:])
    require(native == wanted and digest(native) == expected_pin
            and native == (fixture / 'lib/libscope-auklet.so').read_bytes(),
            'Guest native bytes differ from exact admitted capability arm')
    changed_bytes = sum(left != right for left, right in zip(ancestor, native))
    require(changed_bytes == (0 if arm == 'stock' else 27), 'Native changed-byte count differs')
    require(digest((fixture / 'art/stock.apk').read_bytes()) == APK, 'Stock APK differs')

    events = journal.records(root / 'guest-events.jsonl')
    delivery = journal.validate(events, journal.records(root / 'controller.stdout'), 'stock')
    require(delivery['terminal_delivered'] and delivery['terminal_acknowledged']
            and delivery['missing_delivery_records'] == 0, 'Incomplete journal delivery')
    by_kind = lambda kind: [event for event in events if event['kind'] == kind]

    def one(kind):
        values = by_kind(kind)
        require(len(values) == 1, 'Expected one ' + kind)
        return values[0]

    def bounds(label):
        starts = [event for event in by_kind('call-enter') if event.get('function') == label]
        ends = [event for event in by_kind('call-return') if event.get('function') == label]
        require(len(starts) == len(ends) == 1 and starts[0]['sequence'] < ends[0]['sequence'],
                'Missing actual stock call: ' + label)
        return starts[0]['sequence'], ends[0]['sequence'], ends[0].get('result')

    terminal = one('dependency-stop')
    require(terminal.get('reason') == 'acquired-combined-phase-complete'
            and terminal.get('phase') == 'reload' and terminal.get('exit_code') == 77
            and terminal.get('acquired_combined_experiment') is True
            and terminal.get('physical_contact') is False
            and terminal.get('persistence_backend') == 'stock-memfile-harness-directed-file',
            'Wrong combined terminal')
    required_checks = {'started_false', 'catalog_complete', 'seed_catalog_matches', 'seed_inputs_preserved',
                       'private_reloaded', 'catalog_unchanged', 'no_installer', 'no_token_regeneration',
                       'capability_identity_preserved', 'capability_bandwidth_selected',
                       'capability_record_selected', 'capability_option_policy_preserved',
                       'capability_queries_succeeded'}
    require(required_checks <= set(terminal['expected_checks'])
            and all(value is True for value in terminal['expected_checks'].values()), 'Combined checks failed')
    evaluation = one('entitlement-phase-evaluation')
    require(all(evaluation.get(key) == terminal.get(key) for key in
                ('phase', 'acquired_combined_experiment', 'expected_checks', 'catalog_before',
                 'catalog_after', 'verify_returns', 'stock_codes', 'persistence_backend', 'physical_contact')),
            'Phase evaluation differs from terminal evidence')
    require(tomllib.loads((root / 'result.toml').read_text())['controller_exit'] == 0, 'Controller failed')
    before_health = (root / 'health-before.txt').read_bytes()
    require(before_health == (root / 'health-after.txt').read_bytes()
            and len(before_health.splitlines()) == 3
            and before_health.splitlines()[1].isdigit()
            and before_health.splitlines()[2] == b'Enforcing', 'Guest health changed or malformed')
    require(digest((root / 'policy-before.bin').read_bytes()) in POLICY_BEFORE
            and digest((root / 'policy-after.bin').read_bytes()) == POLICY_AFTER,
            'Guest policy outside exact established pair')

    for label in ('API_GetStarted:preflight', 'API_GetStarted:final'):
        require(bounds(label)[2] in ('false', '0'), 'Started lifecycle differs')
    identity = one('synthetic-identity-confirmed')
    require(all(identity[field] == cfg[field] for field in ('model', 'serial', 'dna_hex', 'file_keys_hex'))
            and identity.get('acquired_material') is True, 'Acquired identity witness differs')
    require(one('synthetic-dna-response')['dna_hex'] == cfg['dna_hex'], 'Modeled acquired DNA response differs')
    key_output = one('acquired-key-outputs')
    require(key_output['key_hex'] == cfg['key_field_hex'] and key_output['left_field'] == cfg['key_left'],
            'Original acquired key parser output differs')
    require(one('service-inventory-complete')['count'] == 49, 'Factory inventory differs')
    initial_capability = one('synthetic-model-capability')
    require(initial_capability['model'] == 'MHO984'
            and initial_capability['raw_bandwidth_enum'] == initial_capability['system_bandwidth_enum'] == expected_bw,
            'Initial cached bandwidth differs')
    capability_result = common.verify_capability(events, cfg)
    initialization = bounds('CApiLicense::init')
    require(initialization[0] < key_output['sequence'] < initialization[1], 'Key output outside original init')

    forbidden_events = ('ordinary-installer-enter', 'ordinary-installer-return', 'stock-active-enter',
                        'stock-active-return', 'synthetic-crypto-roundtrip', 'synthetic-wire-codec-control',
                        'catalog-candidate-witness')
    require(not any(by_kind(kind) for kind in forbidden_events), 'Reload used installer or producer events')
    for event in by_kind('call-enter'):
        label = event.get('function', '')
        require(not label.startswith(('CXXTEA::', 'AES_encrypt:', 'AES_decrypt:roundtrip',
                                      'open-write:', 'write:', 'ApiLicense_SetLicense'))
                and label not in ('AES_set_encrypt_key', 'AES_set_decrypt_key',
                                  'private-store:CApiSetup.formatPrivateSetup'),
                'Reload invoked an installer, producer or fixture rewrite')

    catalogs = by_kind('option-catalog')
    require(len(catalogs) == 2 and [event['checkpoint'] for event in catalogs] == ['before', 'after'],
            'Catalog checkpoints differ')
    for event in catalogs:
        require(event['phase'] == 'reload' and event['options'] == cfg['seed_catalog']
                and event['options'] == terminal['catalog_' + event['checkpoint']]
                and option.validate_catalog(event['options']) == baseline, 'Catalog changed')
        previous = initialization[1]
        for item in event['options']:
            start, end, status = bounds('GetLicenseValid:' + event['checkpoint'] + ':' + item['option_name'])
            require(previous < start < end < event['sequence'] and status == '0',
                    'Catalog value lacks an actual successful stock query')
            previous = end

    observer = one('consumer-observer-installed')
    require(observer.get('stock_call_sites_guarded') is True and observer.get('observational_only') is True
            and observer.get('physical_contact') is False and observer.get('acquired_material') is True,
            'Original consumer observation contract missing')
    kinds = {'consumer-verify-enter', 'consumer-verify-return', 'consumer-hex-decoded',
             'consumer-aes-key', 'consumer-aes-block'}
    groups = {}
    for event in events:
        if event['kind'] in kinds:
            groups.setdefault(event['consumer_invocation'], []).append(event)
    require(len(groups) == 14, 'Expected exactly fourteen original init consumers')
    seen, valid = set(), set()
    for group in groups.values():
        entries = [event for event in group if event['kind'] == 'consumer-verify-enter']
        returns = [event for event in group if event['kind'] == 'consumer-verify-return']
        require(len(entries) == len(returns) == 1, 'Incomplete consumer invocation')
        entry, returned = entries[0], returns[0]
        kind = entry['option_type']
        require(kind in option.CATALOG and kind not in seen and entry['consumer_call'] == 'CApiLicense::init'
                and initialization[0] < entry['sequence'] < returned['sequence'] < initialization[1],
                'Unexpected consumer scope/type')
        seen.add(kind)
        if kind in witnesses:
            option.verify_consumer(group, witnesses[kind], cfg, True)
            valid.add(kind)
        else:
            require(len(group) == 2 and returned['valid'] is False and returned['decrypt_blocks'] == 0
                    and all(event['consumer_call'] == 'CApiLicense::init'
                            and event['option_type'] == kind and event['thread_id'] == entry['thread_id']
                            and event.get('observational_only') is True
                            and event.get('encoding') == 'conventional-byte-hex' for event in group),
                    'Absent license did not retain original empty validation')
    require(seen == set(option.CATALOG) and valid == expected_types
            and len(by_kind('consumer-aes-block')) == 30, 'Incomplete ten-license original validation')

    before_rigol, after_rigol = option.file_map(root / 'before-rigol'), option.file_map(root / 'after-rigol')
    before_model, after_model = option.file_map(root / 'before-model'), option.file_map(root / 'after-model')
    rigol_names = {'data/Key.data'} | {'data/' + name + '.lic' for name in ORDER}
    model_names = {'private.mem'} | {'crypto-' + name + '.toml' for name in ORDER}
    seed_paths = {'rigol/' + name for name in rigol_names} | {'model/' + name for name in model_names}
    require(len(cfg['seed_files']) == 22 and {item['path'] for item in cfg['seed_files']} == seed_paths,
            'Seed inventory is not exactly twenty-two canonical files')
    require(set(before_rigol) == set(after_rigol) == rigol_names and before_rigol == after_rigol,
            'Key or license inventory/bytes changed')
    require(before_rigol['data/Key.data'].hex() == cfg['key_ciphertext_hex'], 'Acquired encrypted key differs')
    expected_seed_event = []
    for item in cfg['seed_files']:
        directory, relative = item['path'].split('/', 1)
        before = before_rigol if directory == 'rigol' else before_model
        after = after_rigol if directory == 'rigol' else after_model
        require(relative in before and before[relative] == after.get(relative)
                and digest(before[relative]) == item['sha256']
                and before[relative] == (fixture / item['path']).read_bytes(), 'Canonical seed bytes changed')
        expected_seed_event.append({'path': item['path'], 'size': len(before[relative]),
                                    'sha256_expected': item['sha256']})
    seed_event = one('catalog-seed-inputs')
    require(seed_event['options'] == seed_options and seed_event['files'] == expected_seed_event
            and seed_event['private_backend'] == 'stock-memfile-harness-directed-file', 'Seed event differs')
    for item in seed_options:
        saved = tomllib.loads(before_model['crypto-' + item['name'] + '.toml'].decode())
        require(saved['schema_version'] == 3 and saved['phase'] == 'positive', 'Seed witness is not positive')
        witness = witnesses[item['type']]
        require(all(saved[field] == witness[field] for field in
                    ('option_type', 'option_name', 'padded_bytes', 'plaintext', 'token_ciphertext_hex', 'wire_token_hex')),
                'Seed witness differs from retained token')
        require(before_rigol['data/' + item['name'] + '.lic'].decode('ascii').strip().split('@') ==
                [item['name'], witness['wire_token_hex']], 'Saved license differs from observed token')

    preflight = one('private-store-directory-preflight')
    require(preflight['flags'] == 0x84000 and all(preflight[field] is True
            for field in ('directory_open', 'directory_fsync', 'directory_close')), 'Private preflight failed')
    private_init = one('private-store-initialized')
    require(private_init['mode'] == 'reload' and private_init['roundtrip_exact'] is True
            and private_init['stock_crc_validation'] is True and private_init['sequence'] < initialization[0],
            'Private state was not decoded by stock before License.init')
    private = before_model['private.mem']
    records = common.private_records(private)
    require(set(records) == {2337, 16192} and records[2337] == bytes.fromhex(cfg['key_ciphertext_hex'])
            and len(records[16192]) == 8, 'Modeled permanent private state differs')
    snapshots = by_kind('private-store-snapshot')
    require(len(snapshots) == 2, 'Private snapshots incomplete')
    snapshot_names = set()
    for event in snapshots:
        name = Path(event['path']).name
        require(name not in snapshot_names and after_model[name] == private
                and event['fsync_completed'] is True and event['readback_exact'] is True
                and event['size'] == len(private) and event['record_count'] == len(records)
                and event['records'] == [{'id': key, 'length': len(value)} for key, value in records.items()],
                'Private snapshot differs from unchanged canonical state')
        snapshot_names.add(name)
    history = {'capability': [], 'process-reload': ['capability'],
               'reboot-reload': ['capability', 'process-reload']}
    require(root.name in history, 'Unknown combined checkpoint')
    prior_snapshots = {'private-' + label + '-' + suffix + '.mem'
                       for label in history[root.name] for suffix in ('before', 'after')}
    require(set(before_model) == model_names | prior_snapshots
            and all(before_model[name] == private for name in prior_snapshots), 'Unexpected prior model artifacts')
    require(snapshot_names == {'private-' + root.name + '-before.mem', 'private-' + root.name + '-after.mem'}
            and set(after_model) == set(before_model) | snapshot_names
            and all(after_model.get(name) == data for name, data in before_model.items()),
            'Reload changed model data or created unexpected files')
    return dict(schema_version='mho900-lab.acquired-combined-verification/1', verification='accepted',
                phase='reload', capability_arm=arm, initialized_consumers=14,
                valid_seed_consumers=10, consumer_aes_blocks=30, ordinary_install_calls=0,
                token_producer_calls=0, enabled_catalog_count=13, bundle_enabled=False,
                canonical_seed_files=22, all_seed_bytes_preserved=True, private_changed_record_ids=[],
                stock_ancestor_sha256=STOCK, observed_native_sha256=expected_pin,
                changed_native_bytes=changed_bytes, stock_apk_sha256=APK,
                public_model='MHO984', raw_bandwidth_enum=expected_bw, effective_bandwidth_enum=expected_bw,
                selected_record_offset=capability_result['selected_record_offset'],
                persistence='harness-directed-stock-MemFile', automatic_fram_persistence_proven=False,
                physical_contact=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('config', type=Path)
    parser.add_argument('--phase', choices=('reload',), required=True)
    args = parser.parse_args()
    result = verify(args.root, tomllib.loads(args.config.read_text()), args.phase)
    for key, value in result.items():
        print(key + ' = ' + json.dumps(value))


if __name__ == '__main__':
    main()
