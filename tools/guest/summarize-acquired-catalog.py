#!/usr/bin/env python3
"""Independently audit and seal one completed offline acquired catalog trial."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tomllib
import sys
sys.dont_write_bytecode=True


def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def load(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();r=a.run
    cfg=tomllib.loads((r/'source/synthetic.toml').read_text());result=tomllib.loads((r/'result.toml').read_text())
    assert result['runner_exit']==result['original_exit']==0 and result['stopped_phase']=='trial-complete' and result['physical_contact'] is False
    assert (r/'fixture-before.toml').read_bytes()==(r/'fixture-final.toml').read_bytes()
    v=load('verify-acquired-catalog');prep=load('prepare-acquired-catalog');prep.verify_fixture(r/'fixture')
    negative=result['trial_mode']=='acquired-catalog-negative'
    assert result['trial_mode'] in ('acquired-catalog-negative','acquired-catalog-positive')
    phases=[('negative','negative')] if negative else [('install','positive'),('process-reload','reload'),('reboot-reload','reload')]
    previous=None;counts=[];calls=[];enabled=[]
    for label,phase in phases:
        d=r/'phases'/label;verdict=v.verify(d,cfg,phase);assert verdict['verification']=='accepted'
        counts.append(len((d/'guest-events.jsonl').read_text().splitlines()));calls.append(verdict['ordinary_install_calls'])
        events=[json.loads(l) for l in (d/'guest-events.jsonl').read_text().splitlines()]
        after=next(e['options'] for e in events if e['kind']=='option-catalog' and e['checkpoint']=='after')
        names=[e['option_name'] for e in after if e['valid']]
        assert not enabled or enabled==names;enabled=names
        files={}
        for folder in ('rigol','model'):
            for f in sorted((d/('after-'+folder)).rglob('*')):
                if f.is_file() and (folder=='rigol' or f.name=='private.mem' or f.name.startswith('crypto-')):
                    files[folder+'/'+str(f.relative_to(d/('after-'+folder)))]=digest(f)
        assert previous is None or previous==files,'Canonical persistent state changed'
        previous=files
    reboot=not negative
    if reboot:assert (r/'initial-boot-id.txt').read_bytes()!=(r/'reboot-boot-id.txt').read_bytes() and calls==[1,0,0]
    else:assert calls==[1]
    index=r/'sealed-sha256.txt'
    if index.exists():
        for line in index.read_text().splitlines():
            h,n=line.split(maxsplit=1);assert digest(r/n)==h
    else:
        files=sorted(f for f in r.rglob('*') if f.is_file() and not f.is_symlink())
        index.write_text(''.join(digest(f)+'  '+str(f.relative_to(r))+'\n' for f in files))
    summary=dict(schema_version=1,run_id=r.name,option_name=cfg['option_name'],arm='negative48' if negative else 'positive',
                 started_at=result['started_at'],finished_at=result['finished_at'],verification='accepted',
                 journal_counts=counts,installer_calls=calls,enabled_catalog=enabled,guest_reboot_observed=reboot,
                 canonical_files_identical_across_reload=reboot,canonical_file_count=len(previous),
                 raw_bandwidth_enum=17,effective_bandwidth_enum=17,physical_contact=False,
                 source_seal=cfg['source_catalog_seal'],seal_sha256=digest(index),auditor_sha256=digest(Path(__file__)))
    a.output.write_text('\n'.join(k+' = '+json.dumps(val) for k,val in summary.items())+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
