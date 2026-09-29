#!/usr/bin/env python3
"""Independently verify the bounded synthetic cached-state reader control."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import tomllib

STOCK_SHA256 = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'
PAGE = 4096
LIMIT = (1 << 64) - 1
RANGES = ((0xbbccf0, 8, 0xbbbcf0), (0xbbcd1c, 16, 0xbbbd1c))
LOADS = ((5, 0, 0, 0xb689d4, 0xb689d4),
         (6, 0xb68c00, 0xb69c00, 0x77200, 0x314ad10))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def add(left, right):
    require(0 <= left <= LIMIT and 0 <= right <= LIMIT - left, 'Address arithmetic overflow')
    return left + right


def floor(value):
    return value & -PAGE


def ceiling(value):
    return add(value, PAGE - 1) & -PAGE


def elf_loads(data, pin=True):
    require(len(data) >= 64 and data[:7] == b'\x7fELF\x02\x01\x01', 'Not ELF64 little endian')
    header = struct.unpack_from('<HHIQQQIHHHHHH', data, 16)
    kind, machine, version, _, phoff, _, _, ehsize, phentsize, phnum, _, _, _ = header
    require((kind, machine, version, ehsize, phentsize) == (3, 183, 1, 64, 56)
            and 0 < phnum <= 64 and add(phoff, phnum * phentsize) <= len(data),
            'ELF header geometry differs')
    loads = []
    for index in range(phnum):
        ptype, flags, offset, va, _, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', data, phoff + index * phentsize)
        if ptype != 1:
            continue
        require(filesz <= memsz and add(offset, filesz) <= len(data)
                and add(va, memsz) <= LIMIT and align >= PAGE and align & (align - 1) == 0
                and offset % PAGE == va % PAGE, 'Invalid PT_LOAD geometry')
        loads.append((flags, offset, va, filesz, memsz))
    require(tuple(loads) == LOADS, 'Unexpected stock PT_LOAD segments')
    if pin:
        require(sha(data) == STOCK_SHA256, 'Native library differs from pinned stock')
    return loads


def maps_rows(text):
    rows = []
    for line in text.splitlines():
        match = re.fullmatch(r'([0-9a-f]+)-([0-9a-f]+) ([r-][w-][x-][ps]) ([0-9a-f]+) ([0-9a-f]+):([0-9a-f]+) ([0-9]+)(?:\s+(.*))?', line)
        require(match is not None, 'Malformed maps row')
        lo, hi, perms, offset, major, minor, inode, path = match.groups()
        row = dict(start=int(lo, 16), end=int(hi, 16), perms=perms, offset=int(offset, 16),
                   major=int(major, 16), minor=int(minor, 16), inode=int(inode), path=path or '')
        require(0 <= row['start'] < row['end'] <= LIMIT and row['start'] % PAGE == 0
                and row['end'] % PAGE == 0 and row['offset'] % PAGE == 0, 'Unaligned or invalid mapping')
        require(not rows or rows[-1]['end'] <= row['start'], 'Overlapping or unordered maps')
        rows.append(row)
    require(rows, 'Empty maps')
    return rows


def resolve(loads, rows, library, identity):
    """Intersect PT_LOAD-derived biases, allowing separate RELRO rows."""
    major, minor, inode = identity
    require(inode > 0 and library.startswith('/') and not library.endswith(' (deleted)'), 'Invalid backing identity')
    matching = []
    for row in rows:
        same_file = (row['major'], row['minor'], row['inode']) == identity
        if row['path'] == library or same_file or row['path'] == library + ' (deleted)':
            require(same_file and row['path'] == library and row['perms'][3] == 'p',
                    'Deleted, substituted or shared library mapping')
            matching.append(row)
    require(matching, 'Backing library has no mappings')
    possibilities = None
    executable = False
    for row in matching:
        candidates = set()
        for flags, offset, va, filesz, _ in loads:
            if not (floor(offset) <= row['offset'] < ceiling(offset + filesz)):
                continue
            if add(row['offset'], row['end'] - row['start']) > ceiling(offset + filesz):
                continue
            if 'x' in row['perms'] and not flags & 1 or 'w' in row['perms'] and not flags & 2:
                continue
            displaced_va = add(floor(va), row['offset'] - floor(offset))
            if row['start'] < displaced_va:
                continue
            bias = row['start'] - displaced_va
            if bias % PAGE == 0:
                candidates.add(bias)
        require(candidates, 'Mapping is inconsistent with every stock PT_LOAD')
        possibilities = candidates if possibilities is None else possibilities & candidates
        require(possibilities, 'Executable and data mappings have inconsistent load bias')
        executable |= 'x' in row['perms']
    require(executable and len(possibilities) == 1, 'Load bias is missing or ambiguous')
    bias = next(iter(possibilities))
    resolved = []
    for va, size, file_offset in RANGES:
        address = add(bias, va)
        end = add(address, size)
        covering = [row for row in matching if row['start'] <= address and end <= row['end']]
        require(len(covering) == 1 and covering[0]['perms'] == 'rw-p',
                'Cached range is not ordinary writable/readable private non-executable file data')
        row = covering[0]
        require(add(row['offset'], address - row['start']) == file_offset,
                'Runtime/file range geometry differs')
        segment = [item for item in loads if item[0] == 6 and item[2] <= va
                   and va + size <= item[2] + item[3] and item[1] + va - item[2] == file_offset]
        require(len(segment) == 1, 'Cached range is not in stock file-backed writable PT_LOAD')
        resolved.append(address)
    return bias, resolved


def proc_identity(text):
    match = re.fullmatch(r'([1-9][0-9]*) \((.*)\) (.*)\s*', text.strip())
    require(match is not None, 'Malformed proc stat')
    fields = match.group(3).split()
    require(len(fields) >= 20 and fields[19].isdigit(), 'Missing process starttime')
    return int(match.group(1)), int(fields[19])


def c_controls(source, elf, maps_text, variants, malformed, stat_text, bias, library):
    """Exercise the reader's pure parsing code on the host; no proc memory access."""
    wrapper = '#define READER_HOST_TEST\n#include ' + json.dumps(str(source.resolve())) + '\n'
    wrapper += '''
void test_hash(const void *p, U n, char *out) { hash_bytes(p, n, out); }
int test_elf(const B *p, U n) { return validate_elf(p, n); }
int test_maps(const char *text, const char *path, U dev, U ino, U *bias) {
    return resolve_maps(text, path, dev, ino, bias);
}
int test_stat(const char *text, U pid, U *out) { return parse_starttime(text, pid, out); }
int test_invalid_range(const char *text, const char *path, U dev, U ino, U *bias) {
    return resolve_maps_ranges(text, path, dev, ino, bias, 0, KEYS);
}
int test_selected_equal(const char *a, const char *b, const char *path, U dev, U ino) {
    return selected_maps_equal(a, b, path, dev, ino);
}
'''
    require(ctypes.sizeof(ctypes.c_ulong) == 8, 'Host C control requires 64-bit unsigned long')
    with tempfile.TemporaryDirectory(prefix='cached-reader-control-') as temporary:
        directory = Path(temporary)
        wrapper_path = directory / 'control.c'
        binary = directory / ('control.dylib' if sys.platform == 'darwin' else 'control.so')
        wrapper_path.write_text(wrapper)
        compiler = '/usr/bin/clang'
        command = [compiler, '-O2', '-fPIC', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                   str(wrapper_path), '-o', str(binary)]
        compiled = subprocess.run(command, capture_output=True, text=True)
        require(compiled.returncode == 0, 'Host control compilation failed: ' + compiled.stderr)
        native = ctypes.CDLL(str(binary))
        native.test_hash.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
        native.test_hash.restype = None
        native.test_elf.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        native.test_elf.restype = ctypes.c_int
        native.test_maps.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong,
                                     ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        native.test_maps.restype = ctypes.c_int
        native.test_stat.argtypes = [ctypes.c_char_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        native.test_stat.restype = ctypes.c_int
        native.test_invalid_range.argtypes = native.test_maps.argtypes
        native.test_invalid_range.restype = ctypes.c_int
        native.test_selected_equal.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                                               ctypes.c_ulong, ctypes.c_ulong]
        native.test_selected_equal.restype = ctypes.c_int
        for data in (b'', b'abc', elf):
            output = ctypes.create_string_buffer(65)
            native.test_hash(data, len(data), output)
            require(output.value.decode() == sha(data), 'Reader SHA-256 differs from independent host implementation')
        require(native.test_elf(elf, len(elf)) == 1 and native.test_elf(bytes(malformed), len(malformed)) == 0,
                'Reader ELF control differs')
        observed = ctypes.c_ulong()
        require(native.test_maps(maps_text.encode(), library.encode(), 0xfd01, 42, ctypes.byref(observed)) == 1
                and observed.value == bias, 'Reader RELRO/data-offset resolution differs')
        for name, text in variants.items():
            require(native.test_maps(text.encode(), library.encode(), 0xfd01, 42, ctypes.byref(observed)) == 0,
                    'Reader accepted host mapping negative: ' + name)
        require(native.test_invalid_range(maps_text.encode(), library.encode(), 0xfd01, 42,
                                          ctypes.byref(observed)) == 0, 'Reader accepted out-of-contract range')
        unrelated = maps_text + f'\n{bias + 0x5000000:x}-{bias + 0x5001000:x} rw-p 00000000 00:00 0\n'
        require(native.test_selected_equal((maps_text + '\n').encode(), unrelated.encode(), library.encode(), 0xfd01, 42) == 1
                and native.test_maps(unrelated.encode(), library.encode(), 0xfd01, 42, ctypes.byref(observed)) == 1
                and observed.value == bias, 'Unrelated mapping change affected cached-range proof')
        require(native.test_stat(stat_text.encode(), 77, ctypes.byref(observed)) == 1 and observed.value == 12345
                and native.test_stat(stat_text.encode(), 78, ctypes.byref(observed)) == 0,
                'Reader process identity parsing differs')
    return {'reader_c_controls': 'accepted', 'reader_source_sha256': sha(source.read_bytes()),
            'reader_sha_vectors': ['empty', 'abc', 'pinned-stock-library'],
            'reader_invalid_range_rejected': True, 'reader_unrelated_map_change_accepted': True}


