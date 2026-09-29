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
import time

import frida


STOCK_STOPS = {"runtime-dna-unavailable", "private-fram-unavailable", "unexpected-pcie-init"}


def accepted_stop(payload):
    if payload.get("kind") != "dependency-stop":
        return False
    if payload.get("reason") == "acquired-key-baseline-complete":
        checks = payload.get("expected_checks", {})
        return (payload.get("exit_code") == 77 and payload.get("terminal_ack") is True
                and all(checks.get(name) is True for name in (
                    "key_outputs_exact", "file_keys_exact", "key_file_unchanged",
                    "fresh_private_store", "catalog_complete", "no_installer", "started_false")))
    if payload.get("reason") == "acquired-combined-phase-complete":
        checks = payload.get("expected_checks")
        required = {"started_false", "catalog_complete", "seed_catalog_matches", "seed_inputs_preserved",
                    "private_reloaded", "catalog_unchanged", "no_installer", "no_token_regeneration",
                    "capability_identity_preserved", "capability_bandwidth_selected", "capability_record_selected",
                    "capability_option_policy_preserved", "capability_queries_succeeded"}
        names = {0: "BND", 1: "EMBD", 2: "COMP", 3: "AUTO", 4: "AUTOA", 5: "FlexA",
                 6: "AUDIOA", 7: "AEROA", 19: "RLU05", 30: "AFG50", 29: "AFG100",
                 22: "BWU03T05", 23: "BWU03T08", 24: "BWU05T08"}
        before, after = payload.get("catalog_before"), payload.get("catalog_after")
        return (payload.get("phase") == os.environ.get("ENTITLEMENT_PHASE") == "reload"
                and payload.get("acquired_combined_experiment") is True
                and payload.get("physical_contact") is False
                and payload.get("persistence_backend") == "stock-memfile-harness-directed-file"
                and payload.get("exit_code") == 77 and payload.get("terminal_ack") is True
                and isinstance(checks, dict) and required <= set(checks)
                and all(value is True for value in checks.values())
                and isinstance(before, list) and len(before) == 14 and before == after
                and all(isinstance(item, dict) and type(item.get("option_type")) is int
                        and item["option_type"] in names
                        and item.get("option_name") == names[item["option_type"]]
                        and item.get("valid") is (item["option_type"] != 0)
                        and type(item.get("status")) is int and item["status"] == 0 for item in before)
                and {item["option_type"] for item in before} == set(names))
    if payload.get("reason") in ("option-catalog-phase-complete", "acquired-option-phase-complete"):
        phase = payload.get("phase")
        common = {"started_false", "catalog_complete", "seed_catalog_matches", "seed_inputs_preserved",
                  "private_reloaded", "catalog_delta_exact", "candidate_file_matches",
                  "capability_identity_preserved", "capability_bandwidth_selected", "capability_record_selected",
                  "capability_option_policy_preserved", "capability_queries_succeeded"}
        fresh = {"token_roundtrip", "wire_codec_roundtrip", "baseline_candidate_disabled"}
        phase_checks = {
            "negative": fresh | {"negative_rejected", "negative_no_license_file"},
            "positive": fresh | {"positive_accepted", "positive_license_file"},
            "reload": {"reload_persisted", "no_installer", "no_token_regeneration"},
        }
        checks = payload.get("expected_checks")
        if phase not in phase_checks or phase != os.environ.get("ENTITLEMENT_PHASE") or not isinstance(checks, dict):
            return False
        catalogs = (payload.get("catalog_before"), payload.get("catalog_after"))
        return (payload.get("exit_code") == 77 and payload.get("terminal_ack") is True
                and all(checks.get(key) is True for key in common | phase_checks[phase])
                and all(isinstance(catalog, list) and len(catalog) == 14
                        and all(isinstance(item, dict) and type(item.get("option_type")) is int
                                and isinstance(item.get("option_name"), str) and type(item.get("valid")) is bool
                                and type(item.get("status")) is int and item["status"] == 0 for item in catalog)
                        and len({item["option_type"] for item in catalog}) == 14 for catalog in catalogs))
    if payload.get("reason") == "entitlement-phase-complete":
        phase = payload.get("phase")
        required = {"started_false", "catalog_complete"}
        phase_checks = {
            "negative": {"key_roundtrip", "token_roundtrip", "wire_codec_roundtrip", "baseline_candidate_disabled", "negative_rejected", "negative_no_license_file"},
            "positive": {"key_roundtrip", "token_roundtrip", "wire_codec_roundtrip", "baseline_candidate_disabled", "positive_accepted", "positive_license_file"},
            "reload": {"reload_persisted", "positive_license_file", "key_matches_saved_witness", "license_matches_saved_witness"},
        }
        checks = payload.get("expected_checks")
        expected_phase = os.environ.get("ENTITLEMENT_PHASE")
        if phase not in phase_checks or phase != expected_phase or not isinstance(checks, dict):
            return False
        catalogs = (payload.get("catalog_before"), payload.get("catalog_after"))
        return (payload.get("exit_code") == 77
                and payload.get("terminal_ack") is True
                and all(checks.get(key) is True for key in required | phase_checks[phase])
                and all(isinstance(catalog, list) and len(catalog) == 14
                        and all(isinstance(item, dict)
                                and type(item.get("option_type")) is int
                                and isinstance(item.get("option_name"), str)
                                and type(item.get("valid")) is bool
                                and type(item.get("status")) is int and item["status"] == 0 for item in catalog)
                        and len({item["option_type"] for item in catalog}) == 14
                        for catalog in catalogs))
    if payload.get("reason") in STOCK_STOPS:
        return payload.get("exit_code") == 77
    if payload.get("reason") == "art-readiness-confirmed":
        return (payload.get("stage") == "stock-api-jni-readiness"
                and payload.get("exit_code") == 77
                and payload.get("java_vm_verified") is True
                and payload.get("api_class_loaded") is True
                and payload.get("stock_factory_called") is False
                and payload.get("callback_substitution") is False
                and payload.get("get_env_return") == 0
                and all(payload.get(name) is True for name in (
                    "environment_present", "class_global_present", "redraw_method_present", "error_method_present")))
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


