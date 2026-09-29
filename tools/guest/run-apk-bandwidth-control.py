#!/usr/bin/env python3
"""Bounded two-word bandwidth reader control in a disposable loopback-only guest."""
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
    for item in build['files']:assert sha(a.build/item['path'])==item['sha256'],item['path']
    run.mkdir(parents=True);(run/'source').mkdir();(run/'inputs').mkdir()
    for name in ['run-apk-bandwidth-control.py','offline-loopback.sb','test-offline-network.py','resolve-apk-cached-identity.py','verify-cached-identity.py']:
        shutil.copy2(repo/'tools/guest'/name,run/'source'/name)
    shutil.copy2(a.apk,run/'inputs/stock.apk')
    for name in ['read-apk-cached-identity','apk-cached-mapping-fixture','build.toml','read-apk-cached-identity.c']:
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
        policyhash=call('policy-sha-before',serial+['shell','sha256sum','/sys/fs/selinux/policy']).stdout
        policy=call('policy-before',serial+['shell','getenforce']).stdout;assert policy.strip()==b'Enforcing'
        system=call('system-server-before',serial+['shell','pidof','system_server']).stdout
        phase='stage';base='/data/local/tmp/apk-cached-control'
        call('mkdir',serial+['shell','test ! -e '+base+' && mkdir -m 700 '+base])
        for n in ['stock.apk','read-apk-cached-identity','apk-cached-mapping-fixture']:
            call('push-'+n,serial+['push',str(run/'inputs'/n),base+'/'+n],timeout=45)
        call('mode',serial+['shell','chmod 700 '+base+'/read-apk-cached-identity '+base+'/apk-cached-mapping-fixture'])
        for n in ['stock.apk','read-apk-cached-identity','apk-cached-mapping-fixture']:
            dst=run/('roundtrip-'+n);call('roundtrip-'+n,serial+['pull',base+'/'+n,str(dst)],timeout=45)
            assert sha(dst)==sha(run/'inputs'/n)
        phase='fixture';fixture=subprocess.Popen(offline+adb+serial+['shell','-T',base+'/apk-cached-mapping-fixture '+base+'/stock.apk'],env=env,stdout=(run/'fixture.stdout').open('wb'),stderr=(run/'fixture.stderr').open('wb'))
        deadline=time.monotonic()+10
        while b'ready\n' not in (run/'fixture.stdout').read_bytes():
            assert fixture.poll() is None,'fixture exited'
            assert time.monotonic()<deadline,'fixture timeout';time.sleep(.1)
        pid=int(call('fixture-pid',serial+['shell','pidof','apk-cached-mapping-fixture']).stdout.strip())
        stat=call('fixture-stat',serial+['shell','cat',f'/proc/{pid}/stat']).stdout.decode();start=stat[stat.rindex(')')+2:].split()[19]
        bootid=call('boot-id',serial+['shell','cat','/proc/sys/kernel/random/boot_id']).stdout.decode().strip()
        maps=call('fixture-maps',serial+['shell','cat',f'/proc/{pid}/maps']).stdout;(run/'fixture-maps.txt').write_bytes(maps)
        toml(run/'fixture-identity.toml',dict(pid=pid,starttime=start,boot_id=bootid,path=base+'/stock.apk',expected_sample_hex=(bytes(range(0x10,0x14))+bytes(range(0x20,0x24))).hex()))
        for mode in ['wrong-starttime','wrong-pin','unmapped-range','positive']:
            phase=mode
            args=[base+'/read-apk-cached-identity',str(pid),start,bootid,base+'/stock.apk',base+'/'+mode,mode]
            r=call('reader-'+mode,serial+['shell','-T',shlex.join(args)],check=False,timeout=45)
            call('pull-'+mode,serial+['pull',base+'/'+mode,str(run/mode)])
            m=tomllib.loads((run/mode/'manifest.toml').read_text())
            if mode!='positive':
                assert r.returncode==3 and m['result']=='rejected'
                assert m['mem_open_count']==m['memory_read_calls']==m['bytes_read']==0
            else:
                assert r.returncode==0 and m['result']=='accepted'
                assert m['mem_open_count']==1 and m['memory_read_calls']==4 and m['bytes_read']==16
                expected=bytes(range(0x10,0x14))+bytes(range(0x20,0x24))
                assert (run/mode/'sample-1.bin').read_bytes()==(run/mode/'sample-2.bin').read_bytes()==expected
        assert call('policy-sha-after',serial+['shell','sha256sum','/sys/fs/selinux/policy']).stdout==policyhash
        assert call('policy-after',serial+['shell','getenforce']).stdout==policy
        assert call('system-server-after',serial+['shell','pidof','system_server']).stdout==system
        phase='complete';result='accepted'
    except BaseException as exc:
        import traceback
        error=str(exc);(run/'failure.txt').write_text(traceback.format_exc())
    finally:
        if boot:
            if pid:call('fixture-stop',serial+['shell','kill','-TERM',str(pid)],check=False)
            call('final-logcat',serial+['logcat','-b','all','-d'],check=False)
        if fixture and fixture.poll() is None:fixture.terminate();fixture.wait(timeout=5)
        if emulator:
            try:call('emulator-stop',serial+['emu','kill'],check=False)
            finally:
                try:emulator.wait(timeout=15)
                except subprocess.TimeoutExpired:emulator.terminate();emulator.wait(timeout=10)
        call('server-stop',['kill-server'],check=False)
        toml(run/'result.toml',dict(schema_version=1,result=result,phase=phase,error=error,started_at=started,finished_at=now(),physical_access=False))
    print((run/'result.toml').read_text())
    return 0 if result=='accepted' else 1


if __name__=='__main__':raise SystemExit(main())