def host_controls(elf, source=None):
    loads = elf_loads(elf)
    bias = 0x7000000000
    library = '/synthetic/libscope-auklet.so'
    identity = (253, 1, 42)
    def row(start, end, perms, offset, device='fd:01', inode=42, path=library):
        return f'{bias + start:x}-{bias + end:x} {perms} {offset:08x} {device} {inode} {path}'
    text = '\n'.join((row(0, 0xb69000, 'r-xp', 0),
                      row(0xb69000, 0xb8f000, 'r--p', 0xb68000),
                      row(0xb8f000, 0xbe1000, 'rw-p', 0xb8e000)))
    actual_bias, addresses = resolve(loads, maps_rows(text), library, identity)
    require(actual_bias == bias and addresses == [bias + value[0] for value in RANGES],
            'Valid RELRO split/data-offset control failed')
    rejected = []
    variants = {
        'inconsistent_bias': text.replace(f'{bias + 0xb8f000:x}-{bias + 0xbe1000:x}',
                                          f'{bias + 0xb90000:x}-{bias + 0xbe2000:x}'),
        'device_substitution': text.replace('rw-p 00b8e000 fd:01 42', 'rw-p 00b8e000 00:05 99'),
        'anonymous_substitution': text.rsplit('\n', 1)[0] + '\n' + row(0xb8f000, 0xbe1000, 'rw-p', 0, '00:00', 0, ''),
        'executable_data': text.replace('rw-p', 'rwxp'),
        'shared_data': text.replace('rw-p', 'rw-s'),
        'deleted_file': text.replace(library, library + ' (deleted)'),
    }
    for name, altered in variants.items():
        try:
            resolve(loads, maps_rows(altered), library, identity)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError('Host negative control accepted: ' + name)
    malformed = bytearray(elf)
    phoff = struct.unpack_from('<Q', malformed, 32)[0]
    phnum = struct.unpack_from('<H', malformed, 56)[0]
    for index in range(phnum):
        at = phoff + index * 56
        if struct.unpack_from('<II', malformed, at) == (1, 6):
            struct.pack_into('<Q', malformed, at + 16, 0xb68c00)
            break
    try:
        elf_loads(malformed, pin=False)
    except ValueError:
        rejected.append('incorrect_elf_data_va')
    else:
        raise ValueError('Host ELF geometry corruption accepted')
    try:
        add(LIMIT - 7, 8)
    except ValueError:
        rejected.append('address_overflow')
    else:
        raise ValueError('Host address overflow accepted')
    fields = ['S'] + ['0'] * 18 + ['12345'] + ['0'] * 3
    stat_text = '77 (worker (nested) name) ' + ' '.join(fields) + '\n'
    require(proc_identity(stat_text) == (77, 12345),
            'Process identity parsing control failed')
    result = {'host_controls': 'accepted', 'relro_split': True, 'virtual_file_delta': 4096,
              'negative_controls': rejected, 'proc_stat_nested_name': True}
    if source is not None:
        result.update(c_controls(source, elf, text, variants, malformed, stat_text, bias, library))
    return result


