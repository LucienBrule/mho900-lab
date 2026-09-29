#!/usr/bin/env python3
"""Prepare a fresh, unit-data-free disposable entitlement fixture."""
import argparse
from pathlib import Path
import shutil
import tomllib


def no_links(root):
    for path in [root, *root.rglob('*')]:
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError('Fixture input contains a link or special file')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source_art_fixture', type=Path)
    parser.add_argument('synthetic_config', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    config = tomllib.loads(args.synthetic_config.read_text())
    if config.get('schema_version') != 'mho900-lab.synthetic-entitlement-fixture/1':
        raise ValueError('Unknown synthetic fixture schema')
    if config.get('specimen_key_files_used') is not False or config.get('physical_contact') is not False:
        raise ValueError('Only synthetic, offline fixtures are accepted')
    for name in ('lib', 'art', 'ramdisk.img'):
        item = args.source_art_fixture / name
        if not item.exists():
            raise ValueError('Missing input: ' + name)
        no_links(item)
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ('lib', 'art'):
        shutil.copytree(args.source_art_fixture / name, args.output / name)
    shutil.copy2(args.source_art_fixture / 'ramdisk.img', args.output / 'ramdisk.img')
    shutil.copy2(args.synthetic_config, args.output / 'synthetic.toml')
    (args.output / 'rigol' / 'data').mkdir(parents=True)
    (args.output / 'model').mkdir()
    print('schema_version = "mho900-lab.synthetic-entitlement-preparation/1"')
    print('unit_specific_files_copied = false')
    print('rigol_initially_empty = true')
    print('model_initially_empty = true')


if __name__ == '__main__':
    main()
