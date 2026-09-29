#!/usr/bin/env python3
"""Independently reconcile retained normal-package loader phases without guest I/O."""
import argparse, hashlib, json, struct, tomllib, zipfile
from pathlib import Path


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return tomllib.loads(p.read_text())


def verify(root):
    result = load(root/'result.toml'); assert result['result'] == result['original_result'] == 'accepted'
    assert result['phase'] == 'complete' and result['cleanup_errors'] == [] and not result['physical_access']
    build = root/'build'; bm = load(build/'build.toml')
    assert bm['profile'] == 'normal-apk-extract-false' and bm['shared_uid'] == 'android.uid.system'
    for item in bm['files']: assert sha(build/item['path']) == item['sha256']
    signature = (build/'verify-signature.stdout').read_text()
    assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
    assert 'Verified using v1 scheme (JAR signing): false' in signature
    manifest = (build/'verify-manifest.stdout').read_text()
    assert 'extractNativeLibs' in manifest and 'android.uid.system' in manifest
    with zipfile.ZipFile(build/'probe.apk') as apk:
        i = apk.getinfo('lib/arm64-v8a/libscope-auklet.so'); assert i.compress_type == 0
        assert apk.read(i) == (build/'marker-17.so').read_bytes()
        namesize, extrasize = struct.unpack_from('<HH', (build/'probe.apk').read_bytes(), i.header_offset+26)
        offset = i.header_offset+30+namesize+extrasize; assert offset % 4096 == 0
    labels = ['baseline', 'sidecar-process', 'sidecar-reboot', 'rollback-process', 'rollback-reboot']
    assert sorted(p.name for p in (root/'phases').iterdir()) == sorted(labels)
    phases = [load(root/'phases'/label/'verification.toml') for label in labels]
    sidecar = phases[1]['marker']; assert sidecar in (17, 18)
    assert [p['marker'] for p in phases] == [17, sidecar, sidecar, 17, 17]
    assert [p['sidecar_present'] for p in phases] == [False, True, True, False, False]
    assert phases[0]['boot_id'] == phases[1]['boot_id']
    assert phases[2]['boot_id'] == phases[3]['boot_id']
    assert len({phases[0]['boot_id'], phases[2]['boot_id'], phases[4]['boot_id']}) == 3
    assert phases[0]['pid'] != phases[1]['pid'] and phases[2]['pid'] != phases[3]['pid']
    for label, v in zip(labels, phases):
        phase = root/'phases'/label; probe = load(phase/'result.toml')
        for name in ('marker', 'pid', 'found_library'): assert probe[name] == v[name]
        assert sha(phase/'base.apk') == sha(build/'probe.apk') == v['installed_apk_sha256']
        maps = (phase/'maps.txt').read_text().splitlines()
        if v['marker'] == 17:
            assert v['found_library'] == probe['source_dir']+'!/lib/arm64-v8a/libscope-auklet.so'
            assert any(row.split()[-1] == probe['source_dir'] and int(row.split()[2], 16) == offset for row in maps)
            assert not any(row.split()[-1] == probe['native_library_dir']+'/libscope-auklet.so' for row in maps)
        else:
            assert v['found_library'] == probe['native_library_dir']+'/libscope-auklet.so'
            assert any(row.split()[-1] == v['found_library'] for row in maps)
        if v['sidecar_present']: assert sha(phase/'sidecar.so') == sha(build/'marker-18.so')
    commands = [json.loads(line) for line in (root/'commands.jsonl').read_text().splitlines()]
    policy = []; enforcing = []; health = {}; reboots = 0
    for index, command in enumerate(commands, 1):
        argv = command['argv']; name = command['name']; prefix = root/(f'{index:03d}-'+name)
        assert argv[:2] == ['-s', 'emulator-5582'] or name in ('server', 'server-stop', 'mdns')
        if argv[2:] == ['reboot']: reboots += 1
        output = prefix.with_suffix('.stdout').read_bytes()
        if name.endswith('-policy-bytes'): assert output; policy.append(output)
        if name.endswith('-enforcing'): enforcing.append(output.strip())
        if name.endswith('-system-server'):
            label = name.removesuffix('-system-server'); health[label] = output.strip()
    assert reboots == 2 and len(policy) == 8 and len(enforcing) == 8
    assert len({hashlib.sha256(b).hexdigest() for b in policy}) == 1 and set(enforcing) == {b'Enforcing'}
    assert health['initial'] == health['baseline-health'] == health['sidecar-process-health']
    assert health['sidecar-reboot'] == health['sidecar-reboot-health'] == health['rollback-process-health']
    assert health['rollback-reboot'] == health['rollback-reboot-health']
    assert result['sidecar_precedence'] == (sidecar == 18)
    return dict(schema='mho900-lab.native-loader-verification/1', accepted=True, normal_package_install=True,
                phase_count=5, actual_guest_reboots=2, signed_apk_unchanged=True,
                sidecar_precedence=sidecar == 18, removal_restores_embedded=True,
                guest_enforcing=True, policy_unchanged=True, physical_access=False)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('run', type=Path); a=p.parse_args()
    for k,v in verify(a.run).items(): print(k+' = '+json.dumps(v))


if __name__ == '__main__': main()