def records(path):
    data = path.read_bytes()
    require(data and data.endswith(b'\n'), 'Empty or incomplete event stream: ' + path.name)
    values = [json.loads(line) for line in data.splitlines()]
    require(all(isinstance(value, dict) for value in values), 'Event stream contains non-object')
    return values


def one(values, kind):
    selected = [item for item in values if item.get('kind') == kind]
    require(len(selected) == 1, 'Expected exactly one ' + kind)
    return selected[0]


def setup_evidence(root):
    journal = records(root / 'guest-events.jsonl')
    host = records(root / 'controller.jsonl')
    require([item.get('sequence') for item in journal] == list(range(1, len(journal) + 1)),
            'Guest journal is not contiguous')
    delivered = []
    delivered_positions = {}
    for position, item in enumerate(host):
        if item.get('kind') != 'frida-message':
            continue
        message = item.get('message', {})
        require(message.get('type') != 'error', 'Setup script emitted error')
        if message.get('type') == 'send':
            payload = message.get('payload')
            require(isinstance(payload, dict), 'Unstructured setup payload')
            delivered.append(payload)
            delivered_positions[payload.get('sequence')] = position
    require(delivered == journal, 'Durable setup journal delivery differs or is incomplete')
    ready = one(journal, 'cached-identity-ready')
    returned = one(journal, 'cached-identity-setup-returned')
    require(returned == journal[-1] and ready['sequence'] < returned['sequence']
            and returned['pid'] == ready['pid'] and returned.get('target_left_alive') is True
            and returned.get('no_further_stock_calls') is True, 'Setup handoff is incomplete')
    require(ready.get('stock_native_sha256') == STOCK_SHA256 and ready.get('started_false') is True
            and ready.get('stock_calls_complete') is True and ready.get('synthetic_only') is True
            and ready.get('physical_contact') is False and ready.get('dna_elf_va') == hex(RANGES[0][0])
            and ready.get('file_keys_elf_va') == hex(RANGES[1][0]), 'Wrong setup contract')
    dna = bytes.fromhex(ready['expected_dna_hex'])
    keys = bytes.fromhex(ready['expected_file_keys_hex'])
    require(dna == bytes.fromhex('efcdab8967452301') and len(keys) == 16
            and ready['expected_sample_hex'] == (dna + keys).hex(), 'Synthetic setup sample differs')
    require(not any(item.get('kind') in ('failure', 'dependency-stop', 'ordinary-installer-enter',
                                       'stock-active-return', 'option-catalog') for item in journal),
            'Setup crossed its bounded identity-only contract')
    calls = [item.get('function', '') for item in journal if item.get('kind') == 'call-enter']
    require(not any('License' in name or 'loadPrivacy' in name or 'PCIeInit' in name for name in calls),
            'Setup invoked excluded native initialization')
    for label in ('API_GetStarted:preflight', 'API_GetStarted:final'):
        observed = [item for item in journal if item.get('kind') == 'call-return' and item.get('function') == label]
        require(len(observed) == 1 and observed[0]['result'] in ('false', '0'), 'Stock started flag differs')
    require(one(journal, 'service-inventory-complete')['count'] == 49, 'Stock factory inventory differs')
    require(calls.count('ApiUtility_GetDNA') == calls.count('ApiUtility_ConvertDNA2Key') == 1,
            'Setup identity initialization call count differs')
    unload, detach = one(host, 'setup-script-unloaded'), one(host, 'setup-frida-detached')
    unload_pos, detach_pos = host.index(unload), host.index(detach)
    require(delivered_positions[returned['sequence']] < unload_pos < detach_pos,
            'Reader handoff did not follow completed setup and instrumentation unload')
    ack = one(host, 'cached-identity-acknowledged')
    require(ack['sequence'] == ready['sequence']
            and delivered_positions[ready['sequence']] < host.index(ack) < unload_pos,
            'Setup ready witness was not durably acknowledged before unload')
    require(not any(item.get('kind') == 'frida-message' for item in host[detach_pos + 1:]),
            'Instrumentation produced events after detach')
    starts = [item for item in host if item.get('kind') == 'reader-command-start']
    completes = [item for item in host if item.get('kind') == 'reader-command-complete']
    modes = ['wrong-pin', 'wrong-starttime', 'unmapped-range', 'positive']
    require([item.get('mode') for item in starts] == modes and [item.get('mode') for item in completes] == modes,
            'Reader control order differs')
    previous = detach_pos
    for start, complete in zip(starts, completes):
        start_pos, end_pos = host.index(start), host.index(complete)
        require(previous < start_pos < end_pos, 'Reader commands overlap or precede detach')
        require(start.get('setup_detached') is True and start['pid'] == ready['pid']
                and start['module_path'] == ready['module_path']
                and complete['returncode'] == (0 if start['mode'] == 'positive' else 3),
                'Reader command contract differs')
        previous = end_pos
    comparison = one(host, 'reader-samples-compared')
    require(previous < host.index(comparison), 'Sample comparison preceded acquisition')
    if any(item.get('kind') == 'cleanup-killed' for item in host):
        require(host.index(comparison) < host.index(one(host, 'cleanup-killed')),
                'Prepared target was killed before comparison')
    expected = tomllib.loads((root / 'setup-expected.toml').read_text())
    for field in ('pid', 'module_base', 'module_path', 'expected_dna_hex', 'expected_file_keys_hex', 'expected_sample_hex'):
        require(expected[field] == ready[field], 'Frozen setup expectation differs from durable witness')
    require(expected['expected_pid'] == ready['pid'], 'Expected PID differs')
    for start in starts:
        require(number(start['starttime']) == number(expected['expected_starttime'])
                and start['boot_id'] == expected['expected_boot_id'], 'Reader target identity differs')
    summary = tomllib.loads((root / 'controller-result.toml').read_text())
    require(summary['controller_exit'] == 0 and summary['setup_detached_before_reader'] is True
            and summary['negative_controls'] == 3 and summary['positive_samples_match'] is True
            and summary['physical_contact'] is False and summary['errors'] == [], 'Controller did not complete')
    require(all(one(host, 'controller-result')[key] == value for key, value in summary.items()),
            'Controller result artifact differs from event')
    return ready, expected, journal, host


