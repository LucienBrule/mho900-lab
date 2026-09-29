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
import threading

import frida


def main():
    assert len(sys.argv) == 2, "Pass one frozen Frida JavaScript source"
    endpoint = os.environ["ENTITLEMENT_FRIDA_ENDPOINT"]
    assert endpoint == "127.0.0.1:27045", "Only the dedicated local guest forward is allowed"
    source = pathlib.Path(sys.argv[1]).read_text()
    lock = threading.Lock()
    done = threading.Event()
    terminal = []
    failure = []

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
            if isinstance(payload, dict) and payload.get("kind") == "dependency-stop":
                terminal.append(payload)
            if isinstance(payload, dict) and payload.get("kind") == "failure":
                failure.append(payload)

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
        return 0 if len(terminal) == 1 and not failure and done.is_set() else 3
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