class ArtHostMarker:
    """Accept one complete stdout readiness line only from the spawned host."""
    marker = b"ART_HOST_READY lab.mho900.guest.EntitlementHost"

    def __init__(self):
        self.pid = None
        self.ready = threading.Event()
        self.buffer = b""
        self.overflow = False
        self.lock = threading.Lock()

    def feed(self, pid, fd, data):
        with self.lock:
            if self.pid is None or pid != self.pid or fd != 1 or self.overflow:
                return
            self.buffer += data
            if len(self.buffer) > 65536:
                self.overflow = True
                return
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                if line == self.marker:
                    self.ready.set()


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
    art_marker = ArtHostMarker()

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

    def output(pid, fd, data):
        record("process-output", pid=pid, fd=fd, text=data.decode("utf-8", errors="replace"))
        art_marker.feed(pid, fd, data)

    device = frida.get_device_manager().add_remote_device(endpoint)
    device.on("output", output)
    host_mode = os.environ.get("ENTITLEMENT_HOST", "sleep")
    if host_mode == "art":
        guest_root = "/data/local/tmp/entitlement"
        environment = {
            "CLASSPATH": guest_root + "/art/host.jar:" + guest_root + "/art/stock.apk",
            "LD_LIBRARY_PATH": guest_root + "/lib",
        }
        argv = ["/system/bin/app_process64", "-Djava.library.path=" + guest_root + "/lib",
                "/system/bin", "lab.mho900.guest.EntitlementHost"]
        pid = device.spawn(argv, env=environment, stdio="pipe")
        record("spawned", pid=pid, host_mode=host_mode, argv=argv, environment=environment)
    elif host_mode == "sleep":
        argv = ["/system/bin/sleep", "120"]
        pid = device.spawn(argv, stdio="pipe")
        record("spawned", pid=pid, host_mode=host_mode, argv=argv)
    else:
        raise ValueError("Unknown disposable guest host mode")
    art_marker.pid = pid
    session = None
    try:
        session = device.attach(pid)
        session.on("detached", detached)
        device.resume(pid)
        if host_mode == "art":
            deadline = time.monotonic() + 15
            while not art_marker.ready.is_set() and not done.is_set() and not art_marker.overflow:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                art_marker.ready.wait(min(0.1, remaining))
            if not art_marker.ready.is_set() or done.is_set() or art_marker.overflow:
                failure.append("art-host-readiness-failed")
                record("art-host-readiness-failed", pid=pid, limit_seconds=15,
                       process_detached=done.is_set(), output_overflow=art_marker.overflow,
                       stock_script_loaded=False)
                record("result", dependency_stops=0, failures=failure)
                return 3
            record("art-host-readiness-confirmed", pid=pid, stock_script_loaded=False)
        script = session.create_script(source)
        script.on("message", message)
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
