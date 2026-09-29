"""Offline-tested CFram private-window observer core; no process or device I/O.

The caller must independently establish the stock owner and process epoch.
This module deliberately supplies no way to discover or contact a process.
"""
from dataclasses import dataclass
import struct
import zlib

CACHE_SIZE = 8192
PRIVATE_OFFSET = 0x100
PRIVATE_WINDOW = 0x700
MAX_READ_BYTES = 2 * (32 + 2 * PRIVATE_WINDOW + 32)

@dataclass(frozen=True)
class Region:
    start: int
    end: int
    permissions: str = 'rw-p'
    name: str = ''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def private_stream(window):
    """Validate a bounded private region; return exact stream and metadata only."""
    require(len(window) == PRIVATE_WINDOW, 'private window size')
    total, inverse = struct.unpack_from('<II', window)
    require(8 <= total < PRIVATE_WINDOW and (total + inverse) & 0xffffffff == 0,
            'stream header')
    cursor, records, seen = 8, [], set()
    while cursor < total:
        require(cursor + 20 <= total, 'truncated record header')
        ident, inverse_id, length, inverse_length, crc = struct.unpack_from('<5I', window, cursor)
        require((ident + inverse_id) & 0xffffffff == 0, 'record ID complement')
        require(ident not in seen, 'duplicate record ID')
        require(0 < length < PRIVATE_WINDOW and (length + inverse_length) & 0xffffffff == 0,
                'record length')
        require(cursor + 20 + length <= total, 'record exceeds stream')
        payload = window[cursor+20:cursor+20+length]
        require(zlib.crc32(payload) == crc, 'record CRC')
        seen.add(ident)
        records.append((ident, length))
        cursor += 20 + length
    require(cursor == total, 'stream end')
    return window[:total], tuple(records)


def observe(read, regions, fram_address):
    """Two matching, bounded observations, not an atomic snapshot or device image.

    read(address, size) must return exactly that many bytes or raise. Regions
    must be independently obtained and checked for the same process epoch.
    Differing *working vs reference* windows are retained, not hidden/repaired.
    """
    regions = tuple(regions)
    for i, region in enumerate(regions):
        require(0 < region.start < region.end <= 1 << 48, 'mapping bounds')
        for other in regions[:i]:
            require(region.end <= other.start or other.end <= region.start, 'overlapping maps')
    budget = 0

    def allowed(address, size):
        require(isinstance(address, int) and address > 0 and size > 0 and address+size <= 1 << 48,
                'address bounds')
        matching = [r for r in regions if r.start <= address and address+size <= r.end]
        require(len(matching) == 1, 'unmapped or crossing range')
        region = matching[0]
        require(region.permissions == 'rw-p' and
                (region.name in ('', '[heap]') or
                 (region.name.startswith('[anon:') and region.name.endswith(']'))),
                'not private anonymous readable memory')

    def bounded_read(address, size):
        nonlocal budget
        allowed(address, size)
        require(budget+size <= MAX_READ_BYTES, 'read budget')
        budget += size
        value = read(address, size)
        require(isinstance(value, bytes) and len(value) == size, 'short or invalid read')
        return value

    def once():
        require(fram_address % 8 == 0, 'unaligned CFram')
        header = bounded_read(fram_address, 32)
        fd, address, size = struct.unpack_from('<iii', header)
        working, reference = struct.unpack_from('<QQ', header, 16)
        require(fd >= 0 and address == 0x50 and size == CACHE_SIZE, 'unexpected CFram metadata')
        require(working % 8 == 0 and reference % 8 == 0, 'unaligned cache')
        allowed(working, CACHE_SIZE)
        allowed(reference, CACHE_SIZE)
        require(working+CACHE_SIZE <= reference or reference+CACHE_SIZE <= working, 'cache overlap')
        require(all(fram_address+32 <= p or p+CACHE_SIZE <= fram_address
                    for p in (working, reference)), 'header/cache overlap')
        w = bounded_read(working+PRIVATE_OFFSET, PRIVATE_WINDOW)
        r = bounded_read(reference+PRIVATE_OFFSET, PRIVATE_WINDOW)
        require(bounded_read(fram_address, 32) == header, 'CFram changed during sample')
        ws, wr = private_stream(w)
        rs, rr = private_stream(r)
        return header, w, r, ws, rs, wr, rr

    first, second = once(), once()
    require(first == second, 'samples changed')
    return {
        'header': first[0], 'working_window': first[1], 'reference_window': first[2],
        'working_stream': first[3], 'reference_stream': first[4],
        'working_records': first[5], 'reference_records': first[6],
        'private_windows_equal': first[1] == first[2],
        'private_streams_equal': first[3] == first[4],
        'bytes_read': budget, 'atomic_snapshot': False, 'device_readback': False,
    }
