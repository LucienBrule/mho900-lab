#!/usr/bin/env python3
"""Host-only completion classification controls using retained guest journals."""
import argparse
import ast
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('combined_journal', type=Path)
    parser.add_argument('catalog_journal', type=Path)
    args = parser.parse_args()
    # Compile only the pure classifier: importing Frida is unnecessary for this control.
    source = Path(__file__).with_name('entitlement-controller.py')
    tree = ast.parse(source.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'accepted_stop')
    namespace = {'os': os, 'STOCK_STOPS': set()}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
    accepted = namespace['accepted_stop']

    def terminal(path):
        values = [json.loads(line) for line in path.read_text().splitlines()]
        stops = [item for item in values if item.get('kind') == 'dependency-stop']
        assert len(stops) == 1
        return stops[0]

    original = terminal(args.combined_journal)
    prior = terminal(args.catalog_journal)
    with patch.dict(os.environ, {'ENTITLEMENT_PHASE': 'reload'}):
        assert accepted(original) and accepted(prior)
        mutations = [
            lambda p: p['expected_checks'].pop('no_installer'),
            lambda p: p['expected_checks'].update(no_installer=False),
            lambda p: p.update(phase='positive'),
            lambda p: p['catalog_after'][0].update(valid=True),
            lambda p: p.update(terminal_ack=False),
            lambda p: p.update(physical_contact=True),
            lambda p: p.update(acquired_combined_experiment=False),
            lambda p: p.update(exit_code=78),
            lambda p: p.update(kind='failure'),
            lambda p: p.update(reason='unrecognized-completion'),
            lambda p: p['catalog_before'][1].update(option_type=0),
        ]
        for mutate in mutations:
            value = copy.deepcopy(original)
            mutate(value)
            assert not accepted(value), 'Invalid terminal was accepted'
        with patch.dict(os.environ, {'ENTITLEMENT_PHASE': 'positive'}):
            assert not accepted(original)
    print('accepted_controls = 2')
    print('rejected_controls = 12')
    print('physical_contact = false')


if __name__ == '__main__':
    main()