def boundary_evidence(root, expected):
    snapshots = [root / 'reader' / label for label in ('before-setup', 'after-setup', 'after-read')]
    for name in ('enforcement.txt', 'boot-id.txt'):
        values = [(directory / name).read_bytes() for directory in snapshots]
        require(values[0] == values[1] == values[2], 'Guest boundary changed: ' + name)
    require((snapshots[0] / 'enforcement.txt').read_text().strip() == 'Enforcing', 'Guest enforcement differs')
    policies, hashes = [], []
    for directory in snapshots:
        policy = (directory / 'policy-sha256.txt').read_text().split()
        require(len(policy) == 2 and re.fullmatch('[0-9a-f]{64}', policy[0])
                and policy[1] == '/sys/fs/selinux/policy', 'Policy hash evidence is malformed')
        raw = (directory / 'policy.bin').read_bytes()
        require(sha(raw) == policy[0], 'Raw policy bytes differ from hash')
        policies.append(raw)
        hashes.append(policy[0])
    require(policies[1] == policies[2], 'Guest policy changed across the detached reader boundary')
    require((snapshots[0] / 'boot-id.txt').read_text().strip() == expected['expected_boot_id'], 'Boot identity differs')
    require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', expected['expected_boot_id']),
            'Malformed boot UUID')
    for directory in snapshots[1:]:
        require(proc_identity((directory / 'stat.txt').read_text())
                == (expected['expected_pid'], number(expected['expected_starttime'])), 'Process identity changed')
        status = (directory / 'status.txt').read_text()
        require(re.search(r'^TracerPid:\s+0\s*$', status, re.MULTILINE), 'Process is still traced')
    return {'policy_before_setup_sha256': hashes[0], 'policy_during_read_sha256': hashes[1],
            'setup_policy_changed': policies[0] != policies[1], 'reader_policy_changed': False}


