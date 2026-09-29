#!/usr/bin/env python3
"""Offline independent geometry/sample verification for the derived two-word reader."""
import argparse, hashlib, importlib.util, json, struct, sys, tomllib
from pathlib import Path
sys.dont_write_bytecode = True
PIN='09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e'
ORACLE_PIN='8730784f02aa0645edea5716c6cdcdab90d0f60c75a68a340b0e4a9674361ec2'
RANGES=((0xbbcce4,4,0xbbbce4),(0xbbcce8,4,0xbbbce8))
SCHEMA='mho900-lab.derived-bandwidth-reader/1'
SAMPLE=struct.pack('<II',18,18)
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return tomllib.loads(p.read_text())
def oracle(path):
    require(sha(path)==ORACLE_PIN,'Independent geometry source differs')
    spec=importlib.util.spec_from_file_location('derived_bandwidth_geometry',path)
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    # Fixed profile parameters applied only to this loaded module, not its source.
    v.STOCK_SHA256=PIN;v.RANGES=RANGES
    return v

def common(m):
    require(m['schema_version']==SCHEMA,'Wrong reader schema')
    require(m['maximum_memory_bytes']==16 and m['raw_band_size']==m['effective_band_size']==4,'Read profile changed')
    for key in ('target_attached','target_calls','target_writes'):require(m[key] is False,'Unexpected target intervention')

def verify_observation(directory,elf,v,expected=None):
    require(sha(elf)==PIN,'Derived ELF pin mismatch')
    loads=v.elf_loads(elf.read_bytes());m=read(directory/'manifest.toml');common(m)
    require(m['mode']=='positive' and m['result']=='accepted' and m['stage']=='complete' and m['error_number']==0,'Reader did not accept')
    require(m['library_sha256']==m['expected_library_sha256']==PIN,'Reader ELF pin mismatch')
    require(v.number(m['validation_raw_band_virtual_address'])==RANGES[0][0],'Validated range differs')
    for field in ('device','inode','mode','size','mtime','mtime_nsec','ctime','ctime_nsec'):
        require(m['library_'+field+'_before']==m['library_'+field+'_after'],'Backing metadata changed: '+field)
    require(m['library_size_before']==elf.stat().st_size==12453760 and m['library_mode_before']&0o170000==0o100000,'Not the complete regular ELF')
    require(m['library_device']==m['library_device_before'] and m['library_inode']==m['library_inode_before'],'Backing identity differs')
    identity=v.device_identity(m['library_device_before'],m['library_inode_before'])
    raw=[];resolved=[];selected=[]
    for epoch in ('before','armed','between','after'):
        require(v.proc_identity((directory/('stat-'+epoch+'.txt')).read_text())==(m['pid'],m['expected_starttime']),'Process identity differs: '+epoch)
        require((directory/('boot-'+epoch+'.txt')).read_text().strip()==m['expected_boot_id'],'Boot differs: '+epoch)
        data=(directory/('maps-'+epoch+'.txt')).read_bytes();raw.append(data);rows=v.maps_rows(data.decode())
        resolved.append(v.resolve(loads,rows,m['library_path'],identity))
        selected.append([r for r in rows if r['path']==m['library_path']])
    require(all(x==resolved[0] for x in resolved) and all(x==selected[0] for x in selected),'Relevant ELF mappings changed')
    bias,addresses=resolved[0]
    require(bias==v.number(m['load_bias']) and addresses==[v.number(m['raw_band_address']),v.number(m['effective_band_address'])],'Independent address resolution differs')
    require(m['full_maps_changed'] is any(x!=raw[0] for x in raw[1:]),'Full maps change reporting differs')
    require(m['observed_starttime_before']==m['observed_starttime_after']==m['expected_starttime'],'Manifest epoch identity differs')
    require(m['boot_id_before']==m['boot_id_after']==m['expected_boot_id'],'Manifest boot differs')
    require(m['mem_open_count']==1 and m['mem_open_flags']==0 and m['memory_read_calls']==4 and m['sample_count']==2,'Read accounting differs')
    require(m['memory_bytes_requested']==m['bytes_read']==16 and m['read_requested']==m['read_results']==[4,4,4,4],'Read bounds differ')
    for key in ('repeat_equal','identity_stable','maps_stable','file_stable'):require(m[key] is True,'Stability flag false: '+key)
    samples=[]
    for n in (1,2):
        p=directory/f'sample-{n}.bin';data=p.read_bytes();samples.append(data)
        require(len(data)==8 and sha(p)==m[f'sample_{n}_sha256'],'Sample extent/hash differs')
    require(samples[0]==samples[1],'Repeated samples differ')
    if expected is not None:
        require(samples[0]==SAMPLE,'Synthetic fixture bytes differ')
        require((m['pid'],m['expected_starttime'],m['expected_boot_id'],m['library_path'])==(expected['pid'],int(expected['starttime']),expected['boot_id'],expected['path']),'Fixture epoch differs')
    raw_value,effective_value=struct.unpack('<II',samples[0])
    return dict(schema='mho900-lab.derived-bandwidth-observation-verification/1',result='accepted',derived_native_sha256=PIN,
                raw_bandwidth=raw_value,effective_bandwidth=effective_value,process_bytes_read=16,repeated_samples_equal=True,
                independent_standalone_geometry=True,atomic_snapshot_claimed=False,target_attached=False,target_calls=False,target_writes=False)

