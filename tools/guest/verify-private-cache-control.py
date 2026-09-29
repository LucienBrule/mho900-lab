#!/usr/bin/env python3
"""Independently audit passive ownership and paired-cache reads in an offline guest."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import struct
import tomllib

sys.dont_write_bytecode = True
SCHEMA = 'mho900-lab.private-cache-reader/1'
REGISTRY = 0xbe0f18
BUDGET = 16384
EMPTY = struct.pack('<II', 8, (-8)&0xffffffff) + bytes(0x700-8)
APK_SHA256 = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
ELF_SHA256 = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_toml(path):
    return tomllib.loads(path.read_text())


def frozen_key(path):
    return str(path).replace('/', '_').replace('.', '_').replace('-', '_')


def audit(run):
    result = read_toml(run / 'result.toml')
    require(result['result'] == 'accepted' and result['physical_access'] is False,
            'Runner did not accept an offline control')
    frozen = read_toml(run / 'frozen-inputs.toml')
    seen = set()
    for folder in ('source', 'inputs'):
        for path in (run / folder).iterdir():
            require(not path.is_symlink(), 'Frozen input is a symlink')
            if not path.is_file():
                continue
            key = frozen_key(path.relative_to(run))
            require(key not in seen and frozen.get(key) == sha(path.read_bytes()),
                    'Frozen input hash absent, ambiguous or changed: ' + str(path.name))
            seen.add(key)
    require(seen == set(frozen), 'Frozen inventory has missing or extra entries')

    spec = importlib.util.spec_from_file_location(
        'private_cache_apk_geometry', run / 'source/resolve-apk-cached-identity.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    verifier = oracle.v
    require(oracle.APK_SHA256 == APK_SHA256 and verifier.STOCK_SHA256 == ELF_SHA256,
            'Geometry oracle stock pins differ')
    # Existing initialized-data anchors establish bias only. The service registry
    # is independently checked as BSS, including its partial file-page tail.

    build = read_toml(run / 'inputs/build.toml')
    require(build.get('profile') == 'private-cache-owner-two-snapshot' and
            build.get('maximum_memory_bytes') == BUDGET, 'Frozen build is not the paired-private-cache profile')
    for name in ('read-private-cache', 'private-cache-mapping-fixture',
                 'read-private-cache.c', 'private-cache-mapping-fixture.c', 'build.py'):
        entries = [item for item in build['files'] if item['path'] == name]
        require(len(entries) == 1 and entries[0]['sha256'] ==
                sha((run / 'inputs' / name).read_bytes()), 'Build pin differs: ' + name)
    for name in ('stock.apk', 'read-private-cache', 'private-cache-mapping-fixture'):
        require((run / ('roundtrip-' + name)).read_bytes() ==
                (run / 'inputs' / name).read_bytes(), 'Guest roundtrip differs: ' + name)

    apk = (run / 'inputs/stock.apk').read_bytes()
    entry, size, loads = oracle.archive_entry(apk)
    require(entry == 0xf05000 and size == 12453760, 'Unexpected embedded ELF geometry')
    identities = {name: read_toml(run / ('fixture-identity-' + name + '.toml'))
                  for name in ('positive', 'bad-backlink')}

    def unique_artifact(suffix, extension='stdout'):
        candidates = list(run.glob('*-' + suffix + '.' + extension))
        require(len(candidates) == 1, 'Missing or ambiguous artifact: ' + suffix)
        return candidates[0]

    def common(manifest, mode, identity):
        require(manifest['schema_version'] == SCHEMA and manifest['mode'] == mode,
                'Wrong reader profile/mode')
        require(manifest['pid'] == identity['pid'] and manifest['expected_boot_id'] == identity['boot_id']
                and manifest['library_path'] == identity['path'], 'Wrong fixture identity')
        require(manifest['maximum_memory_bytes'] == BUDGET and manifest['maximum_registry_active']==64
                and manifest['maximum_registry_capacity']==128 and manifest['window_size']==0x700, 'Read bounds differ')
        require(manifest['atomic_snapshot_proven'] is False and manifest['physical_fram_read'] is False,
                'Reader overstates observation')
        for field in ('target_attached', 'target_calls', 'target_writes'):
            require(manifest[field] is False, 'Unexpected target intervention')

    for mode, stage in (('wrong-starttime','process-identity'), ('wrong-pin','library-hash'),
                        ('unmapped-range','target-ranges')):
        d=run/mode; m=read_toml(d/'manifest.toml'); identity=identities['positive']
        common(m,mode,identity)
        require(m['result']=='rejected' and m['stage']==stage and m['error_number']==0,
                'Negative did not reach intended gate')
        require(read_toml(unique_artifact('reader-'+mode,'toml'))['returncode']==3,
                'Negative return code differs')
        require(all(m[k]==0 for k in ('mem_open_count','memory_read_calls','bytes_read',
                                      'memory_bytes_requested','sample_count')),
                'Pre-read negative touched memory')
        require(m['read_results']==m['read_requested']==m['read_addresses']==[],
                'Pre-read negative attempted reads')
        require(not list(d.glob('read-*.bin')) and not list(d.glob('work-*.bin'))
                and not list(d.glob('ref-*.bin')), 'Pre-read negative retained memory')
        require(verifier.number(m['expected_starttime'])==int(identity['starttime'])+(mode=='wrong-starttime'),
                'Wrong expected starttime')
        if mode=='wrong-starttime':
            require(verifier.number(m['observed_starttime_before'])==int(identity['starttime']),
                    'Stale PID control did not observe the actual process')
        else:
            require(m['library_sha256']==ELF_SHA256 and m['expected_library_sha256']==
                    ('0'*64 if mode=='wrong-pin' else ELF_SHA256), 'Negative ELF pin differs')

    def epoch_geometry(d,m,identity,moments):
        for field in ('device','inode','mode','size','mtime','mtime_nsec','ctime','ctime_nsec'):
            if len(moments)>1:
                require(m['library_'+field+'_before']==m['library_'+field+'_after'],
                        'Backing file metadata changed')
        require(verifier.number(m['library_size_before'])==len(apk)
                and verifier.number(m['library_mode_before'])&0o170000==0o100000,
                'Backing APK is not the full regular file')
        ident=verifier.device_identity(verifier.number(m['library_device_before']),
                                       verifier.number(m['library_inode_before']))
        raw=[]; resolutions=[]; selected=[]; allrows=[]
        for moment in moments:
            require(verifier.proc_identity((d/('stat-'+moment+'.txt')).read_text())==
                    (identity['pid'],int(identity['starttime'])), 'Process identity changed')
            require((d/('boot-'+moment+'.txt')).read_text().strip()==identity['boot_id'],
                    'Boot identity changed')
            data=(d/('maps-'+moment+'.txt')).read_bytes();raw.append(data)
            rows=verifier.maps_rows(data.decode());allrows.append(rows)
            resolutions.append(oracle.resolve_apk(rows,identity['path'],ident,entry,size,loads))
            selected.append([row for row in rows if row['path']==identity['path']])
        require(all(x==resolutions[0] for x in resolutions) and all(x==selected[0] for x in selected),
                'Relevant APK mapping geometry changed')
        bias=resolutions[0][0]
        require(bias==verifier.number(m['load_bias']), 'Independent load bias differs')
        if len(moments)>1:
            require(m['full_maps_changed'] is any(x!=raw[0] for x in raw[1:]),
                    'Full maps change report differs')
        return bias,allrows

    # Load only the frozen pure decoder; no process access or native calls.
    decoder_spec=importlib.util.spec_from_file_location('private_cache_decoder',run/'source/private_cache_snapshot.py')
    decoder=importlib.util.module_from_spec(decoder_spec)
    sys.modules[decoder_spec.name]=decoder
    decoder_spec.loader.exec_module(decoder)

    def transcript(d,m,bias,allrows,bad=False):
        req=m['read_requested'];ret=m['read_results'];addresses=[verifier.number(x) for x in m['read_addresses']]
        require(len(req)==len(ret)==len(addresses)==len(m.get('reads',[]))==m['memory_read_calls'], 'Read accounting length differs')
        require(sum(req)==m['memory_bytes_requested']<=BUDGET and sum(ret)==m['bytes_read'],
                'Read budget/accounting differs')
        require(all(a==b and a>0 for a,b in zip(req,ret)), 'Control contains partial or failed reads')
        require({p.name for p in d.glob('read-*.bin')}=={f'read-{i:03d}.bin' for i in range(len(req))},
                'Raw read artifact inventory differs')
        require(m['mem_open_count']==1 and m['mem_open_flags']==0, 'Wrong memory descriptor policy')
        cursor=0; touched=[]
        module_end=bias+verifier.ceiling(max(va+memsz for _,_,va,_,memsz in loads))
        def region(address,n,anonymous):
            geometry=[]
            for rows in allrows:
                matches=[r for r in rows if r['start']<=address and address+n<=r['end']]
                require(len(matches)==1,'Missing/ambiguous ownership read mapping')
                r=matches[0]
                if anonymous:
                    require(r['perms']=='rw-p' and r['path'] in ('','[heap]','[anon:libc_malloc]')
                            and r['offset']==r['major']==r['minor']==r['inode']==0
                            and (r['end']<=bias or r['start']>=module_end), 'Owner/cache not anonymous private memory')
                else:
                    require(r['perms'] in ('rw-p','r--p') and r['path']==m['library_path'],
                            'Stock structural data mapping differs')
                geometry.append(r)
            require(all(x==geometry[0] for x in geometry), 'Relevant owner/cache mapping changed')
        def take(address,n,anonymous,packed=None):
            nonlocal cursor
            require(cursor<len(req) and (addresses[cursor],req[cursor])==(address,n),
                    'Actual read deviates from reconstructed ownership chain')
            region(address,n,anonymous)
            record=m['reads'][cursor]
            require(record['index']==cursor and record['round']==round_number
                    and verifier.number(record['address'])==address and record['requested']==n
                    and record['returned']==ret[cursor] and record['anonymous'] is anonymous
                    and record['file']==f'read-{cursor:03d}.bin', 'Detailed read record differs')
            data=(d/f'read-{cursor:03d}.bin').read_bytes()
            require(len(data)==ret[cursor], 'Retained read length differs')
            if packed is not None:packed.extend(data)
            cursor+=1;return data
        owners=[];windows=[]
        for round_number in range(1,2 if bad else 3):
            packed=bytearray()
            registry=take(bias+REGISTRY,24,False,packed)
            begin,end,capacity=struct.unpack('<QQQ',registry)
            require(0<begin<=end<=capacity and begin%8==end%8==capacity%8==0
                    and 0<(end-begin)//8<=64 and (capacity-begin)//8<=128,
                    'Service vector bound differs')
            count=(end-begin)//8
            require(count==1 and capacity==end,'Synthetic control registry differs')
            region(begin,capacity-begin,True)
            pointers=struct.unpack('<'+'Q'*count,take(begin,count*8,True,packed))
            require(len(set(pointers))==count and all(x%8==0 and x>0 for x in pointers),
                    'Service item pointers ambiguous or unaligned')
            ids=[struct.unpack('<I',take(pointer,4,True,packed))[0] for pointer in pointers]
            require(ids.count(38)==1,'Setup service is missing or ambiguous')
            item=pointers[ids.index(38)];item_data=take(item,40,True,packed)
            require(struct.unpack_from('<I',item_data)[0]==38,'Selected service ID changed')
            base=struct.unpack_from('<Q',item_data,32)[0];complete=base-8
            require(base>8 and complete%8==0,'Invalid complete owner address')
            setup=take(complete,160,True,packed)
            backlink=struct.unpack_from('<Q',setup,16)[0]
            if bad:
                require(backlink!=item,'Owner-corruption control has correct backlink')
                break
            require(backlink==item,'Owner backlink differs')
            for offset,point,top in ((0,0xb6c3b0,0),(8,0xb6c3f0,-8),(0x48,0xb6c418,-72)):
                require(struct.unpack_from('<Q',setup,offset)[0]==bias+point,'Setup vptr differs')
                vhead=take(bias+point-16,16,False,packed)
                require(struct.unpack('<qQ',vhead)==(top,bias+0xb6c440),'Setup vtable/RTTI metadata differs')
            fd,device,cache_size=struct.unpack_from('<iii',setup,0x58)
            work,ref=struct.unpack_from('<QQ',setup,0x68)
            require(fd>=0 and device==0x50 and cache_size==8192 and work%8==ref%8==0,
                    'CFram header differs')
            region(work,8192,True);region(ref,8192,True)
            require(work+8192<=ref or ref+8192<=work,'Caches overlap')
            require(all(complete+160<=x or x+8192<=complete for x in (work,ref)), 'Owner/cache overlap')
            w=take(work+0x100,0x700,True);r=take(ref+0x100,0x700,True)
            require(take(complete,160,True,packed)==setup
                    and take(item,40,True,packed)==item_data
                    and take(bias+REGISTRY,24,False,packed)==registry,
                    'Owner metadata changed across private-window reads')
            require(w==r==EMPTY,'Synthetic private windows differ')
            require(decoder.private_stream(w)==decoder.private_stream(r)==(EMPTY[:8],()),
                    'Independent private stream decode differs')
            require((d/f'work-{round_number}.bin').read_bytes()==w
                    and (d/f'ref-{round_number}.bin').read_bytes()==r
                    and (d/f'owner-{round_number}.bin').read_bytes()==bytes(packed),
                    'Structured artifacts differ from actual read transcript')
            owners.append(bytes(packed));windows.append((w,r))
            for key,value in [('registry_count',count),('owner_item',item),('owner_base',base),
                              ('owner_complete',complete),('working_pointer',work),('reference_pointer',ref)]:
                require(verifier.number(m[key])==value,'Reported owner differs: '+key)
        require(cursor==len(req), 'Unexpected additional process reads')
        if bad:
            require(not list(d.glob('work-*.bin')) and not list(d.glob('ref-*.bin')),
                    'Owner rejection nevertheless copied private windows')
        else:
            require(owners[0]==owners[1] and windows[0]==windows[1], 'Repeated owner/windows changed')
            require(m['sample_1_sha256']==sha(owners[0]) and m['sample_2_sha256']==sha(owners[1])
                    and m['cache_pair_equal'] is True, 'Owner hash/cache equality report differs')
        return sum(req)

    totals={}
    for scenario in ('positive','bad-backlink'):
        d=run/scenario;m=read_toml(d/'manifest.toml');identity=identities[scenario]
        common(m,'positive',identity)
        require(verifier.number(m['expected_starttime'])==int(identity['starttime']), 'Expected epoch differs')
        require(m['backing_apk_sha256']==APK_SHA256 and m['library_sha256']==m['expected_library_sha256']==ELF_SHA256
                and m['embedded_elf_offset']==entry and m['embedded_elf_size']==size, 'Backing stock pins differ')
        bad=scenario=='bad-backlink'
        require(m['result']==('rejected' if bad else 'accepted')
                and m['stage']==('owner-backlink' if bad else 'complete') and m['error_number']==0,
                'Private observer outcome differs')
        require(read_toml(unique_artifact('reader-'+scenario,'toml'))['returncode']==(3 if bad else 0),
                'Private reader return differs')
        bias,rows=epoch_geometry(d,m,identity,('before','armed') if bad else ('before','armed','between','after'))
        totals[scenario]=transcript(d,m,bias,rows,bad)
        require(totals[scenario]==(236 if bad else 8184)
                and m['memory_read_calls']==(5 if bad else 26), 'Synthetic control read extent differs')
        if bad:
            require(m['sample_count']==0 and not list(d.glob('owner-*.bin')),
                    'Rejected owner produced completed samples')
        if not bad:
            require(m['sample_count']==2,'Positive sample count differs')
            for field in ('repeat_equal','identity_stable','maps_stable','file_stable'):
                require(m[field] is True,'Positive stability assertion failed')
    network = read_toml(run / 'network-control.toml')
    require(network['result'] == 'pass' and network['external_destination_contacted'] is False,
            'Host confinement control failed')
    for field in ('allowed_loopback_tcp', 'denied_other_loopback_tcp',
                  'denied_other_loopback_udp', 'fork_setsid_inheritance'):
        require(network[field] is True, 'Host confinement witness missing: ' + field)
    require(unique_artifact('policy-before').read_bytes() ==
            unique_artifact('policy-after').read_bytes() == b'Enforcing\n',
            'Guest enforcement state changed')
    policy_before = unique_artifact('policy-bytes-before').read_bytes()
    policy_after = unique_artifact('policy-bytes-after').read_bytes()
    require(bool(policy_before) and policy_before == policy_after and
            sha(policy_before) == sha(policy_after), 'Guest policy bytes absent or changed')
    system_before = unique_artifact('system-server-before').read_bytes()
    require(system_before.strip().isdigit() and system_before ==
            unique_artifact('system-server-after').read_bytes(), 'Guest system_server changed')
    return dict(schema_version='mho900-lab.private-cache-control-verification/1', result='accepted',
                negative_controls=4, process_bytes_read=totals['positive'], maximum_memory_bytes=BUDGET,
                owner_negative_bytes_read=totals['bad-backlink'], samples_match_synthetic_fixture=True,
                independent_apk_geometry=True, ownership_reconstructed_from_raw_reads=True,
                private_streams_independently_decoded=True, enforcement_state_unchanged=True,
                policy_bytes_unchanged=True, guest_policy_sha256=sha(policy_before),
                system_server_unchanged=True, host_confinement_control_passed=True,
                physical_access=False, atomic_snapshot_claimed=False, device_readback=False,
                physical_owner_resolution_validated=False,
                verifier_sha256=sha(Path(__file__).read_bytes()))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output already exists')
    values = audit(args.run)
    with args.output.open('x') as output:
        output.write(''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in values.items()))
    print(json.dumps(values))


if __name__ == '__main__':
    main()
