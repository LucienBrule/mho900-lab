#!/usr/bin/env python3
"""Validate retained Frida protocol JSONL, without inferring option installation."""
import argparse
import json
from pathlib import Path


def records(path):
    data = path.read_bytes()
    if not data or not data.endswith(b'\n'):
        raise ValueError(f"Incomplete or empty JSONL: {path.name}")
    values = [json.loads(line) for line in data.splitlines()]
    if not all(isinstance(value, dict) for value in values):
        raise ValueError("Every protocol record must be an object")
    return values


def control_terminal(value):
    try:
        expected = int(value.get('expected_pc', ''), 16)
        observed = int(value.get('observed_pc', ''), 16)
    except (ValueError, TypeError):
        return False
    return (value.get('kind') == 'dependency-stop'
            and value.get('reason') == 'fault-control-confirmed'
            and value.get('stage') == 'private-arm64-null-read'
            and value.get('context_verified') is True
            and value.get('memory_address') == '0x0'
            and value.get('memory_operation') == 'read'
            and value.get('exit_code') == 77
            and expected != 0 and expected == observed)


def art_terminal(value):
    return (value.get('kind') == 'dependency-stop'
            and value.get('reason') == 'art-readiness-confirmed'
            and value.get('stage') == 'stock-api-jni-readiness'
            and value.get('exit_code') == 77
            and value.get('java_vm_verified') is True
            and value.get('api_class_loaded') is True
            and value.get('stock_factory_called') is False
            and value.get('callback_substitution') is False
            and value.get('get_env_return') == 0
            and all(value.get(name) is True for name in (
                'environment_present', 'class_global_present', 'redraw_method_present', 'error_method_present')))


def validate(journal, host, expectation):
    if [record.get('sequence') for record in journal] != list(range(1, len(journal) + 1)):
        raise ValueError('Journal sequence must start at one and remain contiguous')
    positions = [i for i, record in enumerate(journal)
                 if record.get('kind') in ('dependency-stop', 'failure')]
    if len(positions) != 1:
        raise ValueError('Expected exactly one terminal record')
    terminal_position = positions[0]
    terminal = journal[terminal_position]
    for suffix in journal[terminal_position + 1:]:
        allowed = (suffix.get('kind') == 'terminal-acknowledged'
                   or (suffix.get('kind') == 'call-enter' and suffix.get('function') == 'libc._exit'))
        if not allowed:
            raise ValueError('Unexpected operation after terminal record')
    delivered = {}
    for item in host:
        if item.get('kind') != 'frida-message' or item.get('message', {}).get('type') != 'send':
            continue
        payload = item['message'].get('payload')
        if not isinstance(payload, dict):
            raise ValueError('Unexpected non-object guest payload')
        sequence = payload.get('sequence')
        if not isinstance(sequence, int) or not 1 <= sequence <= len(journal):
            raise ValueError('Delivered event missing from journal')
        if sequence in delivered:
            raise ValueError('Duplicate delivered sequence')
        if payload != journal[sequence - 1]:
            raise ValueError('Delivered event differs from durable journal')
        delivered[sequence] = payload
    terminal_delivered = terminal.get('sequence') in delivered
    acknowledged = any(item.get('kind') == 'terminal-acknowledged'
                       and item.get('sequence') == terminal.get('sequence') for item in host)
    verified_control = control_terminal(terminal)
    if expectation == 'control':
        if not verified_control or not terminal_delivered or not acknowledged:
            raise ValueError('Known-fault control requires matching context, delivered terminal and host ack')
    elif expectation == 'art-readiness':
        if not art_terminal(terminal) or not terminal_delivered or not acknowledged:
            raise ValueError('ART readiness requires real JNI witnesses, delivered terminal and host ack')
    elif terminal.get('reason') in ('fault-control-confirmed', 'art-readiness-confirmed'):
        raise ValueError('A private control cannot stand in for the stock diagnostic')
    return {
        'schema_version': 'mho900-lab.entitlement-journal-verification/1',
        'journal_validation': 'accepted',
        'expectation': expectation,
        'journal_records': len(journal),
        'delivered_records': len(delivered),
        'missing_delivery_records': len(journal) - len(delivered),
        'terminal_kind': terminal.get('kind'),
        'terminal_reason': terminal.get('reason', ''),
        'terminal_delivered': terminal_delivered,
        'terminal_acknowledged': acknowledged,
        'known_fault_control_verified': expectation == 'control' and verified_control,
        'art_readiness_verified': expectation == 'art-readiness' and art_terminal(terminal),
        'stock_failure_observed': terminal.get('kind') == 'failure',
        'stock_dependency_stop_observed': expectation == 'stock' and terminal.get('kind') == 'dependency-stop',
        'entitlement_success_claimed': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('journal', type=Path)
    parser.add_argument('controller', type=Path)
    parser.add_argument('--expect', required=True, choices=('control', 'stock', 'art-readiness'))
    args = parser.parse_args()
    for key, value in validate(records(args.journal), records(args.controller), args.expect).items():
        print(f'{key} = {json.dumps(value)}')


if __name__ == '__main__':
    main()
