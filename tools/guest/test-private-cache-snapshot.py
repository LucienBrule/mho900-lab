#!/usr/bin/env python3
"""Offline controls; optional stock-produced stream remains private."""
import argparse
import hashlib
from pathlib import Path
import struct
from private_cache_snapshot import Region, observe, private_stream, PRIVATE_WINDOW, MAX_READ_BYTES

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--stock-stream', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
stream = a.stock_stream.read_bytes()
window = stream + bytes(PRIVATE_WINDOW-len(stream))
parsed, records = private_stream(window)
assert parsed == stream and records == ((2337, 148), (16192, 8))
H, W, R = 0x10000, 0x20000, 0x30000
header = struct.pack('<iiiIQQ', 7, 0x50, 8192, 0, W, R)
regions = [Region(H, H+4096), Region(W, W+8192), Region(R, R+8192)]
passed = []

def run(name, edit=None, expected=None):
    memory = {H: header, W+0x100: window, R+0x100: window}
    maps = list(regions)
    calls = []
    mutator = None
    if edit:
        result = edit(memory, maps)
        if result:
            mutator = result
    def read(address, size):
        calls.append((address, size))
        result = memory[address]
        if mutator:
            result = mutator(len(calls), address, result)
        return result
    try:
        result = observe(read, maps, H)
    except ValueError as error:
        assert expected is not None and str(error) == expected, (name, str(error), expected)
    else:
        assert expected is None, name
        assert result['bytes_read'] == MAX_READ_BYTES == sum(n for _, n in calls)
        assert not result['atomic_snapshot'] and not result['device_readback']
        if name == 'stable-divergent-padding':
            assert not result['private_windows_equal'] and result['private_streams_equal']
        if name == 'stable-divergent-record':
            assert not result['private_streams_equal']
    assert sum(n for _, n in calls) <= MAX_READ_BYTES
    passed.append(name)

def change_header(offset, fmt, value):
    def edit(memory, maps):
        b = bytearray(memory[H]); struct.pack_into(fmt, b, offset, value); memory[H] = bytes(b)
    return edit

def change_window(offset, fmt, value):
    def edit(memory, maps):
        b = bytearray(memory[W+0x100]); struct.pack_into(fmt, b, offset, value); memory[W+0x100] = bytes(b)
    return edit

run('equal-stock-streams')
run('stable-divergent-padding', change_window(PRIVATE_WINDOW-1, '<B', 1))
# Another independently retained stock-produced stream is not required: use the
# canonical empty MemFile framing as a valid, deliberately different reference.
run('stable-divergent-record', lambda m,r: m.update({R+0x100: struct.pack('<II',8,(-8)&0xffffffff)+bytes(PRIVATE_WINDOW-8)}))
run('negative-fd', change_header(0,'<i',-1), 'unexpected CFram metadata')
run('wrong-device-address', change_header(4,'<i',0x51), 'unexpected CFram metadata')
run('wrong-capacity', change_header(8,'<i',4096), 'unexpected CFram metadata')
run('null-working', change_header(16,'<Q',0), 'address bounds')
run('unaligned-working', change_header(16,'<Q',W+1), 'unaligned cache')
run('aliased-caches', change_header(24,'<Q',W), 'cache overlap')
run('unmapped-cache', change_header(16,'<Q',0x40000), 'unmapped or crossing range')
run('short-map', lambda m,r:r.__setitem__(1,Region(W,W+4096)), 'unmapped or crossing range')
run('device-mapping', lambda m,r:r.__setitem__(1,Region(W,W+8192,'rw-s','/dev/example')), 'not private anonymous readable memory')
run('nonreadable-map', lambda m,r:r.__setitem__(1,Region(W,W+8192,'---p')), 'not private anonymous readable memory')
run('overlapping-maps', lambda m,r:r.append(Region(W,W+8192)), 'overlapping maps')
run('short-read', lambda m,r:(lambda n,addr,b:b[:-1] if n==2 else b), 'short or invalid read')
run('header-changed', lambda m,r:(lambda n,addr,b:bytes(32) if n==4 else b), 'CFram changed during sample')
run('second-sample-changed', lambda m,r:(lambda n,addr,b:b[:-1]+b'\x01' if n==6 else b), 'samples changed')
run('wrong-total-complement', change_window(4,'<I',0), 'stream header')
run('oversized-total', change_window(0,'<I',PRIVATE_WINDOW), 'stream header')
run('wrong-id-complement', change_window(12,'<I',0), 'record ID complement')
run('wrong-length-complement', change_window(20,'<I',0), 'record length')
run('crc-damage', change_window(24,'<I',0), 'record CRC')
def duplicate(m,r):
    b=bytearray(m[W+0x100]); second=8+20+148
    struct.pack_into('<II',b,second,2337,(-2337)&0xffffffff);m[W+0x100]=bytes(b)
run('duplicate-record',duplicate,'duplicate record ID')
def truncated(m,r):
    b=bytearray(m[W+0x100]);struct.pack_into('<II',b,0,16,(-16)&0xffffffff);m[W+0x100]=bytes(b)
run('truncated-record',truncated,'truncated record header')
text=['schema_version = "mho900-lab.private-cache-controls/1"',f'controls_passed = {len(passed)}',
      f'stock_stream_sha256 = "{hashlib.sha256(stream).hexdigest()}"',
      f'positive_read_budget = {MAX_READ_BYTES}', 'physical_contact = false', 'guest_execution = false',
      'live_owner_resolution_validated = false', 'device_readback = false']
for name in passed:text+=['','[[controls]]',f'name = "{name}"','passed = true']
a.output.write_text('\n'.join(text)+'\n')
print(f'{len(passed)} offline controls passed; stock stream preserved; {MAX_READ_BYTES}-byte positive budget')
