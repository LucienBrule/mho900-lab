#!/usr/bin/env python3
"""Independent offline verification of a physical derived-capability transition.

No device or network I/O. Correlates retained command and wire evidence, logical
files, stock signed APK, standalone native mapping and fixed repeated samples.
It establishes software policy state, not analog performance.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import socket
import struct
import sys
import tomllib
import zlib
import zipfile
sys.dont_write_bytecode=True
REBOOT_VERIFIER_PIN='aee2561e9cb76183c630049149d3e44bd037aaf1e78b0a126f6524e55f62147e'
DERIVED_VERIFIER_PIN='573611c38749d590b51b164f4d48647148236a8065038383a48e0a41bed4ba06'
DERIVED_PIN='09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e'
DERIVED_READER_PIN='a7c1eda20e814426927a25998b7768e2711fadf2914b64751237118a6d3fc5ff'
PHASES=('scpi-before','scpi-postboot','scpi-post60')
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return tomllib.loads(p.read_text())
def module(path,name,pin):
    require(sha(path)==pin,'Verifier dependency differs: '+path.name)
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=module(Path(__file__).with_name('verify-ordinary-reboot.py'),'d_reboot_evidence',REBOOT_VERIFIER_PIN)
INSTALL_VERIFIER_PIN=r.INSTALL_VERIFIER_PIN
streams=r.streams

def verify_calibration(archives):
    before=archives['before'];post=archives['postboot'];final=archives['post60']
    require(set(before)==set(post)==set(final),'Logical file set changed')
    require(post==final,'Logical files changed during postboot stability interval')
    changed={k for k in before if before[k]!=post[k]}
    require(changed <= {'data/cal_afe_bandwidth.hex','data/cal_tmp_hex.log'},'Unexpected logical data change')
    name='data/cal_afe_bandwidth.hex'
    for a in (before,post,final):
        b=a[name]
        require(len(b)==348 and struct.unpack_from('<I',b,4)[0]==20 and struct.unpack_from('<I',b,20)[0]==320,'Bandwidth calibration envelope changed')
        require(zlib.crc32(b[8:28])==struct.unpack_from('<I',b,0)[0] and zlib.crc32(b[28:])==struct.unpack_from('<I',b,24)[0],'Bandwidth calibration checksum failed')
    require(all(before[name][n]==post[name][n] for n in range(348) if n not in set(range(4))|set(range(12,16))),'Calibration changed outside established metadata words')
    require(len(before['data/cal_tmp_hex.log'])==len(post['data/cal_tmp_hex.log'])==172,'Identity fallback cache extent changed')
    return sorted(changed)

def verify_derived_observation(run,tools_root,epoch):
    d=module(tools_root/'guest/derived-bandwidth-reader/verify.py','physical_d_geometry',DERIVED_VERIFIER_PIN)
    elf=run/'metadata/post60-libscope-auklet.so'
    m=read(run/'reader/observation/manifest.toml')
    require((m['pid'],m['expected_starttime'],m['expected_boot_id'],m['library_path'])==(epoch['pid'],int(epoch['starttime']),epoch['boot_id'],epoch['library']),'Derived observation epoch differs')
    verdict=d.verify_observation(run/'reader/observation',elf,d.oracle(tools_root/'guest/verify-cached-identity.py'))
    require(verdict['raw_bandwidth']==verdict['effective_bandwidth']==18,'Derived policy is not 18/18')
    require(sha(run/'control/read-derived-bandwidth')==sha(run/'metadata/reader-roundtrip')==DERIVED_READER_PIN,'Derived reader binary differs')
    require(read(run/'metadata/cached-read-result.toml')['returncode']==0,'Reader exit differs')
    return verdict

def reassemble_adb(ds):
    require(len(ds['syn'])==1,'ADB stream missing unique SYN')
    origin=(next(iter(ds['syn']))+1)&0xffffffff
    result=bytearray();intervals=[]
    for seq,data,epoch in sorted(ds['segments'],key=lambda x:((x[0]-origin)&0xffffffff,x[2])):
        offset=(seq-origin)&0xffffffff
        require(offset<256*1024*1024 and offset<=len(result),'ADB TCP gap or excessive extent')
        overlap=min(len(data),len(result)-offset)
        require(result[offset:offset+overlap]==data[:overlap],'Conflicting ADB retransmission')
        result.extend(data[overlap:]);intervals.append((offset,offset+len(data),epoch))
    for fin in ds['fin']:require(((fin-origin)&0xffffffff)==len(result),'ADB FIN extent differs')
    return bytes(result),origin,intervals


def adb_messages(data):
    rows=[];offset=0
    while offset<len(data):
        require(len(data)-offset>=24,'Partial ADB header')
        command,arg0,arg1,length,checksum,magic=struct.unpack_from('<6I',data,offset)
        require(magic==command^0xffffffff and length<=16*1024*1024 and offset+24+length<=len(data),'Partial or invalid ADB frame')
        name=struct.pack('<I',command)
        require(name in (b'CNXN',b'AUTH',b'OPEN',b'OKAY',b'CLSE',b'WRTE'),'Unknown or encrypted ADB frame')
        body=data[offset+24:offset+24+length]
        require(checksum==0 or (sum(body)&0xffffffff)==checksum,'ADB checksum differs')
        rows.append(dict(command=name,local=arg0,remote=arg1,offset=offset,end=offset+24+length,body=body))
        offset+=24+length
    return rows


def verify_reboot_wire(path,lease,window):
    pairs={}
    with path.open('rb') as f:
        header=f.read(24)
        require(len(header)==24 and header[:4]==b'\xd4\xc3\xb2\xa1' and struct.unpack_from('<I',header,20)[0]==1,'Invalid Ethernet capture')
        while True:
            rec=f.read(16)
            if not rec:break
            require(len(rec)==16,'Short packet record')
            sec,usec,n,original=struct.unpack('<IIII',rec)
            require(n==original and 14<=n<=262144 and usec<1000000,'Incomplete wire frame')
            raw=f.read(n);require(len(raw)==n,'Short wire frame')
            if raw[12:14]!=b'\x08\x00':continue
            require(len(raw)>=34,'Short IPv4 frame')
            if raw[23]!=6:continue
            ihl=(raw[14]&15)*4;at=14+ihl;iplen=struct.unpack_from('!H',raw,16)[0]
            require(ihl>=20 and iplen>=ihl+20 and 14+iplen<=len(raw),'Invalid TCP frame')
            sport,dport,seq,ack=struct.unpack_from('!HHII',raw,at)
            if sport!=55555 and dport!=55555:continue
            require(struct.unpack_from('!H',raw,20)[0]&0x3fff==0,'Fragmented ADB packet')
            src=socket.inet_ntoa(raw[26:30]);dst=socket.inet_ntoa(raw[30:34]);direction=int(sport==55555)
            key=(src,sport,dst,dport) if direction==0 else (dst,dport,src,sport)
            require(key[0]==lease['server_ip'] and key[2]==lease['client_ip'],'Unexpected ADB peer')
            pair=pairs.setdefault(key,{n:dict(syn=set(),fin=set(),segments=[],acks=[]) for n in (0,1)})
            ds=pair[direction];flags=raw[at+13];tcpheader=(raw[at+12]>>4)*4
            require(tcpheader>=20 and ihl+tcpheader<=iplen,'Invalid ADB TCP header')
            payload=raw[at+tcpheader:14+iplen];offset=(seq+bool(flags&2))&0xffffffff;epoch=sec+usec/1e6
            if flags&2:ds['syn'].add(seq)
            if flags&1:ds['fin'].add((offset+len(payload))&0xffffffff)
            if flags&16:ds['acks'].append((ack,epoch))
            if payload:ds['segments'].append((offset,payload,epoch))
    requests=[]
    for pair in pairs.values():
        rebuilt={};origins={};intervals={};messages={}
        for direction in (0,1):
            rebuilt[direction],origins[direction],intervals[direction]=reassemble_adb(pair[direction])
            messages[direction]=adb_messages(rebuilt[direction])
        for message in messages[0]:
            if message['command']!=b'OPEN':continue
            service=message['body']
            if not service.startswith(b'reboot:'):continue
            require(service==b'reboot:\0','Unexpected reboot service arguments')
            times=[t for a,b,t in intervals[0] if a<message['end'] and b>message['offset']]
            require(times and window[0]<=min(times)<=max(times)<window[1],'Reboot outside recorded window')
            acks=[t for ack,t in pair[1]['acks'] if message['end']<=((ack-origins[0])&0xffffffff)<(1<<31)]
            okay=[m for m in messages[1] if m['command']==b'OKAY' and m['remote']==message['local']]
            require(acks,'Reboot bytes not acknowledged by peer TCP')
            requests.append(dict(first_epoch=min(times),peer_acknowledged=True,adb_okay=bool(okay)))
    require(len(requests)==1,'Not exactly one wire reboot request')
    return dict(requests=1,**requests[0])

def package_paths(run,label):
    text=(run/f'metadata/{label}-package.stdout').read_text()
    require(text.count('\nPackages:\n')==1,'Missing active package section')
    active=text.split('\nPackages:\n',1)[1].split('\nHidden system packages:',1)[0]
    blocks=[b for b in re.split(r'\n  Package ',active) if b.lstrip().startswith('[com.rigol.scope]')]
    require(len(blocks)==1,'Ambiguous active Sparrow package')
    def field(key):
        values=re.findall(r'^    '+re.escape(key)+r'=(\S+)\s*$',blocks[0],re.M)
        require(len(values)==1,'Missing package field '+key);return values[0]
    code=field('codePath');native=field('legacyNativeLibraryDir')
    require(re.fullmatch(r'/data/app/com\.rigol\.scope-[A-Za-z0-9_-]+',code) and native==code+'/lib','Unexpected package path')
    require(field('primaryCpuAbi')=='arm64-v8a' and field('userId')=='1000','Package ABI/UID differs')
    require((run/f'metadata/{label}-package-path.stdout').read_text().strip()=='package:'+code+'/base.apk','Package lookup differs')
    require((run/f'metadata/{label}-native-dirs.stdout').read_text().splitlines()==[native+'/arm64'],'Native directory selection differs')
    require((run/f'metadata/{label}-native-canonical.stdout').read_text().splitlines()==[code,native,native+'/arm64'],'Native path is not canonical')
    return code+'/base.apk',native+'/arm64/libscope-auklet.so'


def sidecar_file(run,label,path):
    fields=(run/f'metadata/{label}-ownership.stdout').read_text().split()
    require(len(fields)==8 and fields[:4]==['-rw-r--r--','1','1000','1000'] and fields[4]=='12453760' and fields[-1]==path,'Sidecar mode/owner/size differs')
    require(sha(run/f'metadata/{label}-libscope-auklet.so')==DERIVED_PIN,'Retained sidecar bytes differ')


def verify_deployment(run,predecessor,predecessor_seal,events,snapshots,archives,mode,i):
    require(mode in ('deploy','persistence'),'Unsupported success profile')
    control=read(run/'control/predecessor.toml')
    seal=predecessor_seal or ('526628e2db6504925c44e61536d24e8b377243b364772de10b14a414b0f1ecc1' if mode=='deploy' else None)
    require(seal is not None and re.fullmatch('[0-9a-f]{64}',seal),'Persistence requires independently supplied predecessor seal')
    require(control['seal']==seal and sha(predecessor/'artifacts.toml')==seal and control['mode']==mode,'Predecessor seal/profile differs')
    require(Path(control['run_directory']).name==predecessor.name,'Wrong predecessor directory')
    members={}
    for item in read(predecessor/'artifacts.toml')['files']:
        rel=Path(item['path']);require(not rel.is_absolute() and '..' not in rel.parts and item['path'] not in members,'Unsafe or duplicate sealed member')
        require(sha(predecessor/rel)==item['sha256'],'Predecessor evidence changed');members[item['path']]=item['sha256']
    members['artifacts.toml']=seal
    for item in control['files']:require(members.get(item['path'])==item['sha256'],'Predecessor selected member outside seal')
    require(control['baseline_archive']=='metadata/data-post60.tar','Unexpected baseline archive')
    baseline=i.archive(predecessor/control['baseline_archive'])
    verify_calibration({'before':baseline,'postboot':archives['before'],'post60':archives['before']})
    require(snapshots['before']['boot_id']==(predecessor/'metadata/post60-boot.stdout').read_text().strip(),'Intervening unrecorded boot')
    previous_verdict=read(predecessor/'independent-validation.toml')
    expected_band=17 if mode=='deploy' else 18
    require(previous_verdict['result']=='accepted' and previous_verdict['raw_bandwidth']==previous_verdict['effective_bandwidth']==expected_band,'Predecessor independent policy verdict differs')
    if mode=='persistence':
        previous_result=read(predecessor/'d-capability-result.toml')
        require(previous_result['result']=='accepted-by-controller' and previous_result['profile']=='deploy','Persistence predecessor is not accepted deployment')
    apk,target=package_paths(run,'selection')
    require(sha(run/'metadata/selection-Sparrow.apk')==i.APK_PIN and sha(run/'control/libscope-auklet.so')==DERIVED_PIN,'Selected APK/native input differs')
    with zipfile.ZipFile(run/'metadata/selection-Sparrow.apk') as z:
        stock=z.read('lib/arm64-v8a/libscope-auklet.so')
    derived=(run/'control/libscope-auklet.so').read_bytes()
    require(hashlib.sha256(stock).hexdigest()=='4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e','Stock embedded ancestor differs')
    original=bytes.fromhex('ea0740f94801088b0b1940b9e80f40f90b0100b9e81780b9287d089b4801088b')
    replacement=bytes.fromhex('1f010bf10bc102916801889aea0740f94801088b0b1940b9e90f40f92b0100b9')
    require(stock[0x42949c:0x4294bc]==original and derived==stock[:0x42949c]+replacement+stock[0x4294bc:],'Derived native transformation differs')
    for label,epoch in snapshots.items():
        require(package_paths(run,label)==(apk,target),'Package/native path changed across boot')
        derived=mode=='persistence' or label!='before'
        require(epoch['library']==(target if derived else apk),'Wrong native backing selected')
        rows=[line.split(None,5) for line in (run/f'metadata/{label}-maps.stdout').read_text().splitlines()]
        mapped={x[5] for x in rows if len(x)==6}
        native_paths={x for x in mapped if x.endswith('/libscope-auklet.so')}
        require(native_paths==({target} if derived else set()),'Ambiguous native mapping')
        if derived:
            sidecar_file(run,label,target)
            require(not any(len(x)==6 and x[5]==apk and 'x' in x[1] for x in rows),'Stock APK executable mapping remains alongside derived native')
    commands={e['name']:e for e in events if e['event']=='adb-command'}
    if mode=='deploy':
        proof=read(run/'introduced-file.toml');temporary=target+'.'+run.name+'.tmp'
        require(package_paths(run,'pre-rename')==(apk,target),'Package path changed before rename')
        transfer_intent=read(run/'transfer-intent.toml')
        require(transfer_intent==dict(target=target,temporary=temporary,sha256=DERIVED_PIN,original_target_absent=True,original_temporary_absent=True),'Transfer intent differs')
        require(proof==dict(schema_version=1,target=target,temporary=temporary,sha256=DERIVED_PIN,original_absent=True,mode='deploy'),'Introduced file proof differs')
        for label,path in [('temporary',temporary),('introduced',target)]:sidecar_file(run,label,path)
        import shlex
        expected={
            'sidecar-absent':'test ! -e '+shlex.quote(target)+' && test ! -L '+shlex.quote(target),
            'temporary-absent':'test ! -e '+shlex.quote(temporary)+' && test ! -L '+shlex.quote(temporary),
            'sidecar-metadata':'chown 1000:1000 '+shlex.quote(temporary)+' && chmod 0644 '+shlex.quote(temporary),
            'sidecar-rename':'test ! -e '+shlex.quote(target)+' && test ! -L '+shlex.quote(target)+' && mv '+shlex.quote(temporary)+' '+shlex.quote(target)}
        for name,command in expected.items():require(name in commands and commands[name]['argv'][-3:]==['shell','-T',command],'Deployment command differs: '+name)
        transfer=commands['sidecar-transfer']['argv'];require(transfer[-3]=='push' and Path(transfer[-2]).name=='libscope-auklet.so' and transfer[-1]==temporary,'Native transfer target differs')
        names=[e['name'] for e in events if e['event']=='adb-command']
        require(names.index('sidecar-absent')<names.index('sidecar-transfer')<names.index('temporary-native-pull')<names.index('sidecar-rename')<names.index('introduced-native-pull')<names.index('normal-reboot'),'Deployment ordering differs')
        intents=[e for e in events if e['event']=='sidecar-rename-intent'];introduced=[e for e in events if e['event']=='sidecar-introduced']
        require(len(intents)==len(introduced)==1 and intents[0]['target']==introduced[0]['target']==target and intents[0]['sha256']==introduced[0]['sha256']==DERIVED_PIN,'Introduction events differ')
    else:
        sidecar_file(run,'retained',target)
        require(not any(e['event'] in ('sidecar-rename-intent','sidecar-introduced','rollback-sidecar-removed') for e in events),'Persistence phase changed native file')
        require(not any(name.startswith(('sidecar-','temporary-','introduced-','rollback-')) for name in commands),'Persistence phase contains deployment/removal commands')
    require(all(sha(run/f'metadata/ui-{label}.png') and (run/f'metadata/ui-{label}.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for label in snapshots),'UI screenshot missing/invalid')
    return seal

def verify(run,source,tools_root,predecessor,predecessor_seal=None):
    i=module(tools_root/'bench/verify-ordinary-install.py','ordinary_install_evidence',INSTALL_VERIFIER_PIN)
    require((run/'live/DONE').is_file() and not any((run/'live'/p).exists() for p in ('STOP','STOPPED','REMOTE_HELPER_UNRESOLVED')),'Reboot run incomplete/stopped')
    expected_control=read(run/'control-sha256.toml')['files'];inventory={x['path']:x['sha256'] for x in expected_control}
    require(len(inventory)==len(expected_control),'Duplicate frozen control entry')
    require(inventory=={'control/'+p.name:sha(p) for p in (run/'control').iterdir() if p.is_file()},'Frozen controls changed')
    source_manifest=source/'sealed-sha256.txt';require(sha(source_manifest)==i.SOURCE_SEAL,'Source catalog seal differs')
    member_hashes=dict((line.split('  ',1)[1],line.split('  ',1)[0]) for line in source_manifest.read_text().splitlines())
    licenses={}
    for name,_ in i.ORDER:
        rel='phases/reboot-reload/after-rigol/data/'+name+'.lic';p=source/rel;require(sha(p)==member_hashes[rel],'Source license differs');licenses['data/'+name+'.lic']=p.read_bytes()
    plan=read(run/'control/request-plan.toml');require(plan['source_seal']==i.SOURCE_SEAL and len(plan['requests'])==10,'Source plan differs')
    for item,(name,selector) in zip(plan['requests'],i.ORDER):require(item['option_name']==name and item['status_selector']==selector and item['stock_saved_license_sha256']==hashlib.sha256(licenses['data/'+name+'.lic']).hexdigest(),'Candidate plan differs')
    protected=read(run/'control/expected-protected-files.toml')['files'];pins={x['path']:x['sha256'] for x in protected}
    require(len(pins)==len(protected)==12 and set(pins)==set(licenses)|{'data/Key.data','data/vendor.bin'},'Protected inventory differs')
    events=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
    bad={'STOP','RESTORATION_FAILURE','RECORDER_FAILURE','LEASE_HELPER_FAILURE','disconnect-error','REMOTE_HELPER_UNRESOLVED','SUPERVISOR_HOLD'}
    require(not any(e['event'] in bad for e in events),'Controller/lifecycle failure')
    def one(kind):
        values=[e for e in events if e['event']==kind];require(len(values)==1,'Missing or duplicate event '+kind);return values[0]
    one('capture-ready');one('host-address-added');one('host-address-removed');one('isolation-restored')
    require(one('recorder-stopped')['code']==0,'Recorder did not exit gracefully')
    commands=[e for e in events if e['event']=='adb-command'];require(len({e['name'] for e in commands})==len(commands),'Duplicate ADB command name');results={e['name']:e for e in events if e['event']=='adb-result'}
    reboots=[e for e in commands if e['argv'][-1:] == ['reboot']];require(len(reboots)==1 and reboots[0]['name']=='normal-reboot','Not exactly one normal reboot request')
    reboot_result=read(run/'metadata/reboot-result.toml')
    require(reboot_result['retransmitted'] is False,'Reboot was retransmitted')
    timeout_events=[e for e in events if e['event']=='reboot-client-timeout']
    returned_events=[e for e in events if e['event']=='reboot-client-returned']
    require(len(timeout_events)+len(returned_events)==1,'Missing/ambiguous reboot client outcome')
    if timeout_events:
        require(reboot_result['returncode']==124 and reboot_result['transport_timeout_or_failure'] is True and timeout_events[0]['retransmitted'] is False and 'normal-reboot' not in results,'Timeout evidence differs')
    else:
        require(results['normal-reboot']['code']==returned_events[0]['code']==reboot_result['returncode'] and reboot_result['transport_timeout_or_failure'] is (reboot_result['returncode']!=0),'Client return evidence differs')
    roots=[e for e in commands if e['argv'][-1:]==['root']];root_events=[e for e in events if e['event']=='single-postboot-adbd-root-request']
    require(len(roots)==len(root_events)<=1 and all(e['name']=='postboot-root-once' and results[e['name']]['code']==0 for e in roots),'Root restart budget differs')
    for e in events:
        if e['event']=='adb-result' and e['name']!='normal-reboot' and not e['name'].startswith(('reconnect-','boot-ready-','ui-ready-')):require(e['code']==0,'Required ADB command failed')
        if e['event']=='host':require(e['code']==0,'Host isolation command failed')
    require(not any('install' in e['name'].lower() for e in commands),'Unexpected installer command')
    snapshots={e['phase']:e for e in events if e['event']=='process-snapshot'};require(set(snapshots)=={'before','postboot','post60'},'Process snapshot set differs')
    before,postboot,post60=[snapshots[n] for n in ('before','postboot','post60')]
    require(before['boot_id']!=postboot['boot_id'] and (postboot['pid'],postboot['starttime'],postboot['boot_id'])==(post60['pid'],post60['starttime'],post60['boot_id']),'Boot transition or postboot continuity differs')
    for label,epoch in snapshots.items():
        require(i.process_identity(run/('metadata/'+label+'-stat.stdout'))==(epoch['pid'],int(epoch['starttime'])),'Recorded process epoch differs')
        require((run/('metadata/'+label+'-boot.stdout')).read_text().strip()==epoch['boot_id'],'Recorded boot differs')
        require((run/('metadata/'+label+'-cmdline.stdout')).read_bytes().split(b'\0')[0]==b'com.rigol.scope','Wrong process')
        require(sha(run/('metadata/'+label+'-Sparrow.apk'))==i.APK_PIN,'Stock APK changed')
        activity=(run/('metadata/'+label+'-activity.stdout')).read_text();require(any('mResumedActivity' in line and 'com.rigol.scope/' in line for line in activity.splitlines()),'Sparrow not resumed')
        require(any(line.split()[-1]==epoch['library'] for line in (run/('metadata/'+label+'-maps.stdout')).read_text().splitlines()),'APK map path absent')
    require(i.process_identity(run/'metadata/target-stat-after.stdout')==(post60['pid'],int(post60['starttime'])),'Process changed after reader')
    require((run/'metadata/target-boot-after.stdout').read_text().strip()==post60['boot_id'],'Boot changed after reader')
    requested=one('single-reboot-requested');complete=one('d-capability-controller-complete')
    require(requested['old_boot_id']==before['boot_id'] and complete['old_boot_id']==before['boot_id'] and complete['new_boot_id']==post60['boot_id'] and complete['root_restart_used']==bool(roots),'Reboot controller epochs differ')
    opened=one('reboot-window-opened');closed=one('reboot-window-closed')
    require(0<opened['deadline_epoch']-opened['epoch']<=180.001 and opened['epoch']<closed['epoch']<=opened['deadline_epoch'] and closed['reason']=='readiness-proven','Reboot readiness window differs')
    require(not (run/'live/REBOOT_PENDING').exists(),'Reboot marker remains')
    require(one('reboot-lease-invalidated')['requires_fresh_captured_ack'] is True,'Old lease reused across reboot')
    connections=[e for e in events if e['event']=='scpi-connected'];require(len(connections)==3 and [e['phase'] for e in connections]==list(PHASES),'SCPI phase count/order differs')
    require((datetime.fromisoformat(connections[2]['utc'])-datetime.fromisoformat(connections[1]['utc'])).total_seconds()>=60,'Missing60-second persistence interval')
    identity=(run/'control/expected-identity.bin').read_bytes();expected={s:int(s!='BND') for s in i.SELECTORS};logs={}
    for phase in PHASES:
        d=run/phase;require(sorted(p.name for p in d.iterdir())==sorted(f'{n:02d}-{kind}.bin' for n in range(12) for kind in ('request','response')),'Unexpected SCPI artifacts')
        replies=[]
        for n,query in enumerate(i.REQUESTS):
            require((d/f'{n:02d}-request.bin').read_bytes()==query,'Unexpected SCPI request');reply=(d/f'{n:02d}-response.bin').read_bytes();replies.append(reply)
            require(reply.endswith(b'\n') and reply.count(b'\n')==1,'SCPI framing differs')
            if n==0:require(reply.strip()==identity.strip(),'Identity changed')
            else:require(reply in ((b'0\n',b'0\r\n') if i.SELECTORS[n-1]=='BND' else (b'1\n',b'1\r\n')),'Option not persistent')
        require(read(run/(phase+'.toml'))==expected,'Status summary differs');logs[phase]=(b''.join(i.REQUESTS),b''.join(replies))
    lease=read(run/'control/lease.toml');require(lease['lease_seconds']==21600 and not lease['router_option'] and not lease['dns_option'],'Unexpected isolated lease configuration')
    actual,capture=streams(run/'live/capture.pcap',connections,i.reconstruct,lease,(opened['epoch'],closed['epoch']));require(actual==logs,'Raw three-stream SCPI transcript differs')
    fresh_acks=[epoch for epoch in capture['dhcp_ack_epochs'] if opened['epoch']<=epoch<closed['epoch']]
    require(fresh_acks,'No fresh ACK captured during requested reboot')
    reconnects=[e for e in commands if e['name'].startswith('reconnect-')]
    require(reconnects and datetime.fromisoformat(reconnects[0]['utc']).timestamp()>=min(fresh_acks),'Reconnect preceded fresh captured ACK')
    recorded_releases=[e['packet_epoch'] for e in events if e['event']=='reboot-release-captured']
    require(recorded_releases==capture['dhcp_release_epochs'],'Recorded release events differ from wire')
    require(all(any(abs((e['expires_epoch']-21600)-epoch)<0.001 for e in events if e['event']=='ack-captured') for epoch in fresh_acks),'Fresh wire ACK missing controller witness')
    cv=read(run/'capture-validation.toml')
    for key in ('capture_frames','capture_bytes','pcap_sha256'):require(cv[key]==capture[key],'Capture validation differs')
    require(cv['kernel_drops']==0 and cv['all_frame_lengths_complete'] is True and cv['all_frames_passed_recorded_network_classifier'] is True,'Capture validation failed')
    stats=(run/'live/capture.stderr').read_text();drops=re.findall(r'(\d+) packets dropped by kernel',stats);require(drops and all(int(x)==0 for x in drops),'Capture dropped packets')
    for text,key in [('packets captured','capture_frames'),('packets received by filter','received_counter')]:
        values=re.findall(r'(?m)^(\d+) '+text+'$',stats);require(values and int(values[-1])==cv[key],'Capture final counter differs')
    archives={}
    for label in ('before','postboot','post60'):
        data=i.archive(run/('metadata/data-'+label+'.tar'));archives[label]=data
        require({n:b for n,b in data.items() if n.endswith('.lic')}==licenses,'Cumulative license bytes differ')
        require(all(n in data and hashlib.sha256(data[n]).hexdigest()==h for n,h in pins.items()),'Protected file changed')
        summary=read(run/('metadata/data-'+label+'-sha256.toml'))['files'];require(len(summary)==len(data) and {x['path']:x['sha256'] for x in summary}=={n:hashlib.sha256(b).hexdigest() for n,b in data.items()},'Logical archive summary differs')
    changed=sorted(n for n in set(archives['before'])|set(archives['post60']) if archives['before'].get(n)!=archives['post60'].get(n));require(read(run/'data-delta.toml')['changed_after_reboot']==changed,'Logical delta summary differs')
    enforcement=(run/'metadata/enforcement-before.stdout').read_bytes();require(enforcement in (b'Enforcing\n',b'Permissive\n',b'Disabled\n') and enforcement==(run/'metadata/enforcement-after.stdout').read_bytes(),'Enforcement changed')
    bandwidth = verify_derived_observation(run,tools_root,post60)
    observation=one('observation-ready');require((observation['pid'],observation['starttime'],observation['boot_id'],observation['library'])==(post60['pid'],post60['starttime'],post60['boot_id'],post60['library']),'Reader launch epoch differs')
    exited=one('cached-helper-exit-proven');require(exited['exit_status']==0 and exited['cleanup'] is False,'Helper exit not proven')
    hp=(run/'metadata/lifecycle-pid-False.stdout').read_text().strip();require(hp.isdigit() and int(hp)==exited['pid'],'Helper PID differs')
    require(i.process_identity(run/'metadata/lifecycle-stat-False.stdout')==(int(hp),int(exited['starttime'])),'Helper start epoch differs')
    stage=observation['staging_directory'];argv=[stage+'/reader',str(post60['pid']),post60['starttime'],post60['boot_id'],post60['library'],stage+'/observation','positive']
    require((run/'metadata/lifecycle-argv-False.stdout').read_bytes()==b''.join(s.encode()+b'\0' for s in argv),'Helper argv differs')
    require((run/'metadata/lifecycle-state-False.stdout').read_bytes().strip()==b'exit 0','Remote wait result differs')
    lifecycle=[e for e in events if e['event']=='lifecycle-command'];require(lifecycle and all(e['code']==0 for e in lifecycle),'Lifecycle proof command failed')
    delta = verify_calibration(archives)
    profile=read(run/'d-capability-result.toml')['profile']
    require(complete['mode']==profile,'Completion profile differs')
    predecessor_pin=verify_deployment(run,predecessor,predecessor_seal,events,snapshots,archives,profile,i)
    delivery = verify_reboot_wire(run/'live/capture.pcap', lease, (opened['epoch'],closed['epoch']))
    result=read(run/'d-capability-result.toml');require(result['result']=='accepted-by-controller' and result['reboots_requested']==1 and result['changed_boot_id'] is True and result['ordinary_options_enabled']==10 and result['bundle_enabled'] is False and result['process_bytes_read']==16 and result['raw_bandwidth_enum']==result['effective_bandwidth_enum']==18 and result['protected_files_unchanged'] is True,'Completion summary differs')
    return dict(schema='mho900-lab.physical-d-capability-verification/1',result='accepted',profile=profile,predecessor_seal=predecessor_pin,reboots_requested=1,boot_identity_changed=True,
                postboot_process_stable=True,ordinary_options_enabled=10,bundle_enabled=False,scpi_streams=3,
                scpi_queries=36,install_requests=0,wire_transcripts_equal=True,protected_files_unchanged=12,
                raw_bandwidth=18,effective_bandwidth=18,process_bytes_read=16,reader_exit_proven=True,
                enforcement_unchanged=True,enforcement_state=enforcement.decode().strip(),postboot_adbd_root_requests=len(roots),
                capture_frames=capture['capture_frames'],pcap_sha256=capture['pcap_sha256'],kernel_drops=0,recorder_exit=0,
                fresh_isolated_lease_after_reboot=True,reboot_dhcp_releases=len(capture['dhcp_release_epochs']),
                logical_changed_paths=changed,source_catalog_seal=i.SOURCE_SEAL,ui_resumed=True,ui_visual_semantics_verified=False,
                atomic_snapshot_claimed=False,reboot_wire_requests=delivery['requests'],reboot_peer_acknowledged=delivery['peer_acknowledged'],reboot_adb_okay=delivery['adb_okay'],calibration_payload_unchanged=True,identity_cache_contents_authenticated=False,verifier_sha256=sha(Path(__file__)))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--source-catalog',type=Path,required=True);p.add_argument('--predecessor',type=Path,required=True);p.add_argument('--predecessor-seal');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Output already exists');values=verify(a.run,a.source_catalog,Path(__file__).resolve().parents[1],a.predecessor,a.predecessor_seal)
    a.output.write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in values.items()));print(json.dumps(values))

if __name__=='__main__':main()
