#!/usr/bin/env python3
"""Offline verification of an accepted bounded private-cache observation.

This verifier opens evidence files only. It does not contact the observed process
or device. Matching software samples do not establish atomicity or FRAM durability.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tomllib

sys.dont_write_bytecode = True
SCHEMA = 'mho900-lab.private-cache-reader/1'
REGISTRY = 0xbe0f18
BUDGET = 16384
APK_SHA256 = '6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
ELF_SHA256 = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(data):return hashlib.sha256(data).hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def audit(observation,apk_path):
    d=Path(observation)
    m=tomllib.loads((d/'manifest.toml').read_text())
    require(m['schema_version']==SCHEMA and m['mode']=='positive'
            and m['result']=='accepted' and m['stage']=='complete' and m['error_number']==0,
            'Reader did not accept a complete positive observation')
    require(m['maximum_memory_bytes']==BUDGET and m['maximum_registry_active']==64
            and m['maximum_registry_capacity']==128 and m['window_size']==0x700,
            'Observation bounds differ')
    for flag in ('target_attached','target_calls','target_writes','atomic_snapshot_proven','physical_fram_read'):
        require(m[flag] is False,'Unexpected intervention or overclaimed observation')
    for flag in ('repeat_equal','identity_stable','maps_stable','file_stable'):
        require(m[flag] is True,'Reader stability check failed')
    require(m['sample_count']==2,'Exactly two samples required')
    helpers=Path(__file__).resolve().parents[1]/'guest'
    oracle=load('private_observation_apk_geometry',helpers/'resolve-apk-cached-identity.py')
    verifier=oracle.v
    require(oracle.APK_SHA256==APK_SHA256 and verifier.STOCK_SHA256==ELF_SHA256,
            'Geometry helper pins differ')
    decoder=load('private_observation_decoder',helpers/'private_cache_snapshot.py')
    apk=Path(apk_path).read_bytes()
    entry,size,loads=oracle.archive_entry(apk)
    require(entry==0xf05000 and size==12453760 and m['embedded_elf_offset']==entry
            and m['embedded_elf_size']==size and m['backing_apk_sha256']==APK_SHA256
            and m['library_sha256']==m['expected_library_sha256']==ELF_SHA256,
            'Stock APK/ELF provenance differs')
    identity=dict(pid=m['pid'],starttime=verifier.number(m['expected_starttime']),
                  boot_id=m['expected_boot_id'],path=m['library_path'])
    require(identity['pid']>1 and identity['starttime']>0 and len(identity['boot_id'])==36
            and identity['path'].startswith('/'),'Invalid process expectation')
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
            decoder.private_stream(w)
            decoder.private_stream(r)
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
                    and m['cache_pair_equal'] is (windows[0][0]==windows[0][1]), 'Owner hash/cache equality report differs')
        return sum(req)

    bias,rows=epoch_geometry(d,m,identity,('before','armed','between','after'))
    total=transcript(d,m,bias,rows)
    require(verifier.number(m['observed_starttime_before'])==identity['starttime']
            and verifier.number(m['observed_starttime_after'])==identity['starttime']
            and m['boot_id_before']==m['boot_id_after']==identity['boot_id'],
            'Reported observed process epoch differs')
    working=(d/'work-1.bin').read_bytes();reference=(d/'ref-1.bin').read_bytes()
    ws,wr=decoder.private_stream(working);rs,rr=decoder.private_stream(reference)
    return dict(schema_version='mho900-lab.private-cache-observation-verification/1',
                result='accepted', registry_count=m['registry_count'], sample_count=2,
                process_bytes_read=total, maximum_memory_bytes=BUDGET,
                memory_read_calls=m['memory_read_calls'],
                working_record_ids=[x[0] for x in wr],working_record_lengths=[x[1] for x in wr],
                reference_record_ids=[x[0] for x in rr],reference_record_lengths=[x[1] for x in rr],
                working_stream_bytes=len(ws),reference_stream_bytes=len(rs),
                private_windows_equal=working==reference,private_streams_equal=ws==rs,
                repeated_samples_equal=True,owner_metadata_bracketed=True,
                independent_apk_geometry=True,process_epoch_stable=True,
                relevant_mappings_stable=True,stock_backing_file_stable=True,
                stock_apk_sha256=APK_SHA256,stock_native_sha256=ELF_SHA256,
                atomic_snapshot_proven=False,device_readback=False,power_loss_durability_proven=False,
                live_memfile_reconstructed=False,verifier_sha256=sha(Path(__file__).read_bytes()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation',type=Path,required=True)
    parser.add_argument('--apk',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require(not args.output.exists(),'Output already exists')
    values=audit(args.observation,args.apk)
    with args.output.open('x') as f:
        f.write(''.join(key+' = '+json.dumps(value)+'\n' for key,value in values.items()))
    print(json.dumps(values))


if __name__=='__main__':main()
