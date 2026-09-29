#!/usr/bin/env python3
"""Offline proof of ordinary-option persistence across one physical reboot.

Reads retained evidence only. It never sends commands or connects to a device.
The three SCPI streams, source licenses, logical archives, process epochs and
fixed stock-APK bandwidth samples are independently reconciled.
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
sys.dont_write_bytecode=True
INSTALL_VERIFIER_PIN='3b589c2022e6881a43f1ab4a95a74ad3176ca0a2fff4179dd694d20fa3c2d551'
APK_ORACLE_PIN='79878ae2e3718dd71c6ef5dac83830c86a8623d3c3b0b97d54340f1d592f906e'
GEOMETRY_PIN='8730784f02aa0645edea5716c6cdcdab90d0f60c75a68a340b0e4a9674361ec2'
READER_PIN='111ae759668e89d13090fc4ac1a930072d9cccc715b4f6b819cdcbf89b6dc4d8'
RANGES=((0xbbcce4,4,0xbbbce4),(0xbbcce8,4,0xbbbce8))
PHASES=('scpi-before','scpi-postboot','scpi-post60')

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return tomllib.loads(p.read_text())
def module(path,name,pin):
    require(sha(path)==pin,'Verifier dependency differs: '+path.name)
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def streams(path,connections,reconstruct,lease=None,window=None):
    expected={};directions={};packet_counts={}
    for c in connections:
        host,hport=c['local'];peer,pport=c['peer'];phase=c['phase'];require(pport==5555,'Unexpected SCPI endpoint')
        forward=(host,hport,peer,pport);reverse=(peer,pport,host,hport)
        require(forward not in expected and reverse not in expected,'SCPI endpoint reused ambiguously')
        expected[forward]=(phase,0);expected[reverse]=(phase,1)
        directions[phase]={0:dict(segments=[],syns=set(),fins=set()),1:dict(segments=[],syns=set(),fins=set())};packet_counts[phase]=0
    h=hashlib.sha256();count=0;total=0;acks=[];releases=[]
    with path.open('rb') as f:
        header=f.read(24);h.update(header);total+=len(header)
        require(len(header)==24 and header[:4]==b'\xd4\xc3\xb2\xa1' and struct.unpack_from('<HH',header,4)==(2,4) and struct.unpack_from('<I',header,20)[0]==1,'Invalid Ethernet pcap')
        while True:
            hdr=f.read(16)
            if not hdr:break
            require(len(hdr)==16,'Truncated pcap record');sec,usec,n,original=struct.unpack('<IIII',hdr)
            require(usec<1000000 and n==original and 14<=n<=262144,'Incomplete captured frame')
            raw=f.read(n);require(len(raw)==n,'Truncated captured frame');h.update(hdr);h.update(raw);count+=1;total+=16+n
            if struct.unpack_from('!H',raw,12)[0]!=0x800:continue
            require(len(raw)>=34 and raw[14]>>4==4,'Malformed IPv4')
            ihl=(raw[14]&15)*4;length=struct.unpack_from('!H',raw,16)[0]
            require(ihl>=20 and length>=ihl and 14+length<=len(raw),'Malformed IPv4 length')
            if raw[23]==17:
                at=14+ihl;require(length>=ihl+8,'Short UDP header')
                sport,dport,udplen=struct.unpack_from('!HHH',raw,at)
                require(8<=udplen<=length-ihl,'Invalid UDP length')
                if (sport,dport) in ((67,68),(68,67)) and lease is not None:
                    require(struct.unpack_from('!H',raw,20)[0]&0x3fff==0,'Fragmented DHCP')
                    payload=raw[at+8:at+udplen]
                    require(len(payload)>=240 and payload[236:240]==bytes.fromhex('63825363'),'Invalid DHCP cookie')
                    require(payload[2]==6 and payload[28:34]==bytes.fromhex(lease['client_mac'].replace(':','')),'Unexpected DHCP client')
                    options={};pos=240
                    while pos<len(payload):
                        tag=payload[pos];pos+=1
                        if tag==255:break
                        if tag==0:continue
                        require(pos<len(payload),'Truncated DHCP option');nopt=payload[pos];pos+=1
                        require(pos+nopt<=len(payload) and tag not in options,'Truncated/duplicate DHCP option')
                        options[tag]=payload[pos:pos+nopt];pos+=nopt
                    require(53 in options and len(options[53])==1,'Missing DHCP message type')
                    kind=options[53][0];epoch=sec+usec/1e6
                    require(kind!=4,'DHCP DECLINE occurred')
                    if kind==7:
                        require(window is not None and window[0]<=epoch<window[1],'DHCP RELEASE outside reboot window');releases.append(epoch)
                    if sport==67:
                        require(set(options)<={53,54,51,1,61} and 3 not in options and 6 not in options,'Unexpected DHCP server option')
                        require(payload[0]==2 and payload[16:20]==socket.inet_aton(lease['client_ip']) and options[54]==socket.inet_aton(lease['server_ip']),'Wrong DHCP server/lease address')
                        require(len(options[51])==4 and int.from_bytes(options[51],'big')==21600,'Unexpected lease duration')
                        if kind==5:acks.append(epoch)
                continue
            if raw[23]!=6:continue
            require(struct.unpack_from('!H',raw,20)[0]&0x3fff==0,'Fragmented TCP outside profile')
            at=14+ihl;require(length>=ihl+20,'Short TCP header');sport,dport,seq=struct.unpack_from('!HHI',raw,at)
            if sport!=5555 and dport!=5555:continue
            key=(socket.inet_ntoa(raw[26:30]),sport,socket.inet_ntoa(raw[30:34]),dport)
            require(key in expected,'Unexpected additional SCPI stream');phase,direction=expected[key];packet_counts[phase]+=1
            size=(raw[at+12]>>4)*4;flags=raw[at+13];require(size>=20 and ihl+size<=length and not flags&4,'Invalid/reset SCPI stream')
            payload=raw[at+size:14+length];d=directions[phase][direction]
            if flags&2:d['syns'].add(seq)
            offset=(seq+bool(flags&2))&0xffffffff
            if payload:d['segments'].append((offset,payload))
            if flags&1:d['fins'].add((offset+len(payload))&0xffffffff)
    values={};retransmissions=0
    for phase,ds in directions.items():
        request,reqdup=reconstruct(**ds[0]);reply,repdup=reconstruct(**ds[1]);values[phase]=(request,reply);retransmissions+=reqdup+repdup
    return values,dict(capture_frames=count,capture_bytes=total,pcap_sha256=h.hexdigest(),scpi_tcp_frames=sum(packet_counts.values()),deduplicated_retransmitted_bytes=retransmissions,dhcp_ack_epochs=acks,dhcp_release_epochs=releases)

def verify_bandwidth(run,oracle_path,pin_module,epoch):
    o=module(oracle_path,'reboot_apk_geometry',APK_ORACLE_PIN);v=o.v
    require(sha(oracle_path.with_name('verify-cached-identity.py'))==GEOMETRY_PIN,'ELF oracle dependency differs')
    v.RANGES=RANGES
    apk=run/'metadata/post60-Sparrow.apk';entry,size,loads=o.archive_entry(apk.read_bytes())
    require(entry==0xf05000 and size==12453760,'Stock embedded ELF geometry differs')
    d=run/'reader/observation';m=read(d/'manifest.toml')
    require(m['schema_version']=='mho900-lab.apk-bandwidth-reader/1' and m['mode']=='positive' and m['result']=='accepted' and m['stage']=='complete' and m['error_number']==0,'Cached observation failed')
    require(m['backing_apk_sha256']==pin_module.APK_PIN and m['library_sha256']==m['expected_library_sha256']==v.STOCK_SHA256,'Cached backing pins differ')
    require(m['embedded_elf_offset']==entry and m['embedded_elf_size']==size,'Cached container geometry differs')
    require((m['pid'],m['expected_starttime'],m['expected_boot_id'],m['library_path'])==(epoch['pid'],int(epoch['starttime']),epoch['boot_id'],epoch['library']),'Cached observation target differs')
    require(m['raw_band_size']==m['effective_band_size']==4 and v.number(m['validation_raw_band_virtual_address'])==RANGES[0][0],'Cached fixed range differs')
    require(m['maximum_memory_bytes']==m['memory_bytes_requested']==m['bytes_read']==16 and m['read_requested']==m['read_results']==[4,4,4,4],'Cached read budget differs')
    require(m['mem_open_count']==1 and m['mem_open_flags']==0 and m['memory_read_calls']==4 and m['sample_count']==2,'Cached read accounting differs')
    for k in ('target_attached','target_calls','target_writes'):require(m[k] is False,'Unexpected cached target intervention')
    for k in ('repeat_equal','identity_stable','maps_stable','file_stable'):require(m[k] is True,'Cached stability check failed')
    for field in ('device','inode','mode','size','mtime','mtime_nsec','ctime','ctime_nsec'):require(m['library_'+field+'_before']==m['library_'+field+'_after'],'APK metadata changed')
    require(m['library_size_before']==apk.stat().st_size and m['library_mode_before']&0o170000==0o100000,'Wrong APK backing metadata')
    identity=v.device_identity(m['library_device_before'],m['library_inode_before']);raw=[];resolutions=[];selected=[]
    for moment in ('before','armed','between','after'):
        require(v.proc_identity((d/('stat-'+moment+'.txt')).read_text())==(epoch['pid'],int(epoch['starttime'])),'Cached process epoch differs')
        require((d/('boot-'+moment+'.txt')).read_text().strip()==epoch['boot_id'],'Cached boot differs')
        data=(d/('maps-'+moment+'.txt')).read_bytes();raw.append(data);rows=v.maps_rows(data.decode())
        resolutions.append(o.resolve_apk(rows,epoch['library'],identity,entry,size,loads));selected.append([r for r in rows if r['path']==epoch['library']])
    require(all(x==resolutions[0] for x in resolutions) and all(x==selected[0] for x in selected),'Cached APK maps changed')
    bias,addresses,_,_=resolutions[0];require(bias==v.number(m['load_bias']) and addresses==[v.number(m['raw_band_address']),v.number(m['effective_band_address'])],'Independent cached addresses differ')
    require(m['full_maps_changed'] is any(x!=raw[0] for x in raw[1:]),'Full mapping report differs')
    for n in (1,2):
        sample=d/f'sample-{n}.bin';require(sample.read_bytes()==struct.pack('<II',17,17) and sha(sample)==m[f'sample_{n}_sha256'],'Cached policy not repeated17/17')
    require(m['observed_starttime_before']==m['observed_starttime_after']==int(epoch['starttime']) and m['boot_id_before']==m['boot_id_after']==epoch['boot_id'],'Cached manifest epoch differs')
    require(sha(run/'control/cached-bandwidth-reader')==READER_PIN and sha(run/'metadata/reader-roundtrip')==READER_PIN,'Helper binary differs')
    require(read(run/'metadata/cached-read-result.toml')['returncode']==0,'Helper return differed')

def verify(run,source,tools_root):
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
    commands=[e for e in events if e['event']=='adb-command'];results={e['name']:e for e in events if e['event']=='adb-result'}
    reboots=[e for e in commands if e['argv'][-1:] == ['reboot']];require(len(reboots)==1 and reboots[0]['name']=='normal-reboot' and results['normal-reboot']['code']==0,'Not exactly one successful reboot command')
    require(read(run/'metadata/reboot-result.toml')['returncode']==0,'Reboot result differs')
    roots=[e for e in commands if e['argv'][-1:]==['root']];root_events=[e for e in events if e['event']=='single-postboot-adbd-root-request']
    require(len(roots)==len(root_events)<=1 and all(e['name']=='postboot-root-once' and results[e['name']]['code']==0 for e in roots),'Root restart budget differs')
    for e in events:
        if e['event']=='adb-result' and not e['name'].startswith(('reconnect-','boot-ready-','ui-ready-')):require(e['code']==0,'Required ADB command failed')
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
    requested=one('single-reboot-requested');complete=one('ordinary-reboot-controller-complete')
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
    verify_bandwidth(run,tools_root/'guest/resolve-apk-cached-identity.py',i,post60)
    observation=one('observation-ready');require((observation['pid'],observation['starttime'],observation['boot_id'],observation['library'])==(post60['pid'],post60['starttime'],post60['boot_id'],post60['library']),'Reader launch epoch differs')
    exited=one('cached-helper-exit-proven');require(exited['exit_status']==0 and exited['cleanup'] is False,'Helper exit not proven')
    hp=(run/'metadata/lifecycle-pid-False.stdout').read_text().strip();require(hp.isdigit() and int(hp)==exited['pid'],'Helper PID differs')
    require(i.process_identity(run/'metadata/lifecycle-stat-False.stdout')==(int(hp),int(exited['starttime'])),'Helper start epoch differs')
    stage=observation['staging_directory'];argv=[stage+'/reader',str(post60['pid']),post60['starttime'],post60['boot_id'],post60['library'],stage+'/observation','positive']
    require((run/'metadata/lifecycle-argv-False.stdout').read_bytes()==b''.join(s.encode()+b'\0' for s in argv),'Helper argv differs')
    require((run/'metadata/lifecycle-state-False.stdout').read_bytes().strip()==b'exit 0','Remote wait result differs')
    lifecycle=[e for e in events if e['event']=='lifecycle-command'];require(lifecycle and all(e['code']==0 for e in lifecycle),'Lifecycle proof command failed')
    result=read(run/'reboot-result.toml');require(result['result']=='accepted-by-controller' and result['reboots_requested']==1 and result['changed_boot_id'] is True and result['ordinary_options_enabled']==10 and result['bundle_enabled'] is False and result['process_bytes_read']==16,'Completion summary differs')
    return dict(schema='mho900-lab.ordinary-reboot-verification/1',result='accepted',reboots_requested=1,boot_identity_changed=True,
                postboot_process_stable=True,ordinary_options_enabled=10,bundle_enabled=False,scpi_streams=3,
                scpi_queries=36,install_requests=0,wire_transcripts_equal=True,protected_files_unchanged=12,
                raw_bandwidth=17,effective_bandwidth=17,process_bytes_read=16,reader_exit_proven=True,
                enforcement_unchanged=True,enforcement_state=enforcement.decode().strip(),postboot_adbd_root_requests=len(roots),
                capture_frames=capture['capture_frames'],pcap_sha256=capture['pcap_sha256'],kernel_drops=0,recorder_exit=0,
                fresh_isolated_lease_after_reboot=True,reboot_dhcp_releases=len(capture['dhcp_release_epochs']),
                logical_changed_paths=changed,source_catalog_seal=i.SOURCE_SEAL,ui_resumed=True,ui_visual_semantics_verified=False,
                atomic_snapshot_claimed=False,verifier_sha256=sha(Path(__file__)))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--source-catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Output already exists');values=verify(a.run,a.source_catalog,Path(__file__).resolve().parents[1])
    a.output.write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in values.items()));print(json.dumps(values))

if __name__=='__main__':main()
