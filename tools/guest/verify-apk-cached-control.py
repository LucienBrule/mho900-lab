#!/usr/bin/env python3
"""Offline audit of frozen APK-reader guest artifacts; no guest/device commands."""
import argparse
import importlib.util
import json
from pathlib import Path
import tomllib


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();r=a.run
    s=importlib.util.spec_from_file_location('apk_geometry',r/'source/resolve-apk-cached-identity.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o);v=o.v
    result=tomllib.loads((r/'result.toml').read_text());assert result['result']=='accepted' and result['physical_access'] is False
    frozen=tomllib.loads((r/'frozen-inputs.toml').read_text())
    for folder in ['source','inputs']:
        for f in (r/folder).iterdir():
            if f.is_file():assert v.sha(f.read_bytes())==frozen[str(f.relative_to(r)).replace('/','_').replace('.','_').replace('-','_')]
    build=tomllib.loads((r/'inputs/build.toml').read_text())
    for name in ['read-apk-cached-identity','apk-cached-mapping-fixture','read-apk-cached-identity.c']:
        entry=next(x for x in build['files'] if x['path']==name);assert v.sha((r/'inputs'/name).read_bytes())==entry['sha256']
    for name in ['stock.apk','read-apk-cached-identity','apk-cached-mapping-fixture']:
        assert (r/('roundtrip-'+name)).read_bytes()==(r/'inputs'/name).read_bytes()
    apk=(r/'inputs/stock.apk').read_bytes();off,size,loads=o.archive_entry(apk)
    expected=tomllib.loads((r/'fixture-identity.toml').read_text())
    sample=bytes(range(0x10,0x18))+bytes(range(0x20,0x30));assert expected['expected_sample_hex']==sample.hex()
    for mode,stage in [('wrong-starttime','process-identity'),('wrong-pin','library-hash'),('unmapped-range','target-ranges')]:
        m=tomllib.loads((r/mode/'manifest.toml').read_text())
        assert m['mode']==mode and m['result']=='rejected' and m['stage']==stage
        assert m['mem_open_count']==m['memory_read_calls']==m['bytes_read']==m['memory_bytes_requested']==m['sample_count']==0
        assert m['maximum_memory_bytes']==48 and m['read_results']==m['read_requested']==[]
    d=r/'positive';m=tomllib.loads((d/'manifest.toml').read_text())
    assert m['result']=='accepted' and m['stage']=='complete' and m['error_number']==0 and m['mode']=='positive'
    assert m['pid']==expected['pid'] and v.number(m['expected_starttime'])==int(expected['starttime']) and m['expected_boot_id']==expected['boot_id']
    assert m['library_path']==expected['path'] and m['backing_apk_sha256']==o.APK_SHA256 and m['library_sha256']==m['expected_library_sha256']==v.STOCK_SHA256
    assert m['embedded_elf_offset']==off and m['embedded_elf_size']==size
    for field in ('device','inode','mode','size','mtime','mtime_nsec','ctime','ctime_nsec'):assert m['library_'+field+'_before']==m['library_'+field+'_after']
    assert v.number(m['library_size_before'])==len(apk) and v.number(m['library_mode_before'])&0o170000==0o100000
    identity=v.device_identity(v.number(m['library_device_before']),v.number(m['library_inode_before']))
    raw=[];resolved=[];selected=[]
    for moment in ['before','armed','between','after']:
        assert v.proc_identity((d/('stat-'+moment+'.txt')).read_text())==(expected['pid'],int(expected['starttime']))
        assert (d/('boot-'+moment+'.txt')).read_text().strip()==expected['boot_id']
        b=(d/('maps-'+moment+'.txt')).read_bytes();raw.append(b);rows=v.maps_rows(b.decode())
        resolved.append(o.resolve_apk(rows,expected['path'],identity,off,size,loads))
        selected.append([row for row in rows if row['path']==expected['path']])
    assert all(x==resolved[0] for x in resolved) and all(x==selected[0] for x in selected)
    bias,addresses,_,_=resolved[0]
    assert bias==v.number(m['load_bias']) and addresses==[v.number(m['dna_address']),v.number(m['file_keys_address'])]
    assert m['full_maps_changed']==any(b!=raw[0] for b in raw[1:])
    assert m['mem_open_count']==1 and m['mem_open_flags']==0 and m['memory_read_calls']==4
    assert m['memory_bytes_requested']==m['maximum_memory_bytes']==m['bytes_read']==48 and m['sample_count']==2
    assert m['read_requested']==m['read_results']==[8,16,8,16]
    for key in ('repeat_equal','identity_stable','maps_stable','file_stable'):assert m[key] is True
    for key in ('target_attached','target_calls','target_writes'):assert m[key] is False
    for i in (1,2):
        b=(d/f'sample-{i}.bin').read_bytes();assert b==sample and v.sha(b)==m[f'sample_{i}_sha256']
    def artifact(suffix):
        candidates=list(r.glob('*-'+suffix+'.stdout'));assert len(candidates)==1;return candidates[0].read_bytes()
    assert artifact('policy-before')==artifact('policy-after')==b'Enforcing\n'
    assert artifact('system-server-before')==artifact('system-server-after')
    values=dict(schema_version=1,result='accepted',negative_controls=3,process_bytes_read=48,
                samples_match_synthetic_fixture=True,independent_apk_geometry=True,policy_unchanged=True,
                system_server_unchanged=True,physical_access=False,atomic_snapshot_claimed=False,
                verifier_sha256=v.sha(Path(__file__).read_bytes()))
    a.output.write_text(''.join(k+' = '+json.dumps(val)+'\n' for k,val in values.items()))
    print(json.dumps(values))


if __name__=='__main__':main()