def device_identity(device, inode):
    major = ((device >> 8) & 0xfff) | ((device >> 32) & 0xfffff000)
    minor = (device & 0xff) | ((device >> 12) & 0xffffff00)
    return major, minor, inode


def reader_evidence(root, expected, loads):
    stages = {'wrong-pin': 'library-hash', 'wrong-starttime': 'process-identity',
              'unmapped-range': 'target-ranges'}
    for mode, stage in stages.items():
        directory = root / 'reader' / mode
        manifest = tomllib.loads((directory / 'manifest.toml').read_text())
        command = tomllib.loads((directory / 'command.toml').read_text())
        require(command['mode'] == mode and command['returncode'] == 3, 'Negative command did not reject')
        require(manifest['schema_version'] == 'mho900-lab.cached-identity-reader/1'
                and manifest['mode'] == mode and manifest['result'] == 'rejected'
                and manifest['stage'] == stage and manifest['pid'] == expected['expected_pid'],
                'Negative reader stopped at unexpected boundary')
        require(manifest['mem_open_count'] == manifest['memory_read_calls'] == manifest['bytes_read'] == 0,
                'Negative control opened or read process memory')
        require(manifest['read_results'] == manifest['read_requested'] == []
                and manifest['memory_bytes_requested'] == 0 and manifest['maximum_memory_bytes'] == 48
                and manifest['sample_count'] == 0
                and not any(directory.glob('sample-*')), 'Negative control retained memory data')
        require(manifest['expected_library_sha256'] == ('0' * 64 if mode == 'wrong-pin' else STOCK_SHA256)
                and number(manifest['validation_dna_virtual_address']) == (0 if mode == 'unmapped-range' else RANGES[0][0]),
                'Negative control intervention differs')
        require(number(manifest['expected_starttime']) == number(expected['expected_starttime'])
                + (1 if mode == 'wrong-starttime' else 0)
                and number(manifest['observed_starttime_before']) == number(expected['expected_starttime'])
                and manifest['expected_boot_id'] == expected['expected_boot_id'], 'Negative identity control differs')
        require(proc_identity((directory / 'stat-before.txt').read_text())
                == (expected['expected_pid'], number(expected['expected_starttime'])), 'Negative raw identity differs')
        if mode != 'wrong-starttime':
            require(manifest['library_sha256'] == STOCK_SHA256, 'Negative control backing file pin differs')
        require(not (directory / 'sample-1.bin').exists() and not (directory / 'sample-2.bin').exists(),
                'Negative control created process samples')
    directory = root / 'reader/positive'
    manifest = tomllib.loads((directory / 'manifest.toml').read_text())
    command = tomllib.loads((directory / 'command.toml').read_text())
    require(command['mode'] == 'positive' and command['returncode'] == 0, 'Positive command failed')
    require(manifest['schema_version'] == 'mho900-lab.cached-identity-reader/1'
            and manifest['mode'] == 'positive' and manifest['result'] == 'accepted'
            and manifest['stage'] == 'complete' and manifest['error_number'] == 0
            and manifest['pid'] == expected['expected_pid'],
            'Positive reader contract differs')
    require(manifest['library_sha256'] == STOCK_SHA256, 'Reader did not pin stock library bytes')
    require(manifest['expected_library_sha256'] == STOCK_SHA256
            and number(manifest['validation_dna_virtual_address']) == RANGES[0][0], 'Positive request differs')
    require(manifest['library_path'] == expected['module_path']
            and manifest['dna_size'] == 8 and manifest['file_keys_size'] == 16
            and all(manifest[field] is False for field in ('target_attached', 'target_calls', 'target_writes')),
            'Reader exceeded observation contract')
    require(number(manifest['expected_starttime']) == number(expected['expected_starttime'])
            and manifest['expected_boot_id'] == expected['expected_boot_id'], 'Reader expected identity differs')
    for suffix in ('before', 'after'):
        require(number(manifest['observed_starttime_' + suffix]) == number(expected['expected_starttime'])
                and manifest['boot_id_' + suffix] == expected['expected_boot_id'], 'Reader observed identity differs')
    metadata = ('device', 'inode', 'mode', 'size', 'mtime', 'mtime_nsec', 'ctime', 'ctime_nsec')
    for field in metadata:
        require(manifest['library_' + field + '_before'] == manifest['library_' + field + '_after'],
                'Backing file metadata changed: ' + field)
    require(number(manifest['library_mode_before']) & 0o170000 == 0o100000,
            'Library backing is not a regular file')
    require(number(manifest['library_size_before']) == (root / 'fixture/lib/libscope-auklet.so').stat().st_size,
            'Library backing size differs')
    identity = device_identity(number(manifest['library_device_before']), number(manifest['library_inode_before']))
    raw_maps = []
    for moment in ('before', 'armed', 'between', 'after'):
        raw_maps.append((directory / ('maps-' + moment + '.txt')).read_bytes())
        require(proc_identity((directory / ('stat-' + moment + '.txt')).read_text())
                == (expected['expected_pid'], number(expected['expected_starttime'])), 'Raw process identity changed')
        require((directory / ('boot-' + moment + '.txt')).read_text().strip() == expected['expected_boot_id'],
                'Raw boot identity changed')
    raw_maps += [(root / 'reader' / moment / 'maps.txt').read_bytes()
                 for moment in ('after-setup', 'after-read')]
    require(manifest['full_maps_changed'] == any(raw != raw_maps[0] for raw in raw_maps[1:4]),
            'Reader full-maps comparison differs from retained raw evidence')
    parsed_maps = [maps_rows(data.decode()) for data in raw_maps]
    resolved = [resolve(loads, rows, expected['module_path'], identity) for rows in parsed_maps]
    require(all(item == resolved[0] for item in resolved), 'Cached range addresses changed')
    relevant = [[row for row in rows if row['path'] == expected['module_path']
                 or (row['major'], row['minor'], row['inode']) == identity] for rows in parsed_maps]
    require(all(rows == relevant[0] for rows in relevant), 'Verified library mappings changed')
    bias, addresses = resolved[0]
    require(bias == number(expected['module_base']) == number(manifest['load_bias'])
            and addresses == [number(manifest['dna_address']), number(manifest['file_keys_address'])],
            'Independent address resolution differs from helper or prior setup witness')
    require(manifest['mem_open_count'] == 1 and manifest['mem_open_flags'] == 0
            and manifest['memory_read_calls'] == 4 and manifest['memory_bytes_requested'] == 48
            and manifest['maximum_memory_bytes'] == 48
            and manifest['bytes_read'] == 48 and manifest['sample_count'] == 2
            and manifest['read_requested'] == manifest['read_results'] == [8, 16, 8, 16],
            'Reader exceeded or did not complete fixed positioned reads')
    require(all(manifest[key] is True for key in ('repeat_equal', 'identity_stable', 'maps_stable', 'file_stable')),
            'Reader stability checks failed')
    samples = [(directory / ('sample-' + str(index) + '.bin')).read_bytes() for index in (1, 2)]
    require(samples[0] == samples[1] == bytes.fromhex(expected['expected_sample_hex']) and len(samples[0]) == 24,
            'Retained samples differ from each other or prior setup witness')
    require(all(sha(data) == manifest['sample_' + str(index) + '_sha256'] for index, data in enumerate(samples, 1)),
            'Sample hashes differ from actual bytes')
    return {'independent_load_bias': hex(bias), 'dna_address': hex(addresses[0]),
            'file_keys_address': hex(addresses[1]), 'sample_sha256': sha(samples[0]),
            'total_process_bytes_read': 48, 'process_memory_reads': 4, 'negative_controls': 3,
            'repeated_samples_equal': True, 'atomic_snapshot_claimed': False,
            'target_library_maps_stable': True,
            'unrelated_maps_changed': any(raw != raw_maps[0] for raw in raw_maps)}


