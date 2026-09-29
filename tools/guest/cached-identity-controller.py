#!/usr/bin/env python3
"""Separate synthetic ART setup from a bounded external cached-state reader.

Only the dedicated loopback emulator and ADB server are accepted. Frida is
unloaded and detached before any reader invocation. No specimen endpoint exists.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import threading
import tomllib

import frida

STOCK = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
GUEST = '/data/local/tmp/entitlement'
LIBRARY = GUEST + '/lib/libscope-auklet.so'
READER = GUEST + '/cached-identity-reader'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def write_toml(path, values):
    with path.open('x') as stream:
        for key, value in values.items():
            stream.write(key + ' = ' + json.dumps(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def starttime(raw, pid):
    text = raw.decode('ascii').strip()
    require(text.startswith(str(pid) + ' ('), 'Process stat PID mismatch')
    tail = text[text.rindex(')') + 2:].split()
    require(len(tail) >= 20 and tail[19].isdigit(), 'Malformed process stat')
    return tail[19]


def main():
    require(len(sys.argv) == 2, 'Pass one frozen setup script')
    run = Path(os.environ['ENTITLEMENT_RUN'])
    adb = Path(os.environ['ENTITLEMENT_ADB'])
    require(run.is_absolute() and run.is_dir() and adb.is_absolute() and adb.is_file(), 'Invalid local paths')
    require(os.environ['ENTITLEMENT_ADB_PORT'] == '5043'
            and os.environ['ENTITLEMENT_SERIAL'] == 'emulator-5582'
            and os.environ['ENTITLEMENT_FRIDA_ENDPOINT'] == '127.0.0.1:27045'
            and os.environ['ENTITLEMENT_HOST'] == 'art', 'Dedicated guest endpoints required')
    require(hashlib.sha256((run / 'fixture/lib/libscope-auklet.so').read_bytes()).hexdigest() == STOCK,
            'Stock setup library pin differs')
    source = Path(sys.argv[1]).read_text()
    reader_root = run / 'reader'
    reader_root.mkdir(exist_ok=False)
    restoration_root = reader_root / 'setup-restoration'
    restoration_root.mkdir(exist_ok=False)
    restoration_artifacts = {}
    restoration_events = []
    restoration_names = {'maps-before.txt', 'rx-before.bin', 'maps-after-hooks-removed.txt',
                         'rx-after-hooks-removed.bin', 'maps-restored.txt'}
    sink = (run / 'controller.jsonl').open('x')
    lock = threading.Lock()
    ready = threading.Event()
    returned = threading.Event()
    art_ready = threading.Event()
    detached = threading.Event()
    errors, witnesses = [], []
    session = script = device = None
    pid = None
    identity = None
    output_buffer = bytearray()
    result = 3
    setup_policy_changed = False
    setup_policy_observed = False
    setup_detached = False
    negative_controls_passed = 0
    positive_samples_match = False
    after_setup = None
    after_read_started = False

    def record(kind, **fields):
        value = {'kind': kind, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), **fields}
        with lock:
            if sink.closed:
                return
            line = json.dumps(value)
            sink.write(line + '\n')
            sink.flush()
            print(line, flush=True)

    def durable():
        with lock:
            sink.flush()
            os.fsync(sink.fileno())
            sys.stdout.flush()
            require(stat.S_ISREG(os.fstat(sys.stdout.fileno()).st_mode), 'Regular stdout evidence sink required')
            os.fsync(sys.stdout.fileno())

    def adb_call(arguments, timeout=30):
        environment = dict(os.environ)
        environment.pop('ADB_SERVER_SOCKET', None)
        environment.pop('ANDROID_ADB_SERVER_PORT', None)
        return subprocess.run([str(adb), '-H', '127.0.0.1', '-P', '5043', '-s', 'emulator-5582', *arguments],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=environment)

    def shell(arguments, timeout=30):
        return adb_call(['shell', shlex.join([str(x) for x in arguments])], timeout)

    def read_guest(path):
        response = shell(['cat', path])
        require(response.returncode == 0, 'Guest metadata read failed: ' + path)
        return response.stdout

    def snapshot(label, target=None):
        directory = reader_root / label
        directory.mkdir(exist_ok=False)
        enforcement = shell(['getenforce'])
        policy = adb_call(['exec-out', 'cat', '/sys/fs/selinux/policy'])
        require(enforcement.returncode == policy.returncode == 0, 'Guest policy evidence unavailable')
        require(enforcement.stdout.strip() == b'Enforcing', 'Guest is not enforcing')
        require(0 < len(policy.stdout) <= 16 * 1024 * 1024, 'Guest policy evidence size invalid')
        policy_hash = hashlib.sha256(policy.stdout).hexdigest()
        boot = read_guest('/proc/sys/kernel/random/boot_id')
        (directory / 'policy.bin').write_bytes(policy.stdout)
        (directory / 'enforcement.txt').write_bytes(enforcement.stdout)
        (directory / 'policy-sha256.txt').write_text(policy_hash + '  /sys/fs/selinux/policy\n')
        (directory / 'boot-id.txt').write_bytes(boot)
        state = {'enforcement': enforcement.stdout, 'policy': policy.stdout, 'boot': boot}
        if target is not None:
            for name in ('stat', 'status', 'maps'):
                state[name] = read_guest('/proc/' + str(target) + '/' + name)
                (directory / (name + '.txt')).write_bytes(state[name])
            require(any(line.strip() == b'TracerPid:\t0' for line in state['status'].splitlines()), 'Target remains traced')
        record('host-guest-state-snapshot', label=label, pid=target, enforcement='Enforcing',
               policy_sha256=policy_hash, boot_id=boot.decode().strip())
        return state

    def on_message(message, data):
        payload = message.get('payload', {}) if message.get('type') == 'send' else {}
        if payload.get('kind') == 'cached-setup-artifact':
            try:
                name = payload.get('name')
                require((name in restoration_names or name in {'raw-maps-1.txt', 'raw-maps-2.txt', 'raw-maps-3.txt'})
                        and name not in restoration_artifacts,
                        'Unexpected or duplicate setup artifact')
                require(isinstance(data, bytes) and 0 < len(data) <= 0xb69000
                        and payload.get('size') == len(data)
                        and payload.get('sha256') == hashlib.sha256(data).hexdigest(),
                        'Setup artifact payload/hash differs')
                with (restoration_root / name).open('xb') as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                restoration_artifacts[name] = payload['sha256']
            except BaseException as error:
                errors.append('setup-artifact: ' + str(error))
                ready.set()
                returned.set()
        if payload.get('kind') == 'setup-mapping-restoration-complete':
            restoration_events.append(payload)
        record('frida-message', message=message, attachment_bytes=len(data) if data else 0)
        if message.get('type') == 'error':
            errors.append('setup-script-error')
            ready.set()
            returned.set()
        if message.get('type') != 'send':
            return
        payload = message.get('payload', {})
        kind = payload.get('kind')
        if kind == 'failure':
            errors.append('setup-failure')
            if payload.get('terminal_ack'):
                durable()
                script.post({'type': 'terminal-ack'})
            ready.set()
            returned.set()
        elif kind == 'cached-identity-ready':
            witnesses.append(payload)
            if (len(restoration_events) != 1 or not restoration_names.issubset(restoration_artifacts)
                    or payload.get('setup_restoration_complete') is not True
                    or restoration_events[0].get('mappings_equal') is not True
                    or restoration_events[0].get('code_bytes_equal') is not True
                    or restoration_artifacts.get('rx-before.bin') != restoration_artifacts.get('rx-after-hooks-removed.bin')):
                errors.append('setup-restoration-proof-incomplete')
                ready.set()
                returned.set()
                return
            durable()
            script.post({'type': 'cached-identity-ack'})
            record('cached-identity-acknowledged', sequence=payload['sequence'])
            ready.set()
        elif kind == 'cached-identity-setup-returned':
            returned.set()

    def on_output(output_pid, fd, data):
        record('process-output', pid=output_pid, fd=fd, text=data.decode('utf-8', errors='replace'))
        if output_pid == pid and fd == 1:
            output_buffer.extend(data)
            if len(output_buffer) > 65536:
                errors.append('host-output-overflow')
                art_ready.set()
            elif b'ART_HOST_READY lab.mho900.guest.EntitlementHost\n' in output_buffer:
                art_ready.set()

    def on_detached(reason, crash):
        record('frida-detached-callback', reason=reason, crash=str(crash) if crash else '')
        if crash:
            errors.append('setup-target-crash')
        detached.set()

    try:
        before = snapshot('before-setup')
        device = frida.get_device_manager().add_remote_device('127.0.0.1:27045')
        device.on('output', on_output)
        argv = ['/system/bin/app_process64', '-Djava.library.path=' + GUEST + '/lib',
                '/system/bin', 'lab.mho900.guest.EntitlementHost']
        environment = {'CLASSPATH': GUEST + '/art/host.jar:' + GUEST + '/art/stock.apk',
                       'LD_LIBRARY_PATH': GUEST + '/lib'}
        pid = device.spawn(argv, env=environment, stdio='pipe')
        record('spawned', pid=pid, argv=argv, environment=environment)
        identity = (pid, starttime(read_guest('/proc/' + str(pid) + '/stat'), pid),
                    read_guest('/proc/sys/kernel/random/boot_id').decode().strip())
        record('spawn-identity-recorded', pid=pid, starttime=identity[1], boot_id=identity[2])
        session = device.attach(pid)
        session.on('detached', on_detached)
        device.resume(pid)
        require(art_ready.wait(15) and not errors and not detached.is_set(), 'Actual ART host readiness failed')
        script = session.create_script(source)
        script.on('message', on_message)
        script.load()
        require(ready.wait(45) and returned.wait(10) and not errors and len(witnesses) == 1,
                'Setup did not return one durable ready witness')
        witness = witnesses[0]
        require(witness['pid'] == pid and witness['module_path'] == LIBRARY and witness['stock_native_sha256'] == STOCK
                and witness['started_false'] is True and witness['stock_calls_complete'] is True
                and witness['synthetic_only'] is True and witness['physical_contact'] is False,
                'Setup witness differs from fixed contract')
        expected = bytes.fromhex(witness['expected_sample_hex'])
        require(len(expected) == 24 and expected[:8].hex() == 'efcdab8967452301'
                and expected.hex() == witness['expected_dna_hex'] + witness['expected_file_keys_hex'],
                'Setup expected bytes malformed')
        script.unload()
        record('setup-script-unloaded', pid=pid)
        session.detach()
        require(detached.wait(10) and not errors, 'Frida setup detach did not complete')
        record('setup-frida-detached', pid=pid, reader_started=False)
        setup_detached = True
        # No Frida operation or target function call occurs below this point.
        after_setup = snapshot('after-setup', pid)
        require(all(before[k] == after_setup[k] for k in ('enforcement', 'boot')), 'Setup changed guest enforcement or boot')
        setup_policy_changed = before['policy'] != after_setup['policy']
        setup_policy_observed = True
        record('setup-policy-comparison', setup_policy_changed=setup_policy_changed,
               enforcement_unchanged=True, boot_unchanged=True)
        require(identity == (pid, starttime(after_setup['stat'], pid), after_setup['boot'].decode().strip()),
                'Target identity changed during setup')
        require(len(identity[2]) == 36, 'Malformed boot identity')
        write_toml(run / 'setup-expected.toml', {key: value for key, value in witness.items()
                   if isinstance(value, (str, int, bool))} | {'expected_pid': pid,
                   'expected_starttime': identity[1], 'expected_boot_id': identity[2]})
        pull = adb_call(['pull', GUEST + '/events.jsonl', str(run / 'guest-events.jsonl')])
        require(pull.returncode == 0, 'Setup journal pull failed')
        require(shell(['mkdir', '-p', GUEST + '/cached-read']).returncode == 0, 'Reader parent directory failed')
        for mode in ('wrong-pin', 'wrong-starttime', 'unmapped-range', 'positive'):
            output = GUEST + '/cached-read/' + mode
            record('reader-command-start', mode=mode, pid=pid, starttime=identity[1], boot_id=identity[2],
                   module_path=LIBRARY, setup_detached=True)
            response = shell([READER, *identity, LIBRARY, output, mode], timeout=30)
            command_dir = reader_root / (mode + '-command')
            command_dir.mkdir(exist_ok=False)
            (command_dir / 'stdout.txt').write_bytes(response.stdout)
            (command_dir / 'stderr.txt').write_bytes(response.stderr)
            write_toml(command_dir / 'result.toml', {'mode': mode, 'returncode': response.returncode})
            target = reader_root / mode
            pull = adb_call(['pull', output, str(target)])
            require(pull.returncode == 0 and target.is_dir(), 'Reader evidence pull failed: ' + mode)
            (target / 'command.stdout').write_bytes(response.stdout)
            (target / 'command.stderr').write_bytes(response.stderr)
            write_toml(target / 'command.toml', {'mode': mode, 'returncode': response.returncode})
            record('reader-command-complete', mode=mode, returncode=response.returncode)
            require(response.returncode == (0 if mode == 'positive' else 3), 'Unexpected reader result: ' + mode)
            manifest = tomllib.loads((target / 'manifest.toml').read_text())
            require(manifest.get('schema_version') == 'mho900-lab.cached-identity-reader/1'
                    and manifest.get('mode') == mode and manifest.get('pid') == pid, 'Reader manifest identity differs')
            samples = [target / 'sample-1.bin', target / 'sample-2.bin']
            if mode == 'positive':
                require(manifest.get('result') == 'accepted' and manifest.get('error_number') == 0
                        and manifest.get('bytes_read') == 48 and manifest.get('memory_read_calls') == 4
                        and manifest.get('mem_open_count') == 1 and manifest.get('sample_count') == 2
                        and manifest.get('read_results') == [8, 16, 8, 16]
                        and manifest.get('read_requested') == [8, 16, 8, 16]
                        and manifest.get('memory_bytes_requested') == 48
                        and manifest.get('library_sha256') == STOCK and manifest.get('library_path') == LIBRARY
                        and manifest.get('mem_open_flags') == 0
                        and manifest.get('expected_starttime') == int(identity[1])
                        and manifest.get('observed_starttime_before') == manifest.get('observed_starttime_after') == int(identity[1])
                        and manifest.get('expected_boot_id') == manifest.get('boot_id_before') == manifest.get('boot_id_after') == identity[2]
                        and int(manifest['load_bias'], 0) == int(witness['module_base'], 0)
                        and int(manifest['dna_address'], 0) == int(witness['module_base'], 0) + 0xbbccf0
                        and int(manifest['file_keys_address'], 0) == int(witness['module_base'], 0) + 0xbbcd1c
                        and all(manifest.get(field) is True for field in ('repeat_equal', 'identity_stable', 'maps_stable', 'file_stable'))
                        and all(manifest.get(field) is False for field in ('target_attached', 'target_calls', 'target_writes')),
                        'Positive reader manifest contract differs')
                require(all(path.is_file() and path.read_bytes() == expected for path in samples),
                        'External samples differ from independent setup witness')
                positive_samples_match = True
                record('reader-samples-compared', mode=mode, samples=2, bytes_per_sample=24,
                       matches_setup=True, samples_sha256=hashlib.sha256(expected).hexdigest())
            else:
                expected_stage = {'wrong-pin': 'library-hash', 'wrong-starttime': 'process-identity',
                                  'unmapped-range': 'target-ranges'}[mode]
                require(manifest.get('result') == 'rejected' and manifest.get('stage') == expected_stage
                        and not any(path.exists() for path in samples)
                        and all(manifest.get(field) == 0 for field in ('bytes_read', 'mem_open_count', 'memory_read_calls',
                                                                    'memory_bytes_requested'))
                        and manifest.get('read_requested') == manifest.get('read_results') == [],
                        'Negative reader control did not reject at its intended boundary')
                negative_controls_passed += 1
        after_read_started = True
        after_read = snapshot('after-read', pid)
        require(all(after_setup[k] == after_read[k] for k in ('enforcement', 'policy', 'boot')),
                'Reader changed guest policy or boot')
        require(starttime(after_read['stat'], pid) == identity[1], 'Target identity changed during controls')
        result = 0
    except BaseException as error:
        errors.append(str(error))
        record('controller-failure', error=str(error))
    finally:
        if session is not None and not session.is_detached:
            session.detach()
        if pid is not None and after_setup is not None and not after_read_started:
            try:
                require(identity is not None and starttime(read_guest('/proc/' + str(pid) + '/stat'), pid) == identity[1]
                        and read_guest('/proc/sys/kernel/random/boot_id').decode().strip() == identity[2],
                        'Refusing final snapshot of unverified or recycled PID')
                after_read_started = True
                final_read = snapshot('after-read', pid)
                require(all(after_setup[k] == final_read[k] for k in ('enforcement', 'policy', 'boot')),
                        'Failed reader phase changed guest policy or boot')
                require(starttime(final_read['stat'], pid) == identity[1], 'Final target identity changed')
            except BaseException as error:
                result = 3
                errors.append('final-read-snapshot: ' + str(error))
                record('final-read-snapshot-failed', error=str(error))
        if pid is not None:
            try:
                raw = read_guest('/proc/' + str(pid) + '/stat')
                require(identity is not None and starttime(raw, pid) == identity[1]
                        and read_guest('/proc/sys/kernel/random/boot_id').decode().strip() == identity[2],
                        'Refusing cleanup of unverified or recycled PID')
                require(shell(['kill', '-TERM', str(pid)]).returncode == 0, 'Own host cleanup failed')
                record('cleanup-killed', pid=pid)
            except BaseException as error:
                result = 3
                errors.append('cleanup: ' + str(error))
                record('cleanup-failed', pid=pid, error=str(error))
        summary = {'controller_exit': result, 'setup_detached_before_reader': setup_detached,
                   'negative_controls': negative_controls_passed, 'positive_samples_match': positive_samples_match,
                   'setup_policy_observed': setup_policy_observed, 'setup_policy_changed': setup_policy_changed,
                   'physical_contact': False, 'errors': errors}
        write_toml(run / 'controller-result.toml', summary)
        record('controller-result', **summary)
        durable()
        with lock:
            sink.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
