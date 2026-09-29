#!/usr/bin/env python3
"""One ordinary install and bounded status observation on a caller-owned socket.

The caller binds source, validates specimen/baseline, and owns capture and socket
cleanup. An unsuccessful return never authorizes retransmission. A status of1
is only an observation; saved-license and unrelated-state checks remain external.
"""
import hashlib
import json
import os
from pathlib import Path
import time

SELECTORS = ('AFG100', 'AFG50', 'AUDio', 'CAN-FD', 'FLEX', 'AERO',
             'RLU-05', 'BWU03T05', 'BWU03T08', 'BWU05T08')
MAX_POLLS = 5
DEADLINE_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 2.0
MAX_RESPONSE_BYTES = 64

class InstallUncertain(RuntimeError):
    """No retransmission: request effects may exist despite missing evidence."""
    def __init__(self, result):
        self.result = result
        super().__init__('Ordinary install outcome uncertain: ' + result['failure_type'])

def _save(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def install(sock, output, request, request_sha256, selector, health):
    """Transmit one exact request, then at most5 documented STATus? queries.

    Nonblocking partial sends advance only by the count accepted by send().
    A send exception is terminal even if its transmission extent is unknown.
    First poll is immediate; subsequent polls start at least2 seconds apart.
    Each response has at most2 seconds, within the shared10-second deadline.
    No install response is expected or read separately. Any extra/malformed
    status bytes terminate observation, leaving the caller to preserve state.
    """
    output = Path(output)
    if not output.is_dir() or any(output.iterdir()):
        raise ValueError('Output must be an existing empty directory')
    if selector not in SELECTORS:
        raise ValueError('Selector outside ordinary-option allowlist')
    if not isinstance(request, bytes) or not 1 <= len(request) <= 4096:
        raise ValueError('Invalid request extent')
    prefix = b':SYSTem:OPTion:INSTall '
    if not request.startswith(prefix) or not request.endswith(b'\n'):
        raise ValueError('Expected exact documented install framing')
    token = request[len(prefix):-1]
    if not token or any(c < 33 or c > 126 or c == 59 for c in token):
        raise ValueError('Expected one opaque ASCII token and one terminator')
    digest = hashlib.sha256(request).hexdigest()
    if digest != request_sha256:
        raise ValueError('Request digest mismatch')
    result = dict(schema_version=1, observed=False, status='not-started',
                  polls=0, install_bytes_sent=0, request_sha256=digest,
                  selector=selector, automatic_retransmissions=0,
                  maximum_polls=MAX_POLLS, deadline_seconds=10,
                  failure_type='')
    events = output / 'send-events.toml'
    def record(kind, offset, sent):
        with events.open('a') as stream:
            stream.write('\n[[sends]]\nkind = '+json.dumps(kind)+'\noffset = '+str(offset)+'\naccepted = '+str(sent)+'\n')
            stream.flush(); os.fsync(stream.fileno())
    def check(deadline):
        health()
        if time.monotonic() >= deadline:
            raise TimeoutError('Bounded install/status deadline')
    def send(data, kind, deadline):
        offset = 0
        while offset < len(data):
            check(deadline)
            try:
                sent = sock.send(data[offset:])
            except BlockingIOError:
                time.sleep(.02)
                continue
            if not isinstance(sent, int) or not 0 < sent <= len(data)-offset:
                raise ConnectionError('Invalid or closed send result')
            previous = offset
            offset += sent
            if kind == 'install':
                result['install_bytes_sent'] = offset
            record(kind, previous, sent)
    try:
        health()
        _save(output / 'install-request.bin', request)
        sock.setblocking(False)
        start = time.monotonic()
        deadline = start + DEADLINE_SECONDS
        result['status'] = 'sending'
        send(request, 'install', deadline)
        result['status'] = 'awaiting-status'
        next_poll = time.monotonic()
        for index in range(MAX_POLLS):
            while time.monotonic() < next_poll:
                check(deadline)
                time.sleep(max(0., min(.02, next_poll-time.monotonic())))
            check(deadline)
            poll_start = time.monotonic()
            query = (':SYSTem:OPTion:STATus? '+selector+'\n').encode('ascii')
            _save(output / f'{index:02d}-request.bin', query)
            result['polls'] += 1
            poll_deadline = min(deadline, poll_start+2)
            send(query, 'status-'+str(index), poll_deadline)
            data = b''
            with (output / f'{index:02d}-response.bin').open('xb') as stream:
                while b'\n' not in data:
                    check(poll_deadline)
                    try:
                        chunk = sock.recv(MAX_RESPONSE_BYTES-len(data))
                    except BlockingIOError:
                        time.sleep(.02)
                        continue
                    if not chunk:
                        raise ConnectionError('Status connection closed')
                    data += chunk
                    stream.write(chunk); stream.flush(); os.fsync(stream.fileno())
                    if len(data) >= MAX_RESPONSE_BYTES:
                        raise ValueError('Status response limit')
            if data not in (b'0\n', b'1\n', b'0\r\n', b'1\r\n'):
                raise ValueError('Malformed or extra status bytes')
            if data.startswith(b'1'):
                result.update(observed=True, status='observed')
                break
            next_poll = poll_start + POLL_INTERVAL_SECONDS
        else:
            result['status'] = 'not-observed'
        health()
    except BaseException as error:
        result.update(status='uncertain', failure_type=type(error).__name__)
        _save(output / 'result.toml', ''.join(k+' = '+json.dumps(v)+'\n' for k,v in result.items()).encode())
        raise InstallUncertain(result) from error
    _save(output / 'result.toml', ''.join(k+' = '+json.dumps(v)+'\n' for k,v in result.items()).encode())
    return result
