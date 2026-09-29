#!/usr/bin/env python3
"""Offline verification of one physical ordinary installer transition.

Only retained files are read. No sockets, subprocesses, device access or token
production. Public results contain option names and evidence facts, not identities
or license contents. TCP retransmissions are deduplicated by sequence and must
agree byte-for-byte; gaps, conflicts and extra SCPI streams are rejected.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import socket
import struct
import tarfile
import tomllib

SOURCE_SEAL='0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781'
APK_PIN='6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
ORDER=(('FlexA','FLEX'),('BWU05T08','BWU05T08'),('AFG100','AFG100'),('AFG50','AFG50'),('AUDIOA','AUDio'),('AUTOA','CAN-FD'),('AEROA','AERO'),('RLU05','RLU-05'),('BWU03T05','BWU03T05'),('BWU03T08','BWU03T08'))
SELECTORS=('BND','AFG100','AFG50','AUDio','CAN-FD','FLEX','AERO','RLU-05','BWU03T05','BWU03T08','BWU05T08')
REQUESTS=(b'*IDN?\n',)+tuple((':SYSTem:OPTion:STATus? '+s+'\n').encode() for s in SELECTORS)

def require(ok,reason):
    if not ok:raise ValueError(reason)
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(path.read_bytes())
def read(path):return tomllib.loads(path.read_text())
def integer(value):return type(value) is int

def reconstruct(segments,syns,fins):
    require(len(syns)==1,'Missing or ambiguous TCP initial sequence')
    origin=(next(iter(syns))+1)&0xffffffff;data={};retransmitted=0
    for seq,payload in segments:
        at=(seq-origin)&0xffffffff
        require(at<1048576 and at+len(payload)<=1048576,'TCP sequence outside bounded SCPI extent')
        for i,byte in enumerate(payload):
            offset=at+i
            if offset in data:
                require(data[offset]==byte,'Conflicting TCP retransmission');retransmitted+=1
            else:data[offset]=byte
    extent=max(data,default=-1)+1
    require(len(data)==extent,'Gap in captured TCP byte sequence')
    require(len(fins)==1 and ((next(iter(fins))-origin)&0xffffffff)==extent,'Missing or inconsistent TCP FIN extent')
    return bytes(data[i] for i in range(extent)),retransmitted

def pcap_stream(path,local,peer):
    host_ip,host_port=local;peer_ip,peer_port=peer
    require(peer_port==5555,'Unexpected SCPI endpoint port')
    direction={0:dict(segments=[],syns=set(),fins=set()),1:dict(segments=[],syns=set(),fins=set())}
    count=0;tcp_frames=0;total=0;h=hashlib.sha256()
    with path.open('rb') as f:
        header=f.read(24);h.update(header);total+=len(header)
        require(len(header)==24 and header[:4]==b'\xd4\xc3\xb2\xa1','Unsupported/truncated pcap header')
        require(struct.unpack_from('<HH',header,4)==(2,4) and struct.unpack_from('<I',header,20)[0]==1,'Not Ethernet pcap2.4')
        while True:
            record=f.read(16)
            if not record:break
            require(len(record)==16,'Truncated pcap record header')
            sec,usec,n,original=struct.unpack('<IIII',record)
            require(usec<1000000 and n==original and 14<=n<=262144,'Truncated or invalid captured frame')
            raw=f.read(n);require(len(raw)==n,'Truncated pcap frame');h.update(record);h.update(raw);total+=16+n;count+=1
            ethertype=struct.unpack_from('!H',raw,12)[0]
            if ethertype!=0x0800:continue
            require(len(raw)>=34 and raw[14]>>4==4,'Invalid IPv4 frame')
            ihl=(raw[14]&15)*4;length=struct.unpack_from('!H',raw,16)[0]
            require(ihl>=20 and length>=ihl and 14+length<=len(raw),'Invalid IPv4 length')
            if raw[23]!=6:continue
            require(struct.unpack_from('!H',raw,20)[0]&0x3fff==0,'Fragmented TCP is outside capture profile')
            at=14+ihl;require(length>=ihl+20,'Short TCP header')
            sport,dport,seq=struct.unpack_from('!HHI',raw,at)
            if sport!=5555 and dport!=5555:continue
            src=socket.inet_ntoa(raw[26:30]);dst=socket.inet_ntoa(raw[30:34])
            if (src,sport,dst,dport)==(host_ip,host_port,peer_ip,peer_port):key=0
            elif (src,sport,dst,dport)==(peer_ip,peer_port,host_ip,host_port):key=1
            else:raise ValueError('Extra or unexpected SCPI TCP stream')
            tcp_frames+=1;size=(raw[at+12]>>4)*4;flags=raw[at+13]
            require(size>=20 and ihl+size<=length and not flags&4,'Invalid or reset SCPI TCP stream')
            payload=raw[at+size:14+length];d=direction[key]
            if flags&2:d['syns'].add(seq)
            payload_seq=(seq+(1 if flags&2 else 0))&0xffffffff
            if payload:d['segments'].append((payload_seq,payload))
            if flags&1:d['fins'].add((payload_seq+len(payload))&0xffffffff)
    request,rd=reconstruct(**direction[0]);reply,sd=reconstruct(**direction[1])
    return request,reply,dict(capture_frames=count,capture_bytes=total,pcap_sha256=h.hexdigest(),scpi_tcp_frames=tcp_frames,deduplicated_retransmitted_bytes=rd+sd)

def archive(path):
    files={};seen=set()
    with tarfile.open(path) as tar:
        for member in tar:
            name=member.name;p=PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and p.parts and p.parts[0]=='data','Unsafe/non-data archive member')
            require(name not in seen,'Duplicate archive member');seen.add(name)
            require(member.isdir() or member.isfile(),'Archive has unsupported links/special files')
            if member.isfile():
                stream=tar.extractfile(member);data=stream.read();require(len(data)==member.size,'Short archive member');files[name]=data
    return files

def process_identity(path):
    text=path.read_text().strip();match=re.fullmatch(r'([1-9][0-9]*) \((.*)\) (.*)',text)
    require(match is not None,'Malformed process stat');fields=match.group(3).split()
    require(len(fields)>=20 and fields[19].isdigit(),'Missing process starttime')
    return int(match.group(1)),int(fields[19])

def verify(run,source):
    require((run/'live/DONE').is_file() and not any((run/'live'/n).exists() for n in ('STOP','STOPPED')),'Run incomplete/stopped')
    # Pin the previously accepted source manifest; verify each candidate member
    # used here against that manifest instead of trusting the local request plan.
    manifest=source/'sealed-sha256.txt';require(sha(manifest)==SOURCE_SEAL,'Accepted source seal differs')
    source_hashes={}
    for row in manifest.read_text().splitlines():
        h,name=row.split('  ',1);require(name not in source_hashes,'Duplicate source seal member');source_hashes[name]=h
    def source_bytes(name):
        p=source/name;require(name in source_hashes and sha(p)==source_hashes[name],'Accepted source member changed');return p.read_bytes()
    plan=read(run/'control/request-plan.toml');require(plan['source_seal']==SOURCE_SEAL and plan['source_phase']=='reboot-reload','Request plan source differs')
    require(plan['requests_sent'] is False and plan['token_generation_performed'] is False,'Preparation plan semantics differ')
    require(len(plan['requests'])==len(ORDER),'Request plan candidate count differs')
    licenses={};requests={}
    for index,(name,selector) in enumerate(ORDER):
        candidate=plan['requests'][index];require(candidate['option_name']==name and candidate['status_selector']==selector,'Candidate order/selector differs')
        lic=source_bytes('phases/reboot-reload/after-rigol/data/'+name+'.lic')
        witness=source_bytes('phases/reboot-reload/after-model/crypto-'+name+'.toml');w=tomllib.loads(witness.decode())
        require(w['phase']=='positive' and w['option_name']==name and w['padded_bytes']==48,'Source candidate witness differs')
        require(lic==(name+'@'+w['wire_token_hex']+'\n').encode(),'Source wire/license mismatch')
        request=b':SYSTem:OPTion:INSTall MHO900-'+lic
        require(digest(lic)==candidate['stock_saved_license_sha256'] and digest(witness)==candidate['witness_sha256'] and digest(request)==candidate['sha256'],'Candidate provenance hashes differ')
        require(candidate['expected_status_before']==0 and candidate['expected_status_after']==1,'Candidate transition differs')
        licenses[name]=lic;requests[name]=request
    config=read(run/'control/config.toml');index=config['option_index'];require(integer(index) and 0<=index<len(ORDER),'Candidate index invalid')
    name,selector=ORDER[index];expected_enabled=[x[1] for x in ORDER[:index]]
    require(len(config['expected_enabled'])==len(expected_enabled) and set(config['expected_enabled'])==set(expected_enabled),'Cumulative baseline differs')
    pinned=read(run/'control-sha256.toml')['files'];seen=set()
    for item in pinned:
        p=PurePosixPath(item['path']);require(not p.is_absolute() and '..' not in p.parts and p.parts[0]=='control','Unsafe control member')
        require(str(p) not in seen and sha(run/str(p))==item['sha256'],'Control input changed');seen.add(str(p))
    require(seen=={'control/'+p.name for p in (run/'control').iterdir() if p.is_file()},'Frozen control inventory differs')
    events=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
    bad={'STOP','RESTORATION_FAILURE','RECORDER_FAILURE','LEASE_HELPER_FAILURE','disconnect-error'}
    require(not any(e['event'] in bad for e in events),'Controller/restoration error recorded')
    def one(kind):
        values=[e for e in events if e['event']==kind];require(len(values)==1,'Missing/duplicate controller event '+kind);return values[0]
    one('capture-ready');one('host-address-added');one('host-address-removed');one('isolation-restored')
    require(one('recorder-stopped')['code']==0,'Recorder exit not graceful')
    require(one('physical-option-accepted')['option']==name,'Controller candidate differs')
    ready=one('single-install-ready');require(ready['option']==name and ready['request_sha256']==digest(requests[name]),'Prepared intervention differs')
    require(all(e['code']==0 for e in events if e['event'] in ('adb-result','host')),'Controller command failed')
    identity=(run/'control/expected-identity.bin').read_bytes();require(identity.strip(),'Empty expected identity')
    status_sets=[];query_requests=[];query_responses=[]
    for label in ('scpi-before','scpi-after'):
        d=run/label;require(sorted(p.name for p in d.iterdir())==sorted([f'{i:02d}-{kind}.bin' for i in range(12) for kind in ('request','response')]),'Unexpected query artifacts')
        responses=[]
        for i,request in enumerate(REQUESTS):
            require((d/f'{i:02d}-request.bin').read_bytes()==request,'Undocumented/reordered query')
            response=(d/f'{i:02d}-response.bin').read_bytes();require(response.count(b'\n')==1 and response.endswith(b'\n'),'Malformed response framing');responses.append(response)
        require(responses[0].strip()==identity.strip(),'Identity changed')
        statuses={}
        for s,response in zip(SELECTORS,responses[1:]):
            require(response in (b'0\n',b'1\n',b'0\r\n',b'1\r\n'),'Status is not documented boolean');statuses[s]=int(response.strip())
        expected={s:int(s in expected_enabled or label=='scpi-after' and s==selector) for s in SELECTORS}
        require(statuses==expected,'Candidate-only cumulative status transition failed')
        require(statuses==read(run/('before-status.toml' if label=='scpi-before' else 'after-status.toml')),'Status summary differs from raw responses')
        status_sets.append(statuses);query_requests.append(b''.join(REQUESTS));query_responses.append(b''.join(responses))
    install=run/'install';r=read(install/'result.toml');require(r['observed'] is True and r['status']=='observed' and r['failure_type']=='','Installer not observed successful')
    polls=r['polls'];require(integer(polls) and 1<=polls<=5 and r['maximum_polls']==5 and r['deadline_seconds']==10 and r['automatic_retransmissions']==0,'Installer bounds differ')
    request=requests[name];require((run/'control/install-request.bin').read_bytes()==(install/'install-request.bin').read_bytes()==request,'Actual request differs from accepted candidate')
    require(r['request_sha256']==digest(request) and r['install_bytes_sent']==len(request) and r['selector']==selector,'Installer request accounting differs')
    query=(':SYSTem:OPTion:STATus? '+selector+'\n').encode();poll_replies=[]
    require(sorted(p.name for p in install.glob('*-request.bin') if p.name!='install-request.bin')==[f'{i:02d}-request.bin' for i in range(polls)],'Extra/missing status polls')
    require(sorted(p.name for p in install.glob('*-response.bin'))==[f'{i:02d}-response.bin' for i in range(polls)],'Extra/missing poll replies')
    for i in range(polls):
        require((install/f'{i:02d}-request.bin').read_bytes()==query,'Poll request differs')
        response=(install/f'{i:02d}-response.bin').read_bytes();require(response in ((b'1\n',b'1\r\n') if i==polls-1 else (b'0\n',b'0\r\n')),'Poll success/bounded stop differs');poll_replies.append(response)
    sends=read(install/'send-events.toml')['sends'];cursor=0
    for kind,payload in [('install',request)]+[('status-'+str(i),query) for i in range(polls)]:
        offset=0
        while cursor<len(sends) and sends[cursor]['kind']==kind:
            item=sends[cursor];require(integer(item['accepted']) and item['offset']==offset and 0<item['accepted']<=len(payload)-offset,'Send offset/count differs');offset+=item['accepted'];cursor+=1
        require(offset==len(payload),'Incomplete send evidence')
    require(cursor==len(sends),'Extra send attempt recorded')
    connection=one('scpi-connected');wire_request,wire_reply,capture=pcap_stream(run/'live/capture.pcap',connection['local'],connection['peer'])
    require(wire_request==query_requests[0]+request+query*polls+query_requests[1],'Wire requests differ from exact sole-install transcript')
    require(wire_reply==query_responses[0]+b''.join(poll_replies)+query_responses[1],'Wire replies differ from retained response logs')
    cv=read(run/'capture-validation.toml')
    for key in ('capture_frames','capture_bytes','pcap_sha256'):require(cv[key]==capture[key],'Capture validation artifact differs')
    require(cv['kernel_drops']==0 and cv['all_frame_lengths_complete'] is True and cv['all_frames_passed_recorded_network_classifier'] is True,'Capture validation failed')
    stats=(run/'live/capture.stderr').read_text()
    for text,key in [('packets captured','capture_frames'),('packets received by filter','received_counter')]:
        values=re.findall(r'(?m)^(\d+) '+text+r'$',stats);require(values and int(values[-1])==cv[key],'Missing or differing recorder counter')
    drops=re.findall(r'(\d+) packets dropped by kernel',stats);require(drops and all(int(x)==0 for x in drops),'Capture drops observed')
    before=archive(run/'metadata/data-before.tar');after=archive(run/'metadata/data-after.tar')
    for which,files in [('before',before),('after',after)]:
        expected_names={n for n,_ in ORDER[:index+(which=='after')]}
        actual_names={PurePosixPath(n).stem for n in files if n.endswith('.lic')}
        require(actual_names==expected_names,'Cumulative license file set differs')
        for n in expected_names:require(files['data/'+n+'.lic']==licenses[n],'Saved license differs from accepted source')
        summary=read(run/('metadata/data-'+which+'-sha256.toml'))['files']
        require({i['path']:i['sha256'] for i in summary}=={n:digest(b) for n,b in files.items()} and len(summary)==len(files),'Archive summary differs')
    for n in ('data/Key.data','data/vendor.bin'):require(n in before and before[n]==after.get(n),'Key/vendor changed')
    for n,b in before.items():
        if n.endswith('.lic'):require(after.get(n)==b,'Prior license changed')
    target='data/'+name+'.lic';require(target not in before and after[target]==licenses[name],'Candidate file transition differs')
    changed=sorted(n for n in set(before)|set(after) if before.get(n)!=after.get(n));require(read(run/'data-delta.toml')['changed_paths']==changed,'Data delta summary differs')
    require(changed==[target],'Unexpected logical data changed')
    require(process_identity(run/'metadata/target-stat.stdout')==process_identity(run/'metadata/target-stat-after.stdout'),'Target process restarted')
    require((run/'metadata/target-cmdline.stdout').read_bytes().split(b'\0')[0]==b'com.rigol.scope','Wrong target process')
    boot=(run/'metadata/target-boot.stdout').read_bytes().strip();require(re.fullmatch(rb'[0-9a-f-]{36}',boot) is not None and boot==(run/'metadata/target-boot-after.stdout').read_bytes().strip(),'Boot changed')
    enforcement=(run/'metadata/enforcement-before.stdout').read_bytes()
    require(enforcement in (b'Enforcing\n',b'Permissive\n',b'Disabled\n') and enforcement==(run/'metadata/enforcement-after.stdout').read_bytes(),'Enforcement changed')
    require(sha(run/'metadata/loaded-Sparrow.apk')==APK_PIN,'Active stock APK differs')
    controller=read(run/'install-result.toml');require(controller['result']=='accepted-by-controller' and controller['option']==name and controller['physical_install_requests']==1 and controller['reboot_performed'] is False,'Controller completion differs')
    return dict(schema='mho900-lab.ordinary-install-verification/1',result='accepted',option=name,documented_statuses=11,
                cumulative_enabled_options=index+1,physical_install_requests=1,status_polls=polls,
                single_scpi_stream=True,wire_request_reply_logs_equal=True,prior_license_key_vendor_unchanged=True,
                candidate_file_matches_accepted_guest=True,logical_data_changed_only_candidate=True,
                process_and_boot_unchanged=True,enforcement_unchanged=True,enforcement_state=enforcement.decode().strip(),recorder_exit=0,kernel_drops=0,
                capture_frames=capture['capture_frames'],pcap_sha256=capture['pcap_sha256'],
                scpi_tcp_frames=capture['scpi_tcp_frames'],deduplicated_retransmitted_bytes=capture['deduplicated_retransmitted_bytes'],
                source_catalog_seal=SOURCE_SEAL,reboot_persistence_tested=False,ui_semantics_independently_verified=False,
                verifier_sha256=sha(Path(__file__)))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--source-catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Output already exists');v=verify(a.run,a.source_catalog)
    a.output.write_text(''.join(k+' = '+json.dumps(value)+'\n' for k,value in v.items()));print(json.dumps(v))

if __name__=='__main__':main()
