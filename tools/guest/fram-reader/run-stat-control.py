#!/usr/bin/env python3
"""Metadata-probe real-syscall controls in a disposable loopback-only guest."""
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
    p.add_argument('--sdk',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    a=p.parse_args();repo=Path(__file__).resolve().parents[3];run=a.run.resolve();assert not run.exists()
    for port in (5043,5582,5583):
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    image=repo/'local/guest-images/api25-default-r02/arm64-v8a'
    pins=tomllib.loads((repo/'experiments/guest-baseline/inputs.toml').read_text())
    for section,root in [('guest_files',image),('runtime_files',a.sdk)]:
        for item in pins[section]:assert sha(root/item['path'])==item['sha256'],item['path']
    build=tomllib.loads((a.build/'build.toml').read_text())
    assert build['profile']=='fram-stat-node'
    for item in build['files']:assert sha(a.build/item['path'])==item['sha256'],item['path']
    run.mkdir(parents=True);(run/'source').mkdir();(run/'inputs').mkdir()
    shutil.copy2(__file__,run/'source/run-stat-control.py')
    for name in ['offline-loopback.sb','test-offline-network.py']:
        shutil.copy2(repo/'tools/guest'/name,run/'source'/name)
    for name in ['stat-node','build.toml','stat-node.c','test-stat-node.c','build-stat.py']:
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
        phase='stage';base='/data/local/tmp/fram-stat-control'
        call('mkdir',serial+['shell','test ! -e '+base+' && mkdir -m 700 '+base])
        call('push',serial+['push',str(run/'inputs/stat-node'),base+'/stat-node'])
        call('mode',serial+['shell','chmod 700 '+base+'/stat-node'])
        dst=run/'roundtrip-stat-node';call('roundtrip',serial+['pull',base+'/stat-node',str(dst)])
        assert sha(dst)==sha(run/'inputs/stat-node')
        phase='metadata-controls'
        call('symlink',serial+['shell','ln -s /dev/null '+base+'/null-link'])
        positive={}
        for name,command in [
            ('dev-null',shlex.join([base+'/stat-node','/dev/null'])),
            ('symlink',shlex.join([base+'/stat-node',base+'/null-link'])),
            ('held-fd',shlex.join([base+'/stat-node','/proc/self/fd/0'])+' < /dev/null')]:
            response=call(name,serial+['shell','-T',command])
            m=tomllib.loads(response.stdout.decode())
            assert set(m)=={'mode','major','minor','inode','device'}
            assert m['mode']&0xf000==0x2000 and (m['major'],m['minor'])==(1,3) and m['inode']>0
            positive[name]=m
        assert positive['dev-null']==positive['symlink']==positive['held-fd']
        response=call('nonexistent',serial+['shell','-T',shlex.join([base+'/stat-node',base+'/not-present'])],check=False)
        assert response.returncode==3 and not response.stdout and b'errno = 2' in response.stderr
        toml(run/'metadata-controls.toml',dict(result='accepted',positive_cases=3,negative_cases=1,symlink_followed=True,held_fd_followed=True,ioctl_calls=0,physical_access=False))
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
