#!/usr/bin/env python3
"""Bounded passive private-cache reader control in a disposable loopback-only guest."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import time
import tomllib


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def toml(path,values):
    with path.open('x') as f:
        for k,v in values.items():f.write(k+' = '+json.dumps(v)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk',type=Path,required=True);p.add_argument('--apk',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();repo=Path(__file__).resolve().parents[2];run=a.run.resolve();assert not run.exists()
    for port in (5043,5582,5583):
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    assert sha(a.apk)=='6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b'
    image=repo/'local/guest-images/api25-default-r02/arm64-v8a'
    pins=tomllib.loads((repo/'experiments/guest-baseline/inputs.toml').read_text())
    for section,root in [('guest_files',image),('runtime_files',a.sdk)]:
        for item in pins[section]:assert sha(root/item['path'])==item['sha256'],item['path']
    build=tomllib.loads((a.build/'build.toml').read_text())
    assert build['profile']=='private-cache-owner-two-snapshot' and build['maximum_memory_bytes']==16384
    for item in build['files']:assert sha(a.build/item['path'])==item['sha256'],item['path']
    run.mkdir(parents=True);(run/'source').mkdir();(run/'inputs').mkdir()
    for name in ['run-private-cache-control.py','verify-private-cache-control.py','private_cache_snapshot.py','offline-loopback.sb','test-offline-network.py','resolve-apk-cached-identity.py','verify-cached-identity.py']:
        shutil.copy2(repo/'tools/guest'/name,run/'source'/name)
    shutil.copy2(a.apk,run/'inputs/stock.apk')
    for name in ['read-private-cache','private-cache-mapping-fixture','build.toml','read-private-cache.c','private-cache-mapping-fixture.c','build.py']:
        shutil.copy2(a.build/name,run/'inputs'/name)
    toml(run/'frozen-inputs.toml',{str(f.relative_to(run)).replace('/','_').replace('.','_').replace('-','_'):sha(f) for d in ['source','inputs'] for f in sorted((run/d).iterdir())})
    subprocess.run(['python3',str(run/'source/test-offline-network.py'),str(run/'source/offline-loopback.sb')],check=True,stdout=(run/'network-control.toml').open('w'),stderr=(run/'network-control.stderr').open('w'))
    env=dict(os.environ,ANDROID_USER_HOME=str(run/'home'),ANDROID_EMULATOR_HOME=str(run/'emulator-home'),ANDROID_AVD_HOME=str(run/'avds'),ANDROID_ADB_SERVER_PORT='5043',ADB_SERVER_SOCKET='tcp:127.0.0.1:5043',ADB_VENDOR_KEYS=str(run/'home'),ADB_MDNS='0',ADB_MDNS_AUTO_CONNECT='0')
    for d in ['home','emulator-home','avds/baseline-api25.avd']:(run/d).mkdir(parents=True)
    (run/'avds/baseline-api25.ini').write_text('avd.ini.encoding=UTF-8\npath='+str(run/'avds/baseline-api25.avd')+'\ntarget=android-25\n')
    (run/'avds/baseline-api25.avd/config.ini').write_text('AvdId=baseline-api25\navd.ini.encoding=UTF-8\nabi.type=arm64-v8a\nhw.cpu.arch=arm64\nhw.cpu.ncore=2\nhw.ramSize=2048\nhw.lcd.width=1280\nhw.lcd.height=800\nhw.lcd.density=160\nhw.gpu.enabled=yes\nhw.gpu.mode=swiftshader\nhw.sdCard=no\nimage.sysdir.1='+str(image)+'/\ntag.id=default\n')
    subprocess.run(['/bin/cp','-c',str(image/'userdata.img'),str(run/'userdata.img')],check=True)
    offline=['/usr/bin/sandbox-exec','-f',str(run/'source/offline-loopback.sb')]
    adb=[str(a.sdk/'platform-tools/adb'),'-H','127.0.0.1','-P','5043'];serial=['-s','emulator-5582']
    index=0;emulator=None;fixture=None;boot=False;pid=None;result='failed';phase='start';error='';started=now()
    def call(name,args,timeout=20,check=True):
        nonlocal index
        index+=1;prefix=run/(f'{index:03d}-'+name)
        with (run/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(utc=now(),name=name,argv=args))+'\n')
        client=[str(a.sdk/'platform-tools/adb'),'-P','5043'] if name=='server' else adb
        r=subprocess.run(offline+client+args,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
        prefix.with_suffix('.stdout').write_bytes(r.stdout);prefix.with_suffix('.stderr').write_bytes(r.stderr)
        toml(prefix.with_suffix('.toml'),dict(returncode=r.returncode))
        if check:assert r.returncode==0,(name,r.returncode,r.stderr.decode(errors='replace'))
        return r
    try:
        call('server',['--one-device','emulator-5582','start-server'])
        mdns=call('mdns',['mdns','check'],check=False);assert b'mdns discovery disabled' in mdns.stdout+mdns.stderr
        argv=[str(a.sdk/'emulator/emulator'),'-avd','baseline-api25','-sysdir',str(image),'-data',str(run/'userdata.img'),'-cache',str(run/'cache.img'),'-port','5582','-no-window','-no-snapshot','-no-boot-anim','-no-audio','-no-metrics','-gpu','swiftshader','-memory','2048','-cores','2','-verbose','-show-kernel']
        (run/'emulator-argv.txt').write_text('\n'.join(argv)+'\n')
        emulator=subprocess.Popen(offline+argv,env=env,stdout=(run/'emulator.log').open('wb'),stderr=subprocess.STDOUT)
        phase='boot';deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            assert emulator.poll() is None,'emulator exited'
            r=call('boot',serial+['shell','getprop','sys.boot_completed'],check=False)
            if r.stdout.strip()==b'1':boot=True;break
            time.sleep(2)
        assert boot,'boot deadline'
        call('guest-root',serial+['root']);call('wait',serial+['wait-for-device'])
        assert b'uid=0(root)' in call('id',serial+['shell','id']).stdout
        policyhash=call('policy-bytes-before',serial+['exec-out','cat','/sys/fs/selinux/policy']).stdout
        policy=call('policy-before',serial+['shell','getenforce']).stdout;assert policy.strip()==b'Enforcing'
        system=call('system-server-before',serial+['shell','pidof','system_server']).stdout
        phase='stage';base='/data/local/tmp/private-cache-control'
        call('mkdir',serial+['shell','test ! -e '+base+' && mkdir -m 700 '+base])
        for n in ['stock.apk','read-private-cache','private-cache-mapping-fixture']:
            call('push-'+n,serial+['push',str(run/'inputs'/n),base+'/'+n],timeout=45)
        call('mode',serial+['shell','chmod 700 '+base+'/read-private-cache '+base+'/private-cache-mapping-fixture'])
        for n in ['stock.apk','read-private-cache','private-cache-mapping-fixture']:
            dst=run/('roundtrip-'+n);call('roundtrip-'+n,serial+['pull',base+'/'+n,str(dst)],timeout=45)
            assert sha(dst)==sha(run/'inputs'/n)
        for scenario in ('positive','bad-backlink'):
            phase='fixture-'+scenario
            fixture=subprocess.Popen(offline+adb+serial+['shell','-T',
                shlex.join([base+'/private-cache-mapping-fixture',base+'/stock.apk',scenario])],
                env=env,stdout=(run/('fixture-'+scenario+'.stdout')).open('wb'),
                stderr=(run/('fixture-'+scenario+'.stderr')).open('wb'))
            deadline=time.monotonic()+10
            while b'ready\n' not in (run/('fixture-'+scenario+'.stdout')).read_bytes():
                assert fixture.poll() is None,'fixture exited'
                assert time.monotonic()<deadline,'fixture timeout';time.sleep(.1)
            pid=int(call('fixture-pid-'+scenario,serial+['shell','pidof','private-cache-mapping-fixture']).stdout.strip())
            stat=call('fixture-stat-'+scenario,serial+['shell','cat',f'/proc/{pid}/stat']).stdout.decode()
            start=stat[stat.rindex(')')+2:].split()[19]
            bootid=call('boot-id-'+scenario,serial+['shell','cat','/proc/sys/kernel/random/boot_id']).stdout.decode().strip()
            maps=call('fixture-maps-'+scenario,serial+['shell','cat',f'/proc/{pid}/maps']).stdout
            (run/('fixture-maps-'+scenario+'.txt')).write_bytes(maps)
            toml(run/('fixture-identity-'+scenario+'.toml'),dict(pid=pid,starttime=start,boot_id=bootid,path=base+'/stock.apk',scenario=scenario))
            modes=['wrong-starttime','wrong-pin','unmapped-range','positive'] if scenario=='positive' else ['bad-backlink']
            for mode in modes:
                phase=mode
                reader_mode='positive' if mode=='bad-backlink' else mode
                args=[base+'/read-private-cache',str(pid),start,bootid,base+'/stock.apk',base+'/'+mode,reader_mode]
                r=call('reader-'+mode,serial+['shell','-T',shlex.join(args)],check=False,timeout=45)
                call('pull-'+mode,serial+['pull',base+'/'+mode,str(run/mode)])
                m=tomllib.loads((run/mode/'manifest.toml').read_text())
                if mode!='positive':
                    assert r.returncode==3 and m['result']=='rejected'
                    expected_stage={'wrong-starttime':'process-identity','wrong-pin':'library-hash',
                                    'unmapped-range':'target-ranges','bad-backlink':'owner-backlink'}[mode]
                    assert m['stage']==expected_stage and m['error_number']==0
                    if mode!='bad-backlink':
                        assert m['mem_open_count']==m['memory_read_calls']==m['bytes_read']==0
                    else:
                        assert m['mem_open_count']==1 and 0<m['bytes_read']<=16384
                        assert not list((run/mode).glob('work-*.bin')) and not list((run/mode).glob('ref-*.bin'))
                else:
                    assert r.returncode==0 and m['result']=='accepted' and m['stage']=='complete'
                    assert m['mem_open_count']==1 and 0<m['bytes_read']<=16384
                    empty=(8).to_bytes(4,'little')+((-8)&0xffffffff).to_bytes(4,'little')+bytes(0x700-8)
                    for sample in (1,2):
                        assert (run/mode/f'work-{sample}.bin').read_bytes()==empty
                        assert (run/mode/f'ref-{sample}.bin').read_bytes()==empty
            call('fixture-stop-'+scenario,serial+['shell','kill','-TERM',str(pid)],check=False)
            fixture.wait(timeout=5);fixture=None;pid=None
        assert call('policy-bytes-after',serial+['exec-out','cat','/sys/fs/selinux/policy']).stdout==policyhash
        assert call('policy-after',serial+['shell','getenforce']).stdout==policy
        assert call('system-server-after',serial+['shell','pidof','system_server']).stdout==system
        phase='complete';result='accepted'
    except BaseException as exc:
        import traceback
        error=str(exc);(run/'failure.txt').write_text(traceback.format_exc())
    finally:
        cleanup_errors=[]
        def cleanup(name,action):
            try:action()
            except BaseException as exc:cleanup_errors.append(name+': '+str(exc))
        if boot:
            if pid:cleanup('fixture-stop',lambda:call('fixture-stop',serial+['shell','kill','-TERM',str(pid)],check=False))
            cleanup('final-logcat',lambda:call('final-logcat',serial+['logcat','-b','all','-d'],check=False))
        if fixture and fixture.poll() is None:
            cleanup('fixture-terminate',lambda:(fixture.terminate(),fixture.wait(timeout=5)))
        if emulator:
            cleanup('emulator-stop',lambda:call('emulator-stop',serial+['emu','kill'],check=False))
            try:emulator.wait(timeout=15)
            except subprocess.TimeoutExpired:
                cleanup('emulator-terminate',lambda:(emulator.terminate(),emulator.wait(timeout=10)))
        cleanup('server-stop',lambda:call('server-stop',['kill-server'],check=False))
        original_result=result
        if cleanup_errors:result='failed'
        toml(run/'result.toml',dict(schema_version=1,result=result,original_result=original_result,
             phase=phase,error=error,cleanup_errors=cleanup_errors,started_at=started,finished_at=now(),physical_access=False))
    print((run/'result.toml').read_text())
    return 0 if result=='accepted' else 1


if __name__=='__main__':raise SystemExit(main())
