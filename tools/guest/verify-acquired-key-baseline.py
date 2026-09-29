#!/usr/bin/env python3
"""Reconcile acquired guest outputs against private input bytes and raw journals."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tomllib


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    a = p.parse_args(); root = a.run
    cfg = tomllib.loads((root/'fixture/acquired.toml').read_text())
    assert cfg['schema_version'] == 2 and cfg['private_store'] == 'fresh-modeled'
    result = tomllib.loads((root/'result.toml').read_text())
    assert result['runner_exit'] == 0 and result['controller_exit'] == '0'
    assert result['trial_mode'] == 'acquired-baseline' and result['physical_contact'] is False
    journal = load('verify-entitlement-journal')
    events = journal.records(root/'guest-events.jsonl')
    host = journal.records(root/'controller.stdout')
    checked = journal.validate(events, host, 'stock')
    assert checked['missing_delivery_records'] == 0 and checked['terminal_acknowledged']
    assert checked['terminal_reason'] == 'acquired-key-baseline-complete'

    def one(kind):
        rows = [e for e in events if e['kind'] == kind]
        assert len(rows) == 1, kind
        return rows[0]
    output = one('acquired-key-outputs')
    assert output['key_length'] == 130 and output['key_hex'] == cfg['key_field_hex']
    assert output['left_field'] == cfg['key_left']
    observed = one('synthetic-identity-confirmed')
    assert observed['acquired_material'] is True
    assert observed['model'] == cfg['model'] and observed['serial'] == cfg['serial']
    assert observed['dna_hex'] == cfg['dna_hex'] and observed['file_keys_hex'] == cfg['file_keys_hex']
    init_enter = [e for e in events if e['kind'] == 'call-enter' and e.get('function') == 'CApiLicense::init']
    init_return = [e for e in events if e['kind'] == 'call-return' and e.get('function') == 'CApiLicense::init']
    assert len(init_enter) == len(init_return) == 1
    assert init_enter[0]['sequence'] < output['sequence'] < init_return[0]['sequence']
    assert not any(e['kind'] in ('stock-active-enter','ordinary-installer-enter','synthetic-crypto-roundtrip') for e in events)
    private = load('verify-synthetic-entitlement')
    options = one('option-catalog')['options']
    assert {o['option_type']:o['option_name'] for o in options} == private.CATALOG
    assert all(o['status'] == 0 and type(o['valid']) is bool for o in options)
    state = one('private-store-initialized')
    assert state['mode'] == 'fresh' and state['record_count'] == 0 and state['size'] == 8
    before = private.private_records((root/'after-model/private-acquired-before.mem').read_bytes())
    after = private.private_records((root/'after-model/private-acquired-after.mem').read_bytes())
    assert not before
    cipher = bytes.fromhex(cfg['key_ciphertext_hex'])
    key_records = [k for k,v in after.items() if v == cipher]
    assert len(key_records) == 1
    for phase in ('fixture','before-rigol','after-rigol'):
        path = root/(phase+'/rigol/data/Key.data' if phase == 'fixture' else phase+'/data/Key.data')
        assert path.read_bytes() == cipher
    assert not list((root/'after-rigol').rglob('*.lic'))
    for leaf in ('enforcing','system-server'):
        assert (root/f'initial-{leaf}.txt').read_bytes() == (root/f'final-{leaf}.txt').read_bytes()
    assert (root/'final-enforcing.txt').read_text().strip() == 'Enforcing'
    # Existing ART/Frida fixture limitation: enforcing persists, policy bytes change.
    # Require the exact previously retained pair, rather than accepting any delta.
    assert sha(root/'selinux-before.policy') == 'd42d4591e6a44551d969db387403b751aef0bb1bb0654f8e05ae7c9a10d224bc'
    assert sha(root/'selinux-after.policy') == '9fc3a821a681116e425f87b9a4eeb73f62b1e299e025709e6f566236761b2181'
    network = tomllib.loads((root/'network-control.toml').read_text())
    assert network['result'] == 'pass' and network['external_destination_contacted'] is False
    assert network['denied_other_loopback_tcp'] and network['denied_other_loopback_udp']
    assert network['fork_setsid_inheritance']
    assert sha(root/'guest-libs/libscope-auklet.so') == '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
    assert sha(root/'guest-art/stock.apk') == '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
    summary = dict(schema_version=1, verification='accepted', journal_records=len(events),
                   exact_key_outputs=True, key_file_preserved=True, empty_private_before=True,
                   key_private_record=key_records[0], private_record_ids=sorted(after),
                   enabled_options=[o['option_name'] for o in options if o['valid']],
                   physical_contact=False, specimen_options_unknown=True, persistence_tested=False,
                   guest_enforcing=True, guest_policy_bytes_changed=True,
                   known_frida_policy_pair=True)
    print(''.join(k+' = '+json.dumps(v)+'\n' for k,v in summary.items()), end='')


if __name__ == '__main__':
    main()
