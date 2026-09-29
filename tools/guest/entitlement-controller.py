#!/usr/bin/env python3
"""Frida-native protocol boundary for a bounded disposable Android component run.

Frida's maintained Python API supplies spawn/attach/detach; no ADB or network
device discovery is performed here. The parent confines this process to loopback.
Messages are preserved as Frida protocol JSONL, not public result manifests.
"""
import datetime
import json
import os
import pathlib
import sys
import stat
import threading

import frida


STOCK_STOPS = {"runtime-dna-unavailable", "private-fram-unavailable", "unexpected-pcie-init"}


def accepted_stop(payload):
    if payload.get("kind") != "dependency-stop":
        return False
    if payload.get("reason") in STOCK_STOPS:
        return payload.get("exit_code") == 77
    if payload.get("reason") != "fault-control-confirmed":
        return False
    try:
        expected = int(payload.get("expected_pc", ""), 16)
        observed = int(payload.get("observed_pc", ""), 16)
    except (ValueError, TypeError):
        return False
    return (payload.get("stage") == "private-arm64-null-read"
            and payload.get("context_verified") is True
            and expected != 0 and expected == observed
            and payload.get("memory_address") == "0x0"
            and payload.get("memory_operation") == "read"
            and payload.get("exit_code") == 77)


def main():
    assert len(sys.argv) == 2, "Pass one frozen Frida JavaScript source"
    endpoint = os.environ["ENTITLEMENT_FRIDA_ENDPOINT"]
    assert endpoint == "127.0.0.1:27045", "Only the dedicated local guest forward is allowed"
    source = pathlib.Path(sys.argv[1]).read_text()
    lock = threading.Lock()
    done = threading.Event()
    terminal = []
    failure = []
    script = None

    def record(kind, **fields):
        with lock:
            print(json.dumps({"kind": kind, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              **fields}), flush=True)

    def message(msg, data):
        record("frida-message", message=msg, attachment_bytes=len(data) if data else 0)
        if msg.get("type") == "error":
            failure.append("script-error")
        if msg.get("type") == "send":
            payload = msg.get("payload", {})
            if isinstance(payload, dict) and payload.get("kind") in ("dependency-stop", "failure"):
                terminal.append(payload)
                if payload.get("kind") == "failure":
                    failure.append(payload)
                elif not accepted_stop(payload):
                    failure.append("unrecognized-dependency-stop")
                if payload.get("terminal_ack") is True:
                    try:
                        # The runner redirects stdout to a regular private evidence file.
                        # Never acknowledge durability if this host sink cannot be synced.
                        sys.stdout.flush()
                        if not stat.S_ISREG(os.fstat(sys.stdout.fileno()).st_mode):
                            raise RuntimeError("Terminal acknowledgement requires a regular evidence file")
                        os.fsync(sys.stdout.fileno())
                        script.post({"type": "terminal-ack", "sequence": payload.get("sequence")})
                        record("terminal-acknowledged", sequence=payload.get("sequence"))
                    except BaseException as error:
                        failure.append("terminal-ack-failed")
                        record("terminal-ack-failed", error=str(error))

    def detached(reason, crash):
        record("detached", reason=reason, crash=str(crash) if crash else None)
        if crash:
            failure.append("native-crash")
        done.set()

    device = frida.get_device_manager().add_remote_device(endpoint)
    device.on("output", lambda pid, fd, data: record(
        "process-output", pid=pid, fd=fd, text=data.decode("utf-8", errors="replace")))
    pid = device.spawn(["/system/bin/sleep", "120"])
    record("spawned", pid=pid)
    session = None
    try:
        session = device.attach(pid)
        session.on("detached", detached)
        script = session.create_script(source)
        script.on("message", message)
        device.resume(pid)
        script.load()
        if not done.wait(60):
            failure.append("timeout")
            record("timeout", limit_seconds=60)
        record("result", dependency_stops=len(terminal), failures=failure)
        return 0 if len(terminal) == 1 and accepted_stop(terminal[0]) and not failure and done.is_set() else 3
    finally:
        if session is not None and not session.is_detached:
            session.detach()
        try:
            device.kill(pid)
            record("cleanup-killed", pid=pid)
        except frida.ProcessNotFoundError:
            record("cleanup-already-exited", pid=pid)


if __name__ == "__main__":
    raise SystemExit(main())
