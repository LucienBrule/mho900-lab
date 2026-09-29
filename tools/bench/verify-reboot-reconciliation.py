#!/usr/bin/env python3
"""Offline reconciliation after a previously requested reboot timed out.

Binds the sealed negative predecessor, fresh isolated-lease capture, two SCPI
read transcripts, logical files, process epochs and fixed 16-byte observation.
A capture gap remains explicit. Screenshots and resumed activity do not alone
prove visual UI semantics. This program never contacts a device.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tomllib
sys.dont_write_bytecode=True
REBOOT_VERIFIER_PIN='aee2561e9cb76183c630049149d3e44bd037aaf1e78b0a126f6524e55f62147e'
PREDECESSOR_SEAL='aa84e900ae872173b43d56b4ab95d5cc170252c733df9f46cfe62ba2ea450e6e'
PHASES=('scpi-postboot','scpi-post60')
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return tomllib.loads(p.read_text())
def module(path,name,pin):
    require(sha(path)==pin,'Verifier dependency differs: '+path.name)
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=module(Path(__file__).with_name('verify-ordinary-reboot.py'),'reconciliation_reboot',REBOOT_VERIFIER_PIN)
INSTALL_VERIFIER_PIN=r.INSTALL_VERIFIER_PIN
streams=r.streams
verify_bandwidth=r.verify_bandwidth

def verify_predecessor(old,run,i):
    require(sha(old/'artifacts.toml')==PREDECESSOR_SEAL,'Predecessor seal differs')
    manifest=read(old/'artifacts.toml');require(manifest['result']=='reboot-transport-timeout','Wrong predecessor conclusion')
    pins={}
    for item in manifest['files']:
        rel=Path(item['path']);require(not rel.is_absolute() and '..' not in rel.parts and item['path'] not in pins,'Unsafe/duplicate predecessor member')
        require(sha(old/rel)==item['sha256'],'Sealed predecessor member changed')
        pins[item['path']]=item['sha256']
    p=read(run/'control/predecessor.toml');require(p['artifact_seal_sha256']==PREDECESSOR_SEAL and Path(p['run_directory']).name==old.name,'Predecessor binding differs')
    for item in p['files']:require(pins.get(item['path'])==item['sha256'],'Selected predecessor member outside seal')
    events=[json.loads(line) for line in (old/'events.jsonl').read_text().splitlines()]
    recorder=[e for e in events if e['event']=='recorder-stopped'];require(len(recorder)==1 and recorder[0]['code']==0,'Predecessor recorder not closed')
    requests=[e for e in events if e['event']=='adb-command' and e['argv'][-1:]==['reboot']]
    require(len(requests)==1 and requests[0]['name']=='normal-reboot','Predecessor reboot request differs')
    require(not any(e['event']=='ordinary-reboot-controller-complete' for e in events),'Predecessor failure relabeled')
    require(read(old/'scpi-before.toml')=={s:int(s!='BND') for s in i.SELECTORS},'Preboot status differs')
    require(sha(old/'metadata/before-Sparrow.apk')==i.APK_PIN,'Preboot stock APK differs')
    identity=(run/'control/expected-identity.bin').read_bytes()
    for n,request in enumerate(i.REQUESTS):
        require((old/f'scpi-before/{n:02d}-request.bin').read_bytes()==request,'Preboot request differs')
        response=(old/f'scpi-before/{n:02d}-response.bin').read_bytes()
        expected=identity.strip() if n==0 else (b'0' if i.SELECTORS[n-1]=='BND' else b'1')
        require(response.strip()==expected,'Preboot raw reply differs')
    archive=i.archive(old/'metadata/data-before.tar')
    rows=read(old/'metadata/data-before-sha256.toml')['files']
    require(len(rows)==len(archive) and {x['path']:x['sha256'] for x in rows}=={n:hashlib.sha256(b).hexdigest() for n,b in archive.items()},'Preboot archive summary differs')
    expiry=[e['expires_epoch'] for e in events if e['event'] in ('prior-lease-validated','ack-captured')]
    require(expiry and p['prior_lease_expiry_epoch']==max(expiry),'Prior lease witness differs')
    return events,(old/'metadata/before-boot.stdout').read_text().strip(),datetime.fromisoformat(recorder[0]['utc']).timestamp()

def verify(run,source,predecessor,tools_root):
    i=module(tools_root/'bench/verify-ordinary-install.py','ordinary_install_evidence',INSTALL_VERIFIER_PIN)
    old_events, old_boot, old_end = verify_predecessor(predecessor, run, i)
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
    require(not any('reboot' in e['argv'] for e in commands),'Additional reboot command')
    roots=[e for e in commands if e['argv'][-1:]==['root']];root_events=[e for e in events if e['event']=='single-postboot-adbd-root-request']
    require(len(roots)==len(root_events)<=1 and all(e['name']=='postboot-root-once' and results[e['name']]['code']==0 for e in roots),'Root restart budget differs')
    for e in events:
        if e['event']=='adb-result' and not e['name'].startswith(('reconnect-','boot-ready-','ui-ready-')):require(e['code']==0,'Required ADB command failed')
        if e['event']=='host':require(e['code']==0,'Host isolation command failed')
    require(not any('install' in e['name'].lower() for e in commands),'Unexpected installer command')
    snapshots={e['phase']:e for e in events if e['event']=='process-snapshot'};require(set(snapshots)=={'postboot','post60'} and len([e for e in events if e['event']=='process-snapshot'])==2,'Process snapshot set differs')
    postboot,post60=[snapshots[n] for n in ('postboot','post60')]
    require(old_boot!=postboot['boot_id'] and (postboot['pid'],postboot['starttime'],postboot['boot_id'])==(post60['pid'],post60['starttime'],post60['boot_id']),'Boot transition or postboot continuity differs')
    for label,epoch in snapshots.items():
        require(i.process_identity(run/('metadata/'+label+'-stat.stdout'))==(epoch['pid'],int(epoch['starttime'])),'Recorded process epoch differs')
        require((run/('metadata/'+label+'-boot.stdout')).read_text().strip()==epoch['boot_id'],'Recorded boot differs')
        require((run/('metadata/'+label+'-cmdline.stdout')).read_bytes().split(b'\0')[0]==b'com.rigol.scope','Wrong process')
        require(sha(run/('metadata/'+label+'-Sparrow.apk'))==i.APK_PIN,'Stock APK changed')
        activity=(run/('metadata/'+label+'-activity.stdout')).read_text();require(any('mResumedActivity' in line and 'com.rigol.scope/' in line for line in activity.splitlines()),'Sparrow not resumed')
        require(any(line.split()[-1]==epoch['library'] for line in (run/('metadata/'+label+'-maps.stdout')).read_text().splitlines()),'APK map path absent')
    require(i.process_identity(run/'metadata/target-stat-after.stdout')==(post60['pid'],int(post60['starttime'])),'Process changed after reader')
    require((run/'metadata/target-boot-after.stdout').read_text().strip()==post60['boot_id'],'Boot changed after reader')
    complete=one('ordinary-reconciliation-controller-complete')
    require(complete['old_boot_id']==old_boot and complete['new_boot_id']==post60['boot_id'] and complete['root_restart_used']==bool(roots),'Reconciliation epoch differs')
    bound=one('predecessor-bound');require(bound['old_boot_id']==old_boot and bound['old_capture_end_epoch']==old_end,'Predecessor event differs')
    ready=one('capture-ready');gap=one('capture-gap')
    gap_seconds=ready['epoch']-old_end
    require(gap_seconds>0 and gap['previous_recorder_exit_epoch']==old_end and gap['new_capture_ready_epoch']==ready['epoch'] and abs(gap['seconds_between_recorder_witnesses']-gap_seconds)<1e-6 and gap['continuous_reboot_capture'] is False,'Capture gap is not accurately disclosed')
    discovered=one('boot-discovered');require(discovered['old_boot_id']==old_boot and discovered['current_boot_id']==post60['boot_id'] and discovered['fresh_ack_captured'] is True,'Boot discovery did not establish changed boot with fresh lease')
    require((run/'metadata/discovery-boot.stdout').read_text().splitlines()[0]==post60['boot_id'],'Raw boot discovery differs')
    require(one('passive-ack-wait-start')['seconds']==120,'Passive observation budget differs')
    connections=[e for e in events if e['event']=='scpi-connected'];require(len(connections)==2 and [e['phase'] for e in connections]==list(PHASES),'SCPI phase count/order differs')
    require((datetime.fromisoformat(connections[1]['utc'])-datetime.fromisoformat(connections[0]['utc'])).total_seconds()>=60,'Missing 60-second persistence interval')
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
    actual,capture=streams(run/'live/capture.pcap',connections,i.reconstruct,lease,None);require(actual==logs,'Raw two-stream SCPI transcript differs')
    fresh_acks=[epoch for epoch in capture['dhcp_ack_epochs'] if epoch>=ready['epoch']]
    require(fresh_acks,'No new captured DHCP ACK')
    require(not capture['dhcp_release_epochs'],'Unexpected DHCP RELEASE')
    first_ack=min(fresh_acks)
    require(datetime.fromisoformat(discovered['utc']).timestamp()>=first_ack,'Boot discovery preceded fresh ACK')
    gated=[e for e in commands if e['name']=='stage-helper' or e in roots]
    require(any(e['name']=='stage-helper' for e in gated) and all(datetime.fromisoformat(e['utc']).timestamp()>=first_ack for e in gated),'Root/helper staging preceded fresh ACK')
    require(all(any(abs((e['expires_epoch']-21600)-epoch)<0.001 for e in events if e['event']=='ack-captured') for epoch in fresh_acks),'Wire ACK lacks controller witness')
    cv=read(run/'capture-validation.toml')
    for key in ('capture_frames','capture_bytes','pcap_sha256'):require(cv[key]==capture[key],'Capture validation differs')
    require(cv['kernel_drops']==0 and cv['all_frame_lengths_complete'] is True and cv['all_frames_passed_recorded_network_classifier'] is True,'Capture validation failed')
    stats=(run/'live/capture.stderr').read_text();drops=re.findall(r'(\d+) packets dropped by kernel',stats);require(drops and all(int(x)==0 for x in drops),'Capture dropped packets')
    for text,key in [('packets captured','capture_frames'),('packets received by filter','received_counter')]:
        values=re.findall(r'(?m)^(\d+) '+text+'$',stats);require(values and int(values[-1])==cv[key],'Capture final counter differs')
    archives={'before':i.archive(predecessor/'metadata/data-before.tar')}
    require({n:b for n,b in archives['before'].items() if n.endswith('.lic')}==licenses,'Sealed preboot licenses differ')
    require(all(n in archives['before'] and hashlib.sha256(archives['before'][n]).hexdigest()==h for n,h in pins.items()),'Protected pins do not match sealed preboot bytes')
    for label in ('postboot','post60'):
        data=i.archive(run/('metadata/data-'+label+'.tar'));archives[label]=data
        require({n:b for n,b in data.items() if n.endswith('.lic')}==licenses,'Cumulative license bytes differ')
        require(all(n in data and hashlib.sha256(data[n]).hexdigest()==h for n,h in pins.items()),'Protected file changed')
        summary=read(run/('metadata/data-'+label+'-sha256.toml'))['files'];require(len(summary)==len(data) and {x['path']:x['sha256'] for x in summary}=={n:hashlib.sha256(b).hexdigest() for n,b in data.items()},'Logical archive summary differs')
    changed=sorted(n for n in set(archives['before'])|set(archives['post60']) if archives['before'].get(n)!=archives['post60'].get(n));require(read(run/'data-delta.toml')['changed_since_predecessor_before']==changed,'Logical delta summary differs')
    enforcement=(predecessor/'metadata/enforcement-before.stdout').read_bytes();require(enforcement in (b'Enforcing\n',b'Permissive\n',b'Disabled\n') and enforcement==(run/'metadata/enforcement-after.stdout').read_bytes(),'Enforcement changed')
    verify_bandwidth(run,tools_root/'guest/resolve-apk-cached-identity.py',i,post60)
    observation=one('observation-ready');require((observation['pid'],observation['starttime'],observation['boot_id'],observation['library'])==(post60['pid'],post60['starttime'],post60['boot_id'],post60['library']),'Reader launch epoch differs')
    exited=one('cached-helper-exit-proven');require(exited['exit_status']==0 and exited['cleanup'] is False,'Helper exit not proven')
    hp=(run/'metadata/lifecycle-pid-False.stdout').read_text().strip();require(hp.isdigit() and int(hp)==exited['pid'],'Helper PID differs')
    require(i.process_identity(run/'metadata/lifecycle-stat-False.stdout')==(int(hp),int(exited['starttime'])),'Helper start epoch differs')
    stage=observation['staging_directory'];argv=[stage+'/reader',str(post60['pid']),post60['starttime'],post60['boot_id'],post60['library'],stage+'/observation','positive']
    require((run/'metadata/lifecycle-argv-False.stdout').read_bytes()==b''.join(s.encode()+b'\0' for s in argv),'Helper argv differs')
    require((run/'metadata/lifecycle-state-False.stdout').read_bytes().strip()==b'exit 0','Remote wait result differs')
    lifecycle=[e for e in events if e['event']=='lifecycle-command'];require(lifecycle and all(e['code']==0 for e in lifecycle),'Lifecycle proof command failed')
    result=read(run/'reconciliation-result.toml');require(result['result']=='accepted-by-controller' and result['new_reboot_requests']==0 and result['changed_boot_id'] is True and result['ordinary_options_enabled']==10 and result['bundle_enabled'] is False and result['protected_files_unchanged'] is True and result['raw_bandwidth_enum']==result['effective_bandwidth_enum']==17 and result['process_bytes_read']==16,'Completion summary differs')
    return dict(schema='mho900-lab.reboot-reconciliation-verification/1',result='accepted',new_reboot_requests=0,boot_identity_changed=True,
                postboot_process_stable=True,ordinary_options_enabled=10,bundle_enabled=False,scpi_streams=2,
                scpi_queries=24,install_requests=0,wire_transcripts_equal=True,protected_files_unchanged=12,
                raw_bandwidth=17,effective_bandwidth=17,process_bytes_read=16,reader_exit_proven=True,
                enforcement_unchanged=True,enforcement_state=enforcement.decode().strip(),postboot_adbd_root_requests=len(roots),
                capture_frames=capture['capture_frames'],pcap_sha256=capture['pcap_sha256'],kernel_drops=0,recorder_exit=0,
                fresh_isolated_lease_after_reboot=True,continuous_reboot_capture=False,capture_gap_seconds=gap_seconds,predecessor_seal=PREDECESSOR_SEAL,
                logical_changed_paths=changed,source_catalog_seal=i.SOURCE_SEAL,ui_resumed=True,ui_visual_semantics_verified=False,
                atomic_snapshot_claimed=False,verifier_sha256=sha(Path(__file__)))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path);p.add_argument('--predecessor',type=Path,required=True)
    p.add_argument('--source-catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();require(not a.output.exists(),'Output already exists')
    values=verify(a.run,a.source_catalog,a.predecessor,Path(__file__).resolve().parents[1])
    a.output.write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in values.items()))
    print(json.dumps(values))
if __name__=='__main__':main()
