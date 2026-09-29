#!/usr/bin/env python3
"""Freeze an exact older-private-state contrast for accepted permanent licenses."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess


def helper(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


combined = helper('prepare-acquired-combined')
base = combined.base
require = base.require
SOURCE_SEAL = combined.SEAL
CONTROL_SEAL = '7ffb39a50f36e97c9fce32e72869b7d3698b2aa869fbb83d10992a061c36101f'
CONTROL_TEMPLATE = '67dbbf4218f0441ecb76987db54b6023481c31e0266f400040baed82c6667199'
CONTROL_CONFIG = '6069133e1d2dff43a8fa6b98966087117782ad26b507741c8e6b7d7f72d0ed41'
BEFORE = '9e211b2fcab8245472c6bd9da85826a4bd2d28d27fe77347518b5d5da7d9eede'
AFTER = 'b13d38eb634fcdb2b64afdb323da5445ca416e22fb2cdf3918bfcea0d3481490'
ADDED = dict(acquired_stale_private_experiment=True, source_stock_control_seal=CONTROL_SEAL,
             stale_private_before_sha256=BEFORE, stale_private_after_sha256=AFTER)


def verify_control_seal(control):
    require(base.sha(control / 'sealed-sha256.txt') == CONTROL_SEAL, 'Stock control seal differs')
    members = set()
    for line in base.read(control / 'sealed-sha256.txt').decode('ascii').splitlines():
        digest, name = line.split(maxsplit=1)
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and path.as_posix() == name
                and name not in members and name != 'sealed-sha256.txt', 'Invalid control seal member')
        require(all(not parent.is_symlink() for parent in (control / path).parents), 'Control ancestry contains symlink')
        require(base.sha(control / path) == digest, 'Control seal member differs')
        members.add(name)
    for directory in ('fixture', 'source', 'phases'):
        require(all(directory + '/' + name in members for name in base.files(control / directory)),
                'Unsealed control input')
    require({'result.toml','fixture-before.toml','fixture-final.toml'} <= members, 'Control seal incomplete')


def verify_sources(source, control):
    combined.source_state(source)  # Pinned seal and all three original phase verifiers.
    verify_control_seal(control)
    result = base.table(control / 'result.toml')
    require(result['runner_exit'] == result['original_exit'] == 0 and result['physical_contact'] is False
            and result['trial_mode'] == 'acquired-combined-stock' and result['stopped_phase'] == 'trial-complete',
            'Stock control incomplete')
    require(base.read(control / 'fixture-before.toml') == base.read(control / 'fixture-final.toml')
            and base.read(control / 'source/synthetic.toml') == base.read(control / 'fixture/synthetic.toml')
            and base.sha(control / 'fixture/synthetic.toml') == CONTROL_CONFIG, 'Stock control configuration differs')
    cfg = combined.verify_fixture(control / 'fixture')
    require(cfg['capability_arm'] == 'stock' and cfg['source_combined_seal'] == SOURCE_SEAL, 'Wrong stock control lineage')
    verdict = helper('verify-acquired-combined').verify(control / 'phases/capability', cfg, 'reload')
    require(verdict['verification'] == 'accepted', 'Independent stock control verification failed')
    for name in combined.PATHS:
        expected = base.read(source / 'phases/reboot-reload' / ('after-' + name))
        require(base.read(control / 'fixture' / name) == expected, 'Control input differs from final catalog')
        for checkpoint in ('before-', 'after-'):
            require(base.read(control / 'phases/capability' / (checkpoint + name)) == expected,
                    'Control phase changed canonical input')
    older = source / 'phases/install/before-model/private.mem'
    newer = source / 'phases/install/after-model/private.mem'
    require(base.sha(older) == BEFORE and base.sha(newer) == AFTER, 'Pinned older/newer private state differs')
    decode = helper('verify-synthetic-entitlement').private_records
    before, after = decode(base.read(older)), decode(base.read(newer))
    require(set(before) == set(after) == {2337,16192} and before[2337] == after[2337]
            and len(before[16192]) == len(after[16192]) == 8 and before[16192] != after[16192],
            'Private contrast not solely saved time')
    return cfg


def verify_fixture(root):
    cfg = combined.verify_fixture(root)
    require(base.sha(root / 'template.js') == CONTROL_TEMPLATE, 'Accepted combined template changed')
    require(cfg['capability_arm'] == 'stock' and cfg['source_combined_seal'] == SOURCE_SEAL,
            'Older-private contrast is stock only')
    require(cfg.get('acquired_stale_private_experiment') is True
            and all(cfg.get(key) == value for key, value in ADDED.items()), 'Older-private provenance differs')
    require(base.files(root / 'provenance') == ['postinstall-private.mem','stock-control.toml']
            and base.sha(root / 'provenance/stock-control.toml') == CONTROL_CONFIG,
            'Pinned stock control configuration differs')
    control = base.table(root / 'provenance/stock-control.toml')
    expected = copy.deepcopy(control)
    expected.update(ADDED)
    old_manifest = [item for item in expected['seed_files'] if item['path'] == 'model/private.mem']
    require(len(old_manifest) == 1 and old_manifest[0]['sha256'] == AFTER, 'Control private pin differs')
    old_manifest[0]['sha256'] = BEFORE
    require(cfg == expected, 'Contrast changes configuration beyond private hash and provenance')
    require(base.sha(root / 'model/private.mem') == BEFORE
            and base.sha(root / 'provenance/postinstall-private.mem') == AFTER,
            'Contrast did not retain exact older/newer private bytes')
    decode = helper('verify-synthetic-entitlement').private_records
    before, after = decode(base.read(root / 'model/private.mem')), decode(base.read(root / 'provenance/postinstall-private.mem'))
    require(set(before) == set(after) == {2337,16192} and before[2337] == after[2337]
            and len(before[16192]) == len(after[16192]) == 8 and before[16192] != after[16192],
            'Retained private contrast differs beyond saved time')
    return cfg


def prepare(source, control, output):
    require(not output.exists(), 'Output already exists')
    cfg = verify_sources(source, control)
    ignored = subprocess.run(['git','check-ignore','--quiet','--',str(output.resolve())],
                             cwd=Path(__file__).resolve().parents[2], check=False)
    require(ignored.returncode == 0, 'Private contrast output must be Git ignored')
    # Copy the accepted stock fixture, including its exact unchanged template.
    shutil.copytree(control / 'fixture', output)
    output.chmod(0o700)
    target = output / 'model/private.mem'
    target.chmod(0o600)
    target.write_bytes(base.read(source / 'phases/install/before-model/private.mem'))
    cfg.update(ADDED)
    for item in cfg['seed_files']:
        if item['path'] == 'model/private.mem':
            item['sha256'] = BEFORE
    destination = output / 'synthetic.toml'
    destination.chmod(0o600)
    destination.write_text(base.dump_config(cfg))
    (output / 'provenance').mkdir(mode=0o700)
    shutil.copy2(control / 'fixture/synthetic.toml', output / 'provenance/stock-control.toml')
    shutil.copy2(source / 'phases/install/after-model/private.mem', output / 'provenance/postinstall-private.mem')
    # Keep the copied control preparation receipt; append separate contrast provenance.
    (output / 'stale-private-preparation.toml').write_text(base.dump_config(dict(
        schema_version='mho900-lab.acquired-stale-private-preparation/1', source_combined_seal=SOURCE_SEAL,
        source_stock_control_seal=CONTROL_SEAL, stale_private_before_sha256=BEFORE,
        stale_private_after_sha256=AFTER, changed_canonical_files=['model/private.mem'],
        private_changed_record_ids=[16192], canonical_seed_files=22, ordinary_seed_count=10,
        physical_contact=False, token_generated=False, lifecycle='License.init-only')))
    verify_fixture(output)
    for name in combined.PATHS:
        if name != 'model/private.mem':
            require(base.read(output / name) == base.read(control / 'fixture' / name), 'Unintended canonical contrast')
    for directory in ('lib','art','ancestor'):
        require(base.files(output / directory) == base.files(control / 'fixture' / directory), 'Runtime inventory changed')
        for name in base.files(output / directory):
            require(base.read(output / directory / name) == base.read(control / 'fixture' / directory / name), 'Runtime bytes changed')
    for name in ('template.js','ramdisk.img'):
        require(base.read(output / name) == base.read(control / 'fixture' / name), 'Template or ramdisk changed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--control',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify-fixture',type=Path)
    args=parser.parse_args()
    if args.verify_fixture:
        require(not any((args.source,args.control,args.output)), 'Mixed invocation')
        verify_fixture(args.verify_fixture)
        print('verification = "accepted"\nprofile = "acquired-stale-private"')
    else:
        require(all((args.source,args.control,args.output)), 'Pass --source --control --output')
        prepare(args.source,args.control,args.output)
        print('preparation = "complete"\nchanged_canonical_files = ["model/private.mem"]\nphysical_contact = false')


if __name__ == '__main__':
    main()
