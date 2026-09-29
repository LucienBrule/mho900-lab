#!/usr/bin/env python3
"""Verify the stock-only stale saved-time contrast against sealed control inputs."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tomllib

sys.dont_write_bytecode = True
SOURCE_SEAL = '0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781'
CONTROL_SEAL = '7ffb39a50f36e97c9fce32e72869b7d3698b2aa869fbb83d10992a061c36101f'
CONTROL_CONFIG = '6069133e1d2dff43a8fa6b98966087117782ad26b507741c8e6b7d7f72d0ed41'
OLDER_PRIVATE = '9e211b2fcab8245472c6bd9da85826a4bd2d28d27fe77347518b5d5da7d9eede'
LATER_PRIVATE = 'b13d38eb634fcdb2b64afdb323da5445ca416e22fb2cdf3918bfcea0d3481490'
CONTROL_TEMPLATE = '67dbbf4218f0441ecb76987db54b6023481c31e0266f400040baed82c6667199'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def helper(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(root, cfg, phase):
    require(phase == 'reload' and cfg.get('acquired_stale_private_experiment') is True
            and cfg.get('capability_arm') == 'stock'
            and cfg.get('source_combined_seal') == SOURCE_SEAL
            and cfg.get('source_stock_control_seal') == CONTROL_SEAL
            and cfg.get('stale_private_before_sha256') == OLDER_PRIVATE
            and cfg.get('stale_private_after_sha256') == LATER_PRIVATE,
            'Not the admitted stock-only stale private-state contrast')
    root = Path(root)
    require(root.name == 'capability', 'Stale private contrast permits one reload checkpoint')
    fixture = root.parents[1] / 'fixture'
    provenance = fixture / 'provenance'
    require({p.name for p in provenance.iterdir()} == {'stock-control.toml', 'postinstall-private.mem'}
            and all(p.is_file() and not p.is_symlink() for p in provenance.iterdir()),
            'Unexpected stale private provenance inventory')
    control_bytes = (provenance / 'stock-control.toml').read_bytes()
    require(sha(control_bytes) == CONTROL_CONFIG, 'Accepted stock control configuration differs')
    control = tomllib.loads(control_bytes.decode())
    require(control['source_combined_seal'] == SOURCE_SEAL and control['capability_arm'] == 'stock',
            'Pinned control lineage differs')
    expected = copy.deepcopy(control)
    expected.update(acquired_stale_private_experiment=True, source_stock_control_seal=CONTROL_SEAL,
                    stale_private_before_sha256=OLDER_PRIVATE, stale_private_after_sha256=LATER_PRIVATE)
    targets = [item for item in expected['seed_files'] if item['path'] == 'model/private.mem']
    require(len(targets) == 1 and targets[0]['sha256'] == LATER_PRIVATE,
            'Control private seed pin differs')
    targets[0]['sha256'] = OLDER_PRIVATE
    require(cfg == expected, 'Contrast changed configuration beyond the admitted private seed/provenance')
    require(tomllib.loads((fixture / 'synthetic.toml').read_text()) == cfg
            and tomllib.loads((root.parents[1] / 'source/synthetic.toml').read_text()) == cfg,
            'Frozen fixture/source configuration differs')
    require(sha((fixture / 'template.js').read_bytes()) == CONTROL_TEMPLATE,
            'Native experiment template differs from accepted stock control')

    older = (fixture / 'model/private.mem').read_bytes()
    later = (provenance / 'postinstall-private.mem').read_bytes()
    require(sha(older) == OLDER_PRIVATE and sha(later) == LATER_PRIVATE,
            'Private streams differ from independently pinned source snapshots')
    common = helper('verify-synthetic-entitlement')
    old_records, new_records = common.private_records(older), common.private_records(later)
    require(set(old_records) == set(new_records) == {2337, 16192}
            and old_records[2337] == new_records[2337] == bytes.fromhex(cfg['key_ciphertext_hex'])
            and len(old_records[16192]) == len(new_records[16192]) == 8
            and [key for key in old_records if old_records[key] != new_records[key]] == [16192],
            'Source contrast exceeds the sole saved-time record difference')
    require(len(control['seed_files']) == 22, 'Pinned control seed count differs')
    for item in control['seed_files']:
        data = (fixture / item['path']).read_bytes()
        require(sha(data) == (OLDER_PRIVATE if item['path'] == 'model/private.mem' else item['sha256']),
                'A canonical input differs beyond the older private stream')
    require((root / 'before-model/private.mem').read_bytes() == older
            and (root / 'after-model/private.mem').read_bytes() == older,
            'Stale private state was modified during the contrast')

    # Retain every original combined profile proof: actual consumers, complete
    # catalog, stock getters/policy, exact native bytes, health and full journal.
    result = helper('verify-acquired-combined').verify(root, cfg, phase)
    require(result['ordinary_install_calls'] == result['token_producer_calls'] == 0
            and result['changed_native_bytes'] == 0
            and result['raw_bandwidth_enum'] == result['effective_bandwidth_enum'] == 17,
            'Contrast exceeded stock reload-only behavior')
    result.update(schema_version='mho900-lab.acquired-stale-private-verification/1',
                  source_stock_control_seal=CONTROL_SEAL, source_combined_seal=SOURCE_SEAL,
                  stale_private_before_sha256=OLDER_PRIVATE, stale_private_after_sha256=LATER_PRIVATE,
                  control_contrast_record_ids=[16192], unchanged_other_canonical_files=21,
                  stale_private_bytes_preserved=True, native_template_unchanged=True)
    return result


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
