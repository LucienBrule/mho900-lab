#!/usr/bin/env python3
"""Verify retained ARM64 private-storage instruction words against pinned stock ELF."""
import argparse
import hashlib
import re
import struct
from pathlib import Path

PIN = '4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf', type=Path, required=True)
    p.add_argument('--assembly', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    data = a.elf.read_bytes()
    if hashlib.sha256(data).hexdigest() != PIN or data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Stock ELF identity mismatch')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    phsize, phnum = struct.unpack_from('<HH', data, 54)
    segments = []
    for n in range(phnum):
        typ, flags, off, va, _, filesz, _, _ = struct.unpack_from('<IIQQQQQQ', data, phoff+n*phsize)
        if typ == 1:
            segments.append((va, off, filesz))
    words = {}
    for line in a.assembly.read_text().splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+', line)
        if not m:
            continue
        va, word = int(m[1], 16), int(m[2], 16).to_bytes(4, 'little')
        mapped = [off+va-base for base, off, size in segments if base <= va and va+4 <= base+size]
        if len(mapped) != 1 or data[mapped[0]:mapped[0]+4] != word:
            raise ValueError(f'Instruction mismatch at {va:x}')
        if va in words and words[va] != word:
            raise ValueError('Conflicting duplicate instruction')
        words[va] = word
    if len(words) < 1000:
        raise ValueError('Unexpectedly incomplete private-storage assembly')
    a.output.write_text('\n'.join([
        'schema_version = "mho900-lab.private-storage-assembly/1"',
        f'stock_native_sha256 = "{PIN}"',
        f'assembly_sha256 = "{hashlib.sha256(a.assembly.read_bytes()).hexdigest()}"',
        f'unique_instruction_words_checked = {len(words)}',
        'instruction_bytes_match = true',
        'interpretation_independently_proven = false',
        'physical_contact = false',
        '',
    ]))
    print(f'Verified {len(words)} stock instruction words')

if __name__ == '__main__':
    main()
