#!/usr/bin/env python3
"""Freeze a private, acquired-input FlexA guest fixture from the accepted baseline.

Uses Python for the existing TOML/hash/Frida protocol tooling. This prepares
inputs only; it does not generate a token, start a guest, or contact a scope.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tomllib


def helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name+'.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


base = helper('prepare-option-catalog-fixture')
SEAL = '26e48de28bb1829c99ab82e768f7f05bb42d0b36ad87bef600573cedc87a83f6'


def verify_fixture(root):
    cfg = base.table(root/'synthetic.toml')
    assert cfg['schema_version'] == 'mho900-lab.acquired-option-fixture/1'
    assert cfg['acquired_option_experiment'] and cfg['physical_contact'] is False
    assert cfg['specimen_key_files_used'] is True and cfg['source_baseline_seal'] == SEAL
    assert cfg['option_type'] == 5 and cfg['option_name'] == 'FlexA'
    assert cfg['model'] == 'MHO984' and cfg['license_type'] == cfg['license_time'] == 0
    assert cfg['stock_native_sha256'] == cfg['expected_native_sha256'] == base.STOCK
    assert cfg['consumer_observation_required'] and cfg['token_text_encoding'] == 'low-nibble-first'
    assert cfg['aes_key_ascii'].encode() == bytes.fromhex(cfg['key_field_hex'])[:32]
    assert len(bytes.fromhex(cfg['key_field_hex'])) == 130
    assert len(bytes.fromhex(cfg['file_keys_hex'])) == 16 and cfg['key_left'] and cfg['serial']
    candidate = cfg['catalog_candidate']
    text = cfg['model']+'#'+cfg['serial']+'#FlexA#guest#0#0'
    padded = 32 if len(text) < 32 else 48
    assert len(text) < padded
    assert candidate == dict(type=5,name='FlexA',padded_bytes=padded,positive_plaintext=text)
    assert cfg['token_padded_bytes'] == padded and cfg['positive_plaintext'] == text
    assert cfg['seed_options'] == []
    base.validate_catalog(cfg['seed_catalog'], [])
    assert sorted(x['path'] for x in cfg['seed_files']) == ['model/private.mem','rigol/data/Key.data']
    for item in cfg['seed_files']:assert base.sha(root/item['path']) == item['sha256']
    assert (root/'rigol/data/Key.data').read_bytes().hex() == cfg['key_ciphertext_hex']
    records = helper('verify-synthetic-entitlement').private_records((root/'model/private.mem').read_bytes())
    assert records == {2337:bytes.fromhex(cfg['key_ciphertext_hex'])}
    assert base.files(root/'rigol') == ['data/Key.data'] and base.files(root/'model') == ['private.mem']
    base.check_runtime(root)
    return cfg


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--verify-fixture',type=Path)
    a=p.parse_args()
    if a.verify_fixture:
        cfg=verify_fixture(a.verify_fixture)
        print('verified = true\nphysical_contact = false\noption_name = "FlexA"\npadded_bytes = '+str(cfg['token_padded_bytes']))
        return
    assert a.source and a.output and not a.output.exists()
    index=a.source/'sealed-evidence-sha256.txt'
    assert base.sha(index)==SEAL
    for line in index.read_text().splitlines():
        pin,name=line.split(maxsplit=1)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert base.sha(a.source/name)==pin, 'Baseline seal member mismatch'
    evidence=base.table(a.source/'acquired-verification.toml')
    assert evidence['verification']=='accepted' and evidence['exact_key_outputs']
    assert evidence['enabled_options']==['EMBD','COMP','AUTO']
    cfg=base.table(a.source/'fixture/acquired.toml')
    cfg.update(schema_version='mho900-lab.acquired-option-fixture/1',acquired_option_experiment=True,
        source_baseline_seal=SEAL,stock_native_sha256=base.STOCK,expected_native_sha256=base.STOCK,
        specimen_key_files_used=True,consumer_observation_required=True,token_text_encoding='low-nibble-first',
        aes_key_ascii=bytes.fromhex(cfg['key_field_hex'])[:32].decode('ascii'),
        option_type=5,option_name='FlexA',license_type=0,license_time=0,installer_family='MHO900',
        private_store='accepted-baseline-modeled',seed_options=[])
    text=cfg['model']+'#'+cfg['serial']+'#FlexA#guest#0#0'
    padded=32 if len(text)<32 else 48
    assert len(text)<padded
    cfg.update(token_padded_bytes=padded,positive_plaintext=text,
               catalog_candidate=dict(type=5,name='FlexA',padded_bytes=padded,positive_plaintext=text))
    events=[json.loads(line) for line in (a.source/'guest-events.jsonl').read_text().splitlines()]
    catalogs=[e for e in events if e['kind']=='option-catalog'];assert len(catalogs)==1
    cfg['seed_catalog']=catalogs[0]['options']
    a.output.mkdir(parents=True,mode=0o700)
    for name in ('lib','art'):shutil.copytree(a.source/'fixture'/name,a.output/name)
    shutil.copy2(a.source/'fixture/ramdisk.img',a.output/'ramdisk.img')
    (a.output/'rigol/data').mkdir(parents=True);(a.output/'model').mkdir()
    shutil.copy2(a.source/'after-rigol/data/Key.data',a.output/'rigol/data/Key.data')
    shutil.copy2(a.source/'after-model/private.mem',a.output/'model/private.mem')
    cfg['seed_files']=[dict(path=n,sha256=base.sha(a.output/n)) for n in ('rigol/data/Key.data','model/private.mem')]
    (a.output/'synthetic.toml').write_text(base.dump_config(cfg))
    verify_fixture(a.output)
    parts=['entitlement-private-store.js','entitlement-acquired-consumer.js','entitlement-capability.js',
           'entitlement-art.js','entitlement-acquired-option.js','entitlement-baseline.js']
    (a.output/'template.js').write_text('\n'.join((Path(__file__).parent/name).read_text() for name in parts))
    (a.output/'preparation.toml').write_text('schema_version = 1\nsource_baseline_seal = "'+SEAL+'"\nphysical_contact = false\ntoken_generated = false\npadded_bytes = '+str(padded)+'\n')
    print('Prepared private acquired-input fixture; no guest or token generation.')


if __name__=='__main__':main()
