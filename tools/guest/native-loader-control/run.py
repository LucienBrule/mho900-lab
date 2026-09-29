#!/usr/bin/env python3
"""Normal APK native-library precedence, reboot and rollback in a disposable guest."""
import argparse
from datetime import datetime, timezone
import hashlib, json, os, re, shlex, shutil, socket, subprocess, sys, time, tomllib, zipfile, struct
from pathlib import Path


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def write_toml(p, values):
    with p.open('x') as f:
        for k, v in values.items(): f.write(k+' = '+json.dumps(v)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk', 'build', 'run'): p.add_argument('--'+name, required=True, type=Path)
    a = p.parse_args(); repo = Path(__file__).resolve().parents[3]; run = a.run.resolve(); builddir = a.build.resolve()
    assert not run.exists()
    for port in (5043, 5582, 5583):
        with socket.socket() as s: s.bind(('127.0.0.1', port))
    image = repo/'local/guest-images/api25-default-r02/arm64-v8a'
    pins = tomllib.loads((repo/'experiments/guest-baseline/inputs.toml').read_text())
    for section, base in [('guest_files', image), ('runtime_files', a.sdk)]:
        for item in pins[section]: assert sha(base/item['path']) == item['sha256'], item['path']
    build = tomllib.loads((builddir/'build.toml').read_text())
    assert build['profile'] == 'normal-apk-extract-false'
    for item in build['files']: assert sha(builddir/item['path']) == item['sha256'], item['path']
    run.mkdir(parents=True); shutil.copytree(builddir, run/'build'); (run/'source').mkdir(); (run/'phases').mkdir()
    for src in [Path(__file__), repo/'tools/guest/offline-loopback.sb', repo/'tools/guest/test-offline-network.py', repo/'experiments/guest-baseline/inputs.toml']:
        shutil.copy2(src, run/'source'/src.name)
    write_toml(run/'source-hashes.toml', {p.name.replace('.', '_').replace('-', '_'): sha(p) for p in sorted((run/'source').iterdir())})
    subprocess.run([sys.executable, str(run/'source/test-offline-network.py'), str(run/'source/offline-loopback.sb')], check=True, stdout=(run/'network-control.toml').open('w'), stderr=(run/'network-control.stderr').open('w'))
    env = dict(os.environ, ANDROID_USER_HOME=str(run/'home'), ANDROID_EMULATOR_HOME=str(run/'emulator-home'), ANDROID_AVD_HOME=str(run/'avds'), ANDROID_ADB_SERVER_PORT='5043', ADB_SERVER_SOCKET='tcp:127.0.0.1:5043', ADB_VENDOR_KEYS=str(run/'home'), ADB_MDNS='0', ADB_MDNS_AUTO_CONNECT='0')
    for d in ('home', 'emulator-home', 'avds/baseline-api25.avd'): (run/d).mkdir(parents=True)
    (run/'avds/baseline-api25.ini').write_text('avd.ini.encoding=UTF-8\npath='+str(run/'avds/baseline-api25.avd')+'\ntarget=android-25\n')
    (run/'avds/baseline-api25.avd/config.ini').write_text('AvdId=baseline-api25\navd.ini.encoding=UTF-8\nabi.type=arm64-v8a\nhw.cpu.arch=arm64\nhw.cpu.ncore=2\nhw.ramSize=2048\nhw.lcd.width=1280\nhw.lcd.height=800\nhw.lcd.density=160\nhw.gpu.enabled=yes\nhw.gpu.mode=swiftshader\nhw.sdCard=no\nimage.sysdir.1='+str(image)+'/\ntag.id=default\n')
    subprocess.run(['/bin/cp', '-c', str(image/'userdata.img'), str(run/'userdata.img')], check=True)
    offline = ['/usr/bin/sandbox-exec', '-f', str(run/'source/offline-loopback.sb')]
    adb = [str(a.sdk/'platform-tools/adb'), '-H', '127.0.0.1', '-P', '5043']; serial = ['-s', 'emulator-5582']
    index = 0; emulator = None; boot = False; result = 'failed'; phase = 'start'; error = ''; started = now(); phases = []
    policy = None; system = None; boot_id = None; apk_path = None; native_dir = None; cleanup_errors = []
    def call(name, args, timeout=20, check=True):
        nonlocal index
        index += 1; prefix = run/(f'{index:03d}-'+name)
        with (run/'commands.jsonl').open('a') as f: f.write(json.dumps(dict(utc=now(), name=name, argv=args))+'\n')
        client = [str(a.sdk/'platform-tools/adb'), '-P', '5043'] if name == 'server' else adb
        r = subprocess.run(offline+client+args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        prefix.with_suffix('.stdout').write_bytes(r.stdout); prefix.with_suffix('.stderr').write_bytes(r.stderr)
        write_toml(prefix.with_suffix('.toml'), dict(returncode=r.returncode))
        if check: assert r.returncode == 0, (name, r.returncode, r.stderr.decode(errors='replace'))
        return r
    def shell(name, command, **kwargs): return call(name, serial+['shell', '-T', command], **kwargs)
    def wait_boot():
        nonlocal boot
        deadline = time.monotonic()+180
        while time.monotonic() < deadline:
            assert emulator.poll() is None, 'emulator exited'
            r = call('boot', serial+['shell', 'getprop', 'sys.boot_completed'], check=False)
            if r.stdout.strip() == b'1': boot = True; return
            time.sleep(2)
        raise AssertionError('boot deadline')
    def identity(label, new_boot=False):
        nonlocal policy, system, boot_id
        call(label+'-root', serial+['root']); call(label+'-wait', serial+['wait-for-device'])
        assert b'uid=0(root)' in shell(label+'-id', 'id').stdout
        current_policy = call(label+'-policy-bytes', serial+['exec-out', 'cat', '/sys/fs/selinux/policy']).stdout
        assert current_policy and shell(label+'-enforcing', 'getenforce').stdout.strip() == b'Enforcing'
        current_system = shell(label+'-system-server', 'pidof system_server').stdout.strip()
        current_boot = shell(label+'-boot-id', 'cat /proc/sys/kernel/random/boot_id').stdout.strip()
        assert re.fullmatch(rb'[0-9a-f-]{36}', current_boot) and current_system.isdigit()
        if policy is not None: assert current_policy == policy, 'SELinux policy changed'
        if boot_id is not None:
            if new_boot: assert current_boot != boot_id, 'boot identity did not change'
            else: assert current_boot == boot_id and current_system == system, 'unexpected guest restart'
        policy, system, boot_id = current_policy, current_system, current_boot
        return current_boot.decode()
    with zipfile.ZipFile(run/'build/probe.apk') as apk:
        info = apk.getinfo('lib/arm64-v8a/libscope-auklet.so')
        raw = (run/'build/probe.apk').read_bytes(); namesize, extrasize = struct.unpack_from('<HH', raw, info.header_offset+26)
        member_offset = info.header_offset+30+namesize+extrasize
        assert member_offset % 4096 == 0
    def observe(label, expected=None, sidecar_present=False):
        nonlocal apk_path, native_dir
        dest = run/'phases'/label; dest.mkdir()
        shell(label+'-force-stop', 'am force-stop lab.mho900.loader')
        shell(label+'-clear-old-evidence', 'rm -f /data/data/lab.mho900.loader/files/result.toml /data/data/lab.mho900.loader/files/maps.txt /data/data/lab.mho900.loader/files/failure.txt')
        shell(label+'-launch', 'am start -W -n lab.mho900.loader/.ProbeActivity', timeout=30)
        deadline = time.monotonic()+20; observed = None
        while time.monotonic() < deadline:
            failure = shell(label+'-probe-error', 'test ! -f /data/data/lab.mho900.loader/files/failure.txt', check=False)
            if failure.returncode:
                call(label+'-pull-failure', serial+['pull', '/data/data/lab.mho900.loader/files/failure.txt', str(dest/'failure.txt')])
                raise AssertionError('application probe failed')
            r = call(label+'-probe-result', serial+['exec-out', 'cat', '/data/data/lab.mho900.loader/files/result.toml'], check=False)
            if r.returncode == 0 and r.stdout:
                (dest/'result.toml').write_bytes(r.stdout); observed = tomllib.loads(r.stdout.decode()); break
            time.sleep(1)
        assert observed is not None, 'probe result deadline'
        assert observed['schema'] == 'mho900-lab.normal-apk-native-loader/1'
        marker = observed['marker']; assert marker in (17, 18)
        if expected is not None: assert marker == expected, (label, marker, expected)
        assert re.fullmatch(r'/data/app/lab\.mho900\.loader-[0-9]+/base\.apk', observed['source_dir'])
        assert observed['native_library_dir'] == observed['source_dir'].removesuffix('/base.apk')+'/lib/arm64'
        if apk_path is not None: assert apk_path == observed['source_dir'] and native_dir == observed['native_library_dir']
        apk_path, native_dir = observed['source_dir'], observed['native_library_dir']
        maps = call(label+'-probe-maps', serial+['exec-out', 'cat', '/data/data/lab.mho900.loader/files/maps.txt']).stdout
        (dest/'maps.txt').write_bytes(maps)
        if marker == 17:
            assert observed['found_library'] == apk_path+'!/lib/arm64-v8a/libscope-auklet.so'
            assert any(line.split()[-1] == apk_path and int(line.split()[2], 16) == member_offset for line in maps.decode().splitlines())
            assert native_dir+'/libscope-auklet.so' not in maps.decode()
        else:
            assert sidecar_present and observed['found_library'] == native_dir+'/libscope-auklet.so'
            assert any(line.split()[-1] == native_dir+'/libscope-auklet.so' for line in maps.decode().splitlines())
        call(label+'-apk-pull', serial+['pull', apk_path, str(dest/'base.apk')])
        assert sha(dest/'base.apk') == sha(run/'build/probe.apk'), 'installed APK changed'
        call(label+'-package', serial+['shell', 'dumpsys', 'package', 'lab.mho900.loader'])
        shell(label+'-file-metadata', 'ls -ldZ '+shlex.quote(native_dir)+' '+shlex.quote(apk_path))
        if sidecar_present:
            call(label+'-sidecar-pull', serial+['pull', native_dir+'/libscope-auklet.so', str(dest/'sidecar.so')])
            assert sha(dest/'sidecar.so') == sha(run/'build/marker-18.so')
            shell(label+'-sidecar-metadata', 'ls -lZ '+shlex.quote(native_dir+'/libscope-auklet.so'))
        else: shell(label+'-sidecar-absent', 'test ! -e '+shlex.quote(native_dir+'/libscope-auklet.so'))
        same_boot = identity(label+'-health')
        record = dict(label=label, marker=marker, pid=observed['pid'], boot_id=same_boot, installed_apk_sha256=sha(dest/'base.apk'), sidecar_present=sidecar_present, found_library=observed['found_library'])
        write_toml(dest/'verification.toml', record); phases.append(record)
        return marker
    def reboot(label):
        nonlocal boot
        call(label+'-reboot', serial+['reboot']); boot = False
        time.sleep(2); wait_boot(); identity(label, new_boot=True)
    try:
        call('server', ['--one-device', 'emulator-5582', 'start-server'])
        mdns = call('mdns', ['mdns', 'check'], check=False); assert b'mdns discovery disabled' in mdns.stdout+mdns.stderr
        argv = [str(a.sdk/'emulator/emulator'), '-avd', 'baseline-api25', '-sysdir', str(image), '-data', str(run/'userdata.img'), '-cache', str(run/'cache.img'), '-port', '5582', '-no-window', '-no-snapshot', '-no-boot-anim', '-no-audio', '-no-metrics', '-gpu', 'swiftshader', '-memory', '2048', '-cores', '2', '-verbose', '-show-kernel']
        (run/'emulator-argv.txt').write_text('\n'.join(argv)+'\n')
        emulator = subprocess.Popen(offline+argv, env=env, stdout=(run/'emulator.log').open('wb'), stderr=subprocess.STDOUT)
        phase = 'boot'; wait_boot(); identity('initial')
        phase = 'install'; install = call('install', serial+['install', '--no-streaming', str(run/'build/probe.apk')], timeout=40)
        assert b'Success' in install.stdout
        phase = 'baseline'; observe('baseline', 17)
        phase = 'publish-sidecar'
        target = native_dir+'/libscope-auklet.so'; staging = native_dir+'/libscope-auklet.staged'
        shell('require-sidecar-absent', 'test ! -e '+shlex.quote(target)+' && test ! -e '+shlex.quote(staging))
        call('stage-sidecar', serial+['push', str(run/'build/marker-18.so'), staging])
        call('roundtrip-staged-sidecar', serial+['pull', staging, str(run/'staged-roundtrip.so')]); assert sha(run/'staged-roundtrip.so') == sha(run/'build/marker-18.so')
        shell('publish-sidecar', 'chown 1000:1000 '+shlex.quote(staging)+' && chmod 644 '+shlex.quote(staging)+' && mv '+shlex.quote(staging)+' '+shlex.quote(target))
        phase = 'sidecar-process'; sidecar_marker = observe('sidecar-process', sidecar_present=True)
        phase = 'sidecar-reboot'; reboot('sidecar-reboot'); observe('sidecar-reboot', sidecar_marker, True)
        phase = 'remove-sidecar'; shell('remove-sidecar', 'rm '+shlex.quote(target))
        phase = 'rollback-process'; observe('rollback-process', 17)
        phase = 'rollback-reboot'; reboot('rollback-reboot'); observe('rollback-reboot', 17)
        assert phases[0]['pid'] != phases[1]['pid'] and phases[2]['pid'] != phases[3]['pid']
        phase = 'complete'; result = 'accepted'
    except BaseException as exc:
        import traceback
        error = str(exc); (run/'failure.txt').write_text(traceback.format_exc())
    finally:
        def cleanup(name, action):
            try: action()
            except BaseException as exc: cleanup_errors.append(name+': '+str(exc))
        if boot: cleanup('final-logcat', lambda: call('final-logcat', serial+['logcat', '-b', 'all', '-d'], check=False))
        if emulator:
            cleanup('emulator-stop', lambda: call('emulator-stop', serial+['emu', 'kill'], check=False))
            try: emulator.wait(timeout=15)
            except subprocess.TimeoutExpired: cleanup('emulator-terminate', lambda: (emulator.terminate(), emulator.wait(timeout=10)))
        cleanup('server-stop', lambda: call('server-stop', ['kill-server'], check=False))
        original = result
        if cleanup_errors: result = 'failed'
        write_toml(run/'result.toml', dict(schema='mho900-lab.native-loader-control/1', result=result, original_result=original, phase=phase, error=error, cleanup_errors=cleanup_errors, started_at=started, finished_at=now(), physical_access=False, phase_count=len(phases), sidecar_precedence=(len(phases)>1 and phases[1]['marker']==18)))
    print((run/'result.toml').read_text())
    return 0 if result == 'accepted' else 1


if __name__ == '__main__': raise SystemExit(main())
