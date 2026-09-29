#!/usr/bin/env python3
"""Offline original-instruction controls for the license consumer's string/key span.

Python is used for Unicorn. All key strings are synthetic; this neither creates
option tokens nor contacts a guest or instrument. The string object is a declared
libc++ layout fixture, not a claim that constructors were executed.
"""
import argparse
import importlib.util
from pathlib import Path
import struct
import traceback
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm64_const import UC_ARM64_REG_X2

spec = importlib.util.spec_from_file_location('coherence', Path(__file__).with_name('physical-identity-coherence.py'))
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    result = dict(schema_version=1, result='failed', physical_access=False,
                  synthetic_only=True, error='')
    try:
        blob = a.library.read_bytes()
        core.ALLOWED = [(0x2356d8, 0x235718), (0x2357d0, 0x235808),
                        (0x235978, 0x235a9c), (0x3e9d24, 0x3ea76c),
                        (0x202cf0, 0x202d00)]
        cpu = core.Stock(blob)
        # Stock R_AARCH64_JUMP_SLOT for AES_set_encrypt_key; no code patch.
        cpu.u.mem_write(core.BASE + 0xb7dd50, struct.pack('<Q', core.BASE + 0x3e9d24))
        key = core.DATA + 0x1000
        schedule = core.DATA + 0x2000
        reads = []

        def read(uc, access, address, size, value, user):
            if key <= address < key + 0x1000:
                reads.append((address-key, size))
        cpu.u.hook_add(UC_HOOK_MEM_READ, read)

        # Inline short-string data pointer, then long-string pointer/length.
        cpu.u.mem_write(core.DATA, bytes([6]) + b'abc\0' + bytes(19))
        assert cpu.call(0x235978, core.DATA) == core.DATA + 1
        prefix = b'0123456789abcdef' * 2
        fields = [prefix, prefix + b'a'*98, prefix + b'b'*98,
                  b'X' + prefix[1:] + b'a'*98]
        schedules = []
        spans = []
        for field in fields:
            cpu.u.mem_write(key, field + b'\0')
            cpu.u.mem_write(core.DATA, struct.pack('<3Q', 0x201, len(field), key))
            pointer = cpu.call(0x235978, core.DATA)
            assert pointer == key
            cpu.u.mem_write(schedule, bytes(244))
            cpu.u.reg_write(UC_ARM64_REG_X2, schedule)
            reads.clear()
            assert cpu.call(0x3ea328, pointer, 256) == 0
            covered = sorted({i for off, size in reads for i in range(off, off+size)})
            assert covered == list(range(32)), 'unexpected input key span'
            spans.append(reads.copy())
            schedules.append(bytes(cpu.u.mem_read(schedule, 244)))
        assert schedules[0] == schedules[1] == schedules[2]
        assert schedules[3] != schedules[1]
        assert struct.unpack('<I', schedules[0][-4:])[0] == 14
        # Stock errors, not exercised by the fixed-width ordinary consumer.
        cpu.u.reg_write(UC_ARM64_REG_X2, schedule)
        assert cpu.call(0x3ea328, 0, 256) & 0xffffffff == 0xffffffff
        cpu.u.reg_write(UC_ARM64_REG_X2, schedule)
        assert cpu.call(0x3ea328, key, 130) & 0xffffffff == 0xfffffffe
        core.write_toml(a.output/'controls.toml', dict(field_lengths=list(map(len, fields)),
            schedule_sha256=[core.sha(x) for x in schedules], key_read_spans=spans,
            same_prefix_same_schedule=True, changed_prefix_changes_schedule=True,
            short_pointer=True, long_pointer=True, rounds=14,
            null_key_result=-1, unsupported_width_result=-2))
        (a.output/'instruction-trace.txt').write_text(''.join(hex(x)+'\n' for x in cpu.trace))
        core.write_toml(a.output/'inputs.toml', dict(library_sha256=core.sha(blob),
            source_sha256=core.sha(Path(__file__).read_bytes()),
            loader_sha256=core.sha(Path(core.__file__).read_bytes()),
            unicorn_version=core.unicorn.__version__, string_layout_modeled=True,
            original_instructions=True, os_services=False))
        result.update(result='accepted', key_bytes_read=32, field_controls=4,
                      pointer_controls=2, error_controls=2)
    except BaseException as exc:
        result['error'] = str(exc)
        (a.output/'failure.txt').write_text(traceback.format_exc())
    core.write_toml(a.output/'result.toml', result)
    print((a.output/'result.toml').read_text())
    return 0 if result['result'] == 'accepted' else 1


if __name__ == '__main__':
    raise SystemExit(main())
