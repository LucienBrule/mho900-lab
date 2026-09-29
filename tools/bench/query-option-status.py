#!/usr/bin/env python3
"""One bounded documented SCPI identity/status sequence on an existing socket."""
import os
from pathlib import Path
import time

SELECTORS = ('BND', 'AFG100', 'AFG50', 'AUDio', 'CAN-FD', 'FLEX', 'AERO',
             'RLU-05', 'BWU03T05', 'BWU03T08', 'BWU05T08')
REQUESTS = (b'*IDN?\n',) + tuple((':SYSTem:OPTion:STATus? ' + s + '\n').encode('ascii') for s in SELECTORS)


def query(sock, output, expected_identity, health):
    output = Path(output)
    assert output.is_dir() and not any(output.iterdir())
    statuses = {}
    sock.setblocking(False)
    for index, request in enumerate(REQUESTS):
        health()
        # Tiny requests; nonblocking partial sends are handled without repeating bytes.
        (output / f'{index:02d}-request.bin').write_bytes(request)
        offset = 0
        deadline = time.monotonic() + 10
        while offset < len(request):
            health()
            if time.monotonic() > deadline:
                raise TimeoutError('SCPI send deadline')
            try:
                sent = sock.send(request[offset:])
            except BlockingIOError:
                time.sleep(.02)
                continue
            if sent == 0:
                raise RuntimeError('SCPI connection closed during request')
            offset += sent
        data = b''
        with (output / f'{index:02d}-response.bin').open('xb') as stream:
            while b'\n' not in data:
                health()
                if time.monotonic() > deadline:
                    raise TimeoutError('SCPI response deadline')
                try:
                    chunk = sock.recv(4096 - len(data))
                except BlockingIOError:
                    time.sleep(.02)
                    continue
                if not chunk:
                    raise RuntimeError('SCPI connection closed before response terminator')
                data += chunk
                stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
                if len(data) >= 4096:
                    raise ValueError('SCPI response too large')
        if data.count(b'\n') != 1 or not data.endswith(b'\n'):
            raise ValueError('Unexpected extra SCPI response bytes')
        if index == 0:
            if data.strip() != expected_identity.strip():
                raise ValueError('Specimen identity differs')
        else:
            if data.strip() not in (b'0', b'1'):
                raise ValueError('Option status outside documented boolean format')
            statuses[SELECTORS[index - 1]] = int(data.strip())
    health()
    return statuses