def audit(run):
    result=read(run/'result.toml');require(result['result']==result['original_result']=='accepted' and result['cleanup_errors']==[] and result['physical_access'] is False,'Runner failed')
    frozen=read(run/'frozen-inputs.toml');found={}
    for folder in ('source','inputs'):
        for p in (run/folder).iterdir():
            require(p.is_file() and not p.is_symlink(),'Frozen input not a regular file')
            key=str(p.relative_to(run)).replace('/','_').replace('.','_').replace('-','_');require(key not in found,'Ambiguous frozen key');found[key]=sha(p)
    require(found==frozen,'Frozen source/input inventory changed')
    v=oracle(run/'source/verify-cached-identity.py');elf=run/'inputs/libscope-auklet.so';require(sha(elf)==PIN,'Derived input differs')
    build=read(run/'inputs/build.toml');require(build['profile']=='derived-bandwidth-4-4' and build['maximum_memory_bytes']==16 and build['derived_library_sha256']==PIN,'Build profile differs')
    for item in build['files']:require(sha(run/'inputs'/item['path'])==item['sha256'],'Build member differs')
    for name in ('libscope-auklet.so','read-derived-bandwidth','derived-bandwidth-fixture'):
        require((run/('roundtrip-'+name)).read_bytes()==(run/'inputs'/name).read_bytes(),'Staged guest input differs')
    expected=read(run/'fixture-identity.toml');require(expected['expected_sample_hex']==SAMPLE.hex(),'Declared fixture differs')
    def artifact(name,suffix='stdout'):
        matches=list(run.glob('*-'+name+'.'+suffix));require(len(matches)==1,'Missing/ambiguous artifact '+name);return matches[0]
    for mode,stage in [('wrong-starttime','process-identity'),('wrong-pin','library-hash'),('unmapped-range','target-ranges'),('bad-mapping','target-ranges')]:
        directory=run/mode;m=read(directory/'manifest.toml');common(m)
        require(m['result']=='rejected' and m['stage']==stage and m['error_number']==0,'Wrong rejection gate: '+mode)
        require(read(artifact('reader-'+mode,'toml'))['returncode']==3,'Wrong rejection exit')
        require(all(m[k]==0 for k in ('mem_open_count','memory_read_calls','bytes_read','memory_bytes_requested','sample_count')),'Rejected control accessed memory')
        require(m['read_results']==m['read_requested']==[] and not list(directory.glob('sample-*')),'Rejected control retained memory samples')
        exp=read(run/'bad-fixture-identity.toml') if mode=='bad-mapping' else expected
        require(m['mode']==('positive' if mode=='bad-mapping' else mode),'Wrong control mode')
        require(m['pid']==exp['pid'] and m['expected_boot_id']==exp['boot_id'] and m['library_path']==exp['path'],'Negative fixture identity differs')
        require(m['expected_starttime']==int(exp['starttime'])+(mode=='wrong-starttime'),'Negative start expectation differs')
        require(v.number(m['validation_raw_band_virtual_address'])==(0 if mode=='unmapped-range' else RANGES[0][0]),'Negative range request differs')
        require(v.proc_identity((directory/'stat-before.txt').read_text())==(exp['pid'],int(exp['starttime'])),'Negative actual stat differs')
        if mode!='wrong-starttime':
            require(m['library_sha256']==PIN and m['expected_library_sha256']==('0'*64 if mode=='wrong-pin' else PIN),'Negative file pin differs')
        if mode=='bad-mapping':
            rows=v.maps_rows((directory/'maps-before.txt').read_text());identity=v.device_identity(m['library_device'],m['library_inode'])
            try:v.resolve(v.elf_loads(elf.read_bytes()),rows,m['library_path'],identity)
            except ValueError as e:require('not ordinary writable/readable' in str(e),'Bad mapping failed at unrelated oracle gate')
            else:raise ValueError('Independent geometry accepted bad mapping')
    verdict=verify_observation(run/'positive',elf,v,expected)
    require(read(artifact('reader-positive','toml'))['returncode']==0,'Positive exit differs')
    network=read(run/'network-control.toml');require(network['result']=='pass' and network['external_destination_contacted'] is False,'Host confinement control failed')
    for key in ('allowed_loopback_tcp','denied_other_loopback_tcp','denied_other_loopback_udp','fork_setsid_inheritance'):require(network[key] is True,'Missing confinement witness')
    require(artifact('policy-before').read_bytes()==artifact('policy-after').read_bytes()==b'Enforcing\n','Guest not Enforcing')
    policy=artifact('policy-bytes-before').read_bytes();require(policy and policy==artifact('policy-bytes-after').read_bytes(),'Guest policy changed')
    system=artifact('system-server-before').read_bytes();require(system.strip().isdigit() and system==artifact('system-server-after').read_bytes(),'Guest system_server changed')
    commands=[json.loads(line) for line in (run/'commands.jsonl').read_text().splitlines()]
    require(all(c['argv'][:2]==['-s','emulator-5582'] or c['name'] in ('server','server-stop','mdns') for c in commands),'Non-emulator ADB transport')
    verdict.update(negative_controls=4,samples_match_synthetic_fixture=True,guest_enforcing=True,guest_policy_unchanged=True,system_server_unchanged=True,physical_access=False)
    return verdict

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--run',type=Path);g.add_argument('--observation',type=Path)
    p.add_argument('--elf',type=Path);p.add_argument('--oracle',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Output exists')
    if a.run:values=audit(a.run)
    else:
        require(a.elf is not None,'--elf required for observation')
        oracle_path=a.oracle or Path(__file__).resolve().parent.parent/'verify-cached-identity.py'
        values=verify_observation(a.observation,a.elf,oracle(oracle_path))
    a.output.write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in values.items()))
    print(json.dumps(values))

if __name__=='__main__':main()
