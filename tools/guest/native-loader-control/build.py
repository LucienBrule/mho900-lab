#!/usr/bin/env python3
"""Build the normal APK loader control offline with explicit tool/signing inputs."""
import argparse, hashlib, json, os, shutil, subprocess, zipfile
from pathlib import Path


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk', 'jdk', 'cc', 'ld', 'key', 'cert', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); src = Path(__file__).resolve().parent; out = a.out.resolve()
    assert not out.exists(); out.mkdir(parents=True)
    tools = a.sdk/'build-tools/35.0.0'; android = a.sdk/'platforms/android-35/android.jar'
    env = dict(os.environ, JAVA_HOME=str(a.jdk), PATH=str(a.jdk/'bin')+':'+os.environ['PATH'])
    def run(name, argv):
        with (out/'commands.jsonl').open('a') as f: f.write(json.dumps([str(v) for v in argv])+'\n')
        r = subprocess.run([str(v) for v in argv], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out/(name+'.stdout')).write_bytes(r.stdout); (out/(name+'.stderr')).write_bytes(r.stderr)
        assert r.returncode == 0, (name, r.returncode, r.stderr.decode(errors='replace'))
    for name in ('AndroidManifest.xml', 'ProbeActivity.java', 'marker.c', 'build.py'):
        shutil.copy2(src/name, out/name)
    (out/'classes').mkdir(); (out/'dex').mkdir()
    run('javac', [a.jdk/'bin/javac', '-source', '8', '-target', '8', '-classpath', android, '-d', out/'classes', out/'ProbeActivity.java'])
    run('d8', [tools/'d8', '--min-api', '25', '--lib', android, '--output', out/'dex', out/'classes/lab/mho900/loader/ProbeActivity.class'])
    for marker in (17, 18):
        run('native-'+str(marker), [a.cc, '--target=aarch64-linux-android25', '-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-fPIC', '-shared', '-nostdlib', '-Werror', '-Wall', '-Wextra', '--ld-path='+str(a.ld), '-Wl,-soname,libscope-auklet.so', '-Wl,-z,max-page-size=4096', '-DMARKER='+str(marker), '-o', out/('marker-'+str(marker)+'.so'), out/'marker.c'])
    run('aapt', [tools/'aapt', 'package', '-f', '-M', out/'AndroidManifest.xml', '-I', android, '-F', out/'unsigned.apk'])
    with zipfile.ZipFile(out/'unsigned.apk', 'a') as apk:
        apk.write(out/'dex/classes.dex', 'classes.dex', compress_type=zipfile.ZIP_STORED)
        apk.write(out/'marker-17.so', 'lib/arm64-v8a/libscope-auklet.so', compress_type=zipfile.ZIP_STORED)
    run('align', [tools/'zipalign', '-p', '-f', '4', out/'unsigned.apk', out/'aligned.apk'])
    run('sign', [tools/'apksigner', 'sign', '--key', a.key, '--cert', a.cert, '--v1-signing-enabled', 'false', '--v2-signing-enabled', 'true', '--v3-signing-enabled', 'false', '--v4-signing-enabled', 'false', '--out', out/'probe.apk', out/'aligned.apk'])
    run('verify-signature', [tools/'apksigner', 'verify', '--verbose', '--print-certs', out/'probe.apk'])
    run('verify-align', [tools/'zipalign', '-c', '-p', '4', out/'probe.apk'])
    run('verify-manifest', [tools/'aapt', 'dump', 'xmltree', out/'probe.apk', 'AndroidManifest.xml'])
    with zipfile.ZipFile(out/'probe.apk') as apk:
        assert apk.read('lib/arm64-v8a/libscope-auklet.so') == (out/'marker-17.so').read_bytes()
        assert apk.getinfo('lib/arm64-v8a/libscope-auklet.so').compress_type == zipfile.ZIP_STORED
    rows = ['schema = "mho900-lab.native-loader-build/1"', 'profile = "normal-apk-extract-false"', 'package = "lab.mho900.loader"', 'shared_uid = "android.uid.system"', 'embedded_marker = 17', 'sidecar_marker = 18', '']
    for name, path in [('compiler', a.cc), ('linker', a.ld), ('javac', a.jdk/'bin/javac'), ('android_jar', android), ('certificate', a.cert)]+[(x, tools/x) for x in ('aapt', 'd8', 'apksigner', 'zipalign')]:
        rows += ['[[tool_inputs]]', 'name = '+json.dumps(name), 'sha256 = '+json.dumps(sha(path)), '']
    for path in sorted(out.rglob('*')):
        if path.is_file(): rows += ['[[files]]', 'path = '+json.dumps(str(path.relative_to(out))), 'sha256 = '+json.dumps(sha(path)), '']
    (out/'build.toml').write_text('\n'.join(rows))
    print('Built normal APK, embedded marker17 and standalone marker18; signature/alignment verified.')


if __name__ == '__main__': main()
