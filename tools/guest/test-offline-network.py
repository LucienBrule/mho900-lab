#!/usr/bin/env python3
"""Host-only child sandbox control; every test address is IPv4 loopback."""
import errno
import os
from pathlib import Path
import socket
import subprocess
import sys


def child(allowed_port, denied_port):
    # Detach a grandchild to exercise inherited restrictions after daemon-like fork.
    if os.fork():
        _, status = os.wait()
        return os.waitstatus_to_exitcode(status)
    os.setsid()
    try:
        with socket.create_connection(("127.0.0.1", allowed_port), timeout=3) as stream:
            stream.sendall(b"inherited-loopback-ok")
        for family, kind, address in (
            (socket.AF_INET, socket.SOCK_STREAM, ("127.0.0.2", denied_port)),
            (socket.AF_INET, socket.SOCK_DGRAM, ("127.0.0.2", denied_port)),
        ):
            with socket.socket(family, kind) as stream:
                stream.settimeout(3)
                try:
                    if kind == socket.SOCK_STREAM:
                        stream.connect(address)
                    else:
                        stream.sendto(b"must-not-leave-child", address)
                except OSError as error:
                    if error.errno not in (errno.EPERM, errno.EACCES):
                        raise RuntimeError(f"Expected policy denial, got {error!r}")
                else:
                    raise RuntimeError("Disallowed loopback alias was reachable")
        os._exit(0)
    except BaseException:
        import traceback
        traceback.print_exc()
        os._exit(1)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        return child(int(sys.argv[2]), int(sys.argv[3]))
    profile = Path(sys.argv[1] if len(sys.argv) > 1 else __file__).resolve()
    if len(sys.argv) == 1:
        profile = profile.with_name("offline-loopback.sb")
    with socket.socket() as allowed:
        allowed.bind(("127.0.0.1", 0))
        allowed.listen(1)
        allowed.settimeout(5)
        command = ["/usr/bin/sandbox-exec", "-f", str(profile), sys.executable,
                   str(Path(__file__).resolve()), "child", str(allowed.getsockname()[1]),
                   str(allowed.getsockname()[1])]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with allowed.accept()[0] as stream:
                stream.settimeout(3)
                assert stream.recv(128) == b"inherited-loopback-ok"
            stdout, stderr = process.communicate(timeout=8)
            assert process.returncode == 0, stderr.decode(errors="replace")
        except BaseException:
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=3)
            sys.stderr.write(stderr.decode(errors="replace"))
            raise
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    print('schema_version = "mho900-lab.offline-network-control/1"')
    print('result = "pass"')
    print('allowed_loopback_tcp = true')
    print('denied_other_loopback_tcp = true')
    print('denied_other_loopback_udp = true')
    print('fork_setsid_inheritance = true')
    print('external_destination_contacted = false')
    return 0


if __name__ == "__main__":
    sys.exit(main())