def verify(root, config):
    data = (root / 'fixture/lib/libscope-auklet.so').read_bytes()
    loads = elf_loads(data)
    require(config['schema_version'] == 'mho900-lab.cached-identity-reader-inputs/1'
            and config['library_sha256'] == STOCK_SHA256 and config['library_size'] == len(data)
            and config['elf_class'] == 64 and config['elf_machine'] == 183 and config['elf_type'] == 3
            and config['page_size'] == PAGE and config['sample_bytes'] == 24 and config['samples'] == 2
            and config['maximum_memory_bytes'] == 48, 'Frozen input contract differs')
    require(tuple((item['flags'], item['file_offset'], item['virtual_address'], item['file_size'], item['memory_size'])
                  for item in config['loads']) == LOADS
            and tuple((item['virtual_address'], item['size'], item['file_offset']) for item in config['ranges']) == RANGES,
            'Frozen ELF/range geometry differs')
    require([item['symbol'] for item in config['ranges']] == ['_ZN11CApiUtility5m_DNAE', 'fileKeys']
            and config['negative_controls'] == {'modes': ['wrong-pin', 'wrong-starttime', 'unmapped-range'],
                                                'exit_code': 3, 'memory_read_calls': 0, 'bytes_read': 0,
                                                'mem_open_count': 0}, 'Frozen controls differ')
    controls = host_controls(data)
    ready, expected, journal, host = setup_evidence(root)
    policy = boundary_evidence(root, expected)
    comparison = one(host, 'setup-policy-comparison')
    summary = one(host, 'controller-result')
    require(comparison['setup_policy_changed'] == policy['setup_policy_changed']
            and comparison['enforcement_unchanged'] is True and comparison['boot_unchanged'] is True
            and summary['setup_policy_observed'] is True
            and summary['setup_policy_changed'] == policy['setup_policy_changed'], 'Setup policy summary differs')
    readings = reader_evidence(root, expected, loads)
    reader = (root / 'cached-identity-reader').read_bytes()
    require(reader == (root / 'guest-cached-identity-reader').read_bytes(), 'Staged reader differs from host binary')
    build = tomllib.loads((root / 'source/reader-build.toml').read_text())
    require(build['schema_version'] == 'mho900-lab.cached-identity-reader-build/1'
            and build['binary_sha256'] == sha(reader)
            and build['source_sha256'] == sha((root / 'source/read-cached-identity.c').read_bytes())
            and build['builder_sha256'] == sha((root / 'source/build-cached-identity-reader.sh').read_bytes())
            and build['inputs_sha256'] == sha((root / 'source/reader-inputs.toml').read_bytes())
            and build['compiler_sha256'] == config['compiler_sha256']
            and build['linker_sha256'] == config['linker_sha256']
            and build['target'] == 'aarch64-linux-gnu' and build['static'] is True and build['libc'] is False,
            'Reader build provenance differs')
    return {'schema_version': 'mho900-lab.cached-identity-verification/1', 'verification': 'accepted',
            'stock_native_sha256': sha(data), 'reader_sha256': sha(reader), **policy,
            'setup_journal_records': len(journal), 'setup_delivery_complete': True,
            'setup_detached_before_reader': True, 'host_addressing_controls': controls['host_controls'],
            **readings, 'physical_contact': False, 'physical_permission_established': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path, nargs='?')
    parser.add_argument('config', type=Path, nargs='?')
    parser.add_argument('--self-test', type=Path, metavar='PINNED_ELF')
    parser.add_argument('--reader-source', type=Path, help='Also compile and test the reader pure helpers on the host')
    args = parser.parse_args()
    if args.self_test is not None:
        require(args.run_dir is None and args.config is None, 'Self-test takes only pinned ELF')
        result = host_controls(args.self_test.read_bytes(), args.reader_source)
    else:
        require(args.reader_source is None, 'Reader source controls require --self-test')
        require(args.run_dir is not None and args.config is not None, 'Pass run directory and frozen inputs')
        result = verify(args.run_dir, tomllib.loads(args.config.read_text()))
    for key, value in result.items():
        print(key + ' = ' + json.dumps(value))


if __name__ == '__main__':
    main()
