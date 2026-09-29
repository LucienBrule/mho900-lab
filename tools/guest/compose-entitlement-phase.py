#!/usr/bin/env python3
"""Convert frozen TOML to the Frida JavaScript protocol boundary."""
import argparse
import json
from pathlib import Path
import tomllib


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path)
    parser.add_argument('template', type=Path)
    parser.add_argument('phase', choices=('negative', 'positive', 'reload'))
    parser.add_argument('output', type=Path)
    parser.add_argument('--checkpoint', choices=('negative', 'install', 'capability', 'process-reload', 'reboot-reload'))
    args = parser.parse_args()
    fixture = tomllib.loads(args.config.read_text())
    acquired = fixture.get('schema_version') == 'mho900-lab.acquired-option-fixture/1'
    if acquired and (fixture.get('acquired_option_experiment') is not True or args.phase not in ('positive','reload')):
        raise ValueError('Invalid acquired-input phase')
    if not acquired and fixture.get('schema_version') != 'mho900-lab.synthetic-entitlement-fixture/1':
        raise ValueError('Unknown fixture schema')
    if fixture.get('capability_experiment') is True and args.phase != 'reload':
        raise ValueError('Capability experiments only reload the verified seed')
    with args.output.open('x') as stream:
        stream.write('const entitlementFixture = ' + json.dumps(fixture, sort_keys=True) + ';\n')
        stream.write('const entitlementPhase = ' + json.dumps(args.phase) + ';\n')
        stream.write('const entitlementCheckpoint = ' + json.dumps(args.checkpoint or args.phase) + ';\n')
        stream.write(args.template.read_text())


if __name__ == '__main__':
    main()
