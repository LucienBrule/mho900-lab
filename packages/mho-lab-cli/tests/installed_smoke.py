"""Installed-wheel consumer, copied outside the checkout and run with Python -I.

The shell gate supplies locations through explicit environment variables. This
module is not a user CLI and does not import source files from the checkout.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tomllib
from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path

from mho_adb import (
    DecodeAccepted,
    DecodeRejected,
    MatchOpenRequest,
    StreamReadyMatched,
    decode,
    match_open,
)
from mho_capture import (
    ReadyMarker,
    RecorderAbnormal,
    RecorderCleanupUncertain,
    RecorderGraceful,
    RecorderReady,
    RecorderRequest,
    RecorderStartFailed,
    RecorderStartRejected,
    lifecycle,
    reap,
    start,
    stop,
)
from mho_evidence import (
    ArchiveAccepted,
    ArchiveLimits,
    ArchiveRejected,
    ArchiveRequest,
    InventoryDelta,
    InventoryDiffRequest,
    SealCreated,
    SealRejected,
    SealRequest,
    Sha256,
    VerificationAccepted,
    VerificationLimits,
    VerificationRejected,
    VerifyRequest,
    compare_inventory,
    inspect_archive,
    load_manifest,
    seal,
    verify,
)
from mho_review import (
    ProfileAccepted,
    ReviewAccepted,
    ReviewRejected,
    ReviewRequest,
    load_profile,
    review,
)
from mho_rf import ReceiveQualified, ReceiveRejected, ReceiveRequest, qualify_receive
from mho_scpi import (
    ExchangeAccepted,
    IdentityObservation,
    IdentityQuery,
    OptionSelector,
    OptionStatusQuery,
    SessionComplete,
    SessionIncomplete,
    SessionRequest,
    decode_exchange,
    execute,
)
from mho_source import FactoryPointCommand, PointCommand, encode_factory_point, encode_point
from mho_transport import (
    Endpoint,
    TranscriptAccepted,
    TranscriptRejected,
    TranscriptRequest,
    reconstruct,
)
from mho_waveform import (
    ParsedWaveform,
    RawAcquisition,
    RawQualified,
    WaveformInputs,
    parse_ascii,
    qualify_raw,
)


@dataclass(frozen=True)
class Project:
    name: str
    version: str


@dataclass(frozen=True)
class InstalledPackage:
    name: str
    version: str
    workspace_member: bool
    modules: tuple[str, ...]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def table(value: object) -> dict[str, object]:
    require(isinstance(value, dict), "Expected TOML/metadata table")
    if not isinstance(value, dict):
        raise ValueError("Expected table")
    result: dict[str, object] = {}
    for key, item in value.items():
        require(isinstance(key, str), "Expected string table key")
        if isinstance(key, str):
            result[key] = item
    return result


def strings(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Expected string list")
    return [item for item in value if isinstance(item, str)]


def text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Expected string")
    return value


def toml(path: Path) -> dict[str, object]:
    value: object = tomllib.loads(path.read_text())
    return table(value)


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def workspace_projects(checkout: Path, frozen: Path) -> list[Project]:
    require((checkout / "pyproject.toml").read_bytes() == frozen.read_bytes(), "Workspace changed")
    workspace = table(table(toml(frozen)["tool"])["uv"])
    members = table(workspace["workspace"])
    excludes = strings(members.get("exclude", []))
    paths = {
        path
        for pattern in strings(members["members"])
        for path in checkout.glob(pattern)
        if not any(path.relative_to(checkout).match(excluded) for excluded in excludes)
    }
    projects: list[Project] = []
    for path in sorted(paths):
        project = table(toml(path / "pyproject.toml")["project"])
        projects.append(Project(canonical(text(project["name"])), text(project["version"])))
    require(bool(projects), "No workspace distributions found")
    require(len({p.name for p in projects}) == len(projects), "Duplicate workspace names")
    return projects


def installed_packages(checkout: Path, evidence: Path) -> list[InstalledPackage]:
    projects = workspace_projects(checkout, evidence / "workspace.toml")
    expected = {project.name: project.version for project in projects}
    lock = toml(evidence / "uv.lock")
    package_values = lock["package"]
    require(isinstance(package_values, list), "Lock package inventory missing")
    if not isinstance(package_values, list):
        raise ValueError("Lock package list missing")
    locked: dict[str, set[str]] = {}
    for value in package_values:
        package = table(value)
        locked.setdefault(canonical(text(package["name"])), set()).add(text(package["version"]))
    prefix = Path(sys.prefix).resolve()
    observed: list[InstalledPackage] = []
    for distribution in importlib.metadata.distributions():
        name = canonical(distribution.metadata["Name"])
        version = distribution.version
        require(version in locked.get(name, set()), "Installed dependency outside lock: " + name)
        require(
            Path(str(distribution.locate_file(""))).resolve().is_relative_to(prefix),
            "External distribution",
        )
        direct = distribution.read_text("direct_url.json")
        if direct is not None:
            decoded: object = json.loads(direct)
            origin = table(decoded)
            require("dir_info" not in origin, "Directory/editable install detected: " + name)
        modules: list[str] = []
        if name in expected:
            require(version == expected[name], "Workspace distribution version differs")
            require(distribution.files is not None, "Wheel file inventory missing")
            if distribution.files is None:
                raise ValueError("Wheel inventory unavailable")
            markers = [p for p in distribution.files if p.name == "py.typed"]
            require(bool(markers), "Typing marker absent: " + name)
            for marker in markers:
                require(
                    Path(str(distribution.locate_file(marker))).is_file(),
                    "Typing marker missing on disk",
                )
                module_name = str(marker.parent).replace("/", ".")
                module = importlib.import_module(module_name)
                location: object = getattr(module, "__file__", None)
                require(isinstance(location, str), "Imported module lacks concrete location")
                path = Path(text(location)).resolve()
                require(
                    path.is_relative_to(prefix), "Workspace import outside isolated environment"
                )
                require(not path.is_relative_to(checkout), "Editable source import detected")
                modules.append(module_name)
        observed.append(InstalledPackage(name, version, name in expected, tuple(sorted(modules))))
    actual = {p.name: p.version for p in observed if p.workspace_member}
    require(actual == expected, "Installed workspace inventory differs")
    require(len(list((evidence / "wheels").glob("*.whl"))) == len(projects), "Wheel count differs")
    return sorted(observed, key=lambda p: p.name)


def run_cli(evidence: Path, name: str, arguments: list[str], expected_exit: int) -> None:
    entry = Path(sys.prefix) / "bin" / "mho-lab"
    require(entry.is_file(), "Installed CLI entry point absent")
    result = subprocess.run(
        [sys.executable, "-I", str(entry), *arguments],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    (evidence / (name + ".stdout")).write_text(result.stdout)
    (evidence / (name + ".stderr")).write_text(result.stderr)
    require(result.returncode == expected_exit, "Unexpected installed CLI exit: " + name)


def evidence_roundtrip(evidence: Path) -> None:
    root = Path.cwd() / "fixture"
    root.mkdir()
    data = b"installed artifact consumer\n"
    (root / 'quoted "snowman" \u2603.bin').write_bytes(data)
    (root / "empty").write_bytes(b"")
    manifest_path = Path.cwd() / "library.toml"
    result = seal(SealRequest(root, manifest_path))
    require(isinstance(result, SealCreated), "Installed library seal failed")
    manifest = load_manifest(manifest_path.read_bytes())
    require(len(manifest.artifacts) == 2, "Library inventory differs")
    require(
        sum(a.size_bytes for a in manifest.artifacts) == len(data), "Library byte counts differ"
    )
    require(
        {a.sha256.root for a in manifest.artifacts}
        == {hashlib.sha256(data).hexdigest(), hashlib.sha256(b"").hexdigest()},
        "Independent content hashes differ",
    )
    require(
        isinstance(verify(VerifyRequest(root, manifest_path)), VerificationAccepted),
        "Verify failed",
    )
    before = manifest_path.read_bytes()
    require(isinstance(seal(SealRequest(root, manifest_path)), SealRejected), "Seal overwritten")
    require(manifest_path.read_bytes() == before, "Existing manifest bytes changed")
    run_cli(evidence, "cli-version", ["version"], 0)
    cli_manifest = Path.cwd() / "cli.toml"
    run_cli(evidence, "cli-seal", ["evidence", "seal", str(root), "--output", str(cli_manifest)], 0)
    require(cli_manifest.read_bytes() == before, "CLI and library serialization differ")
    arguments = ["evidence", "verify", str(root), "--manifest", str(cli_manifest)]
    run_cli(evidence, "cli-verify", arguments, 0)
    (root / "empty").write_bytes(b"changed")
    require(
        isinstance(verify(VerifyRequest(root, manifest_path)), VerificationRejected),
        "Installed library accepted altered evidence",
    )
    run_cli(evidence, "cli-tamper-rejected", arguments, 1)
    (evidence / "synthetic-manifest.toml").write_bytes(before)


def capture_record(sequence: int, flags: int, payload: bytes, *, reverse: bool = False) -> bytes:
    source = IPv4Address("192.0.2.2" if reverse else "192.0.2.1")
    destination = IPv4Address("192.0.2.1" if reverse else "192.0.2.2")
    source_port = 5555 if reverse else 41000
    destination_port = 41000 if reverse else 5555
    tcp = (
        source_port.to_bytes(2, "big")
        + destination_port.to_bytes(2, "big")
        + sequence.to_bytes(4, "big")
        + bytes(4)
        + bytes([0x50, flags])
        + bytes(6)
        + payload
    )
    ip = (
        b"\x45\x00"
        + (20 + len(tcp)).to_bytes(2, "big")
        + bytes(4)
        + b"\x40\x06"
        + bytes(2)
        + source.packed
        + destination.packed
        + tcp
    )
    ethernet = bytes(12) + b"\x08\x00" + ip
    return bytes(8) + len(ethernet).to_bytes(4, "little") * 2 + ethernet


def transport_roundtrip(evidence: Path) -> None:
    capture = Path.cwd() / "synthetic.pcap"
    request = b"SYNTHETIC-REQUEST\n"
    reply = b"SYNTHETIC-PRIVATE-REPLY\n"
    header = (
        b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00"
        + bytes(8)
        + (65535).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
    )
    encoded = (
        header
        + capture_record(100, 2, b"")
        + capture_record(200, 18, b"", reverse=True)
        + capture_record(101, 24, request)
        + capture_record(201, 24, reply, reverse=True)
        + capture_record(101 + len(request), 17, b"")
        + capture_record(201 + len(reply), 17, b"", reverse=True)
    )
    capture.write_bytes(encoded)
    selection = TranscriptRequest(
        capture=capture,
        client=Endpoint(address=IPv4Address("192.0.2.1"), port=41000),
        server=Endpoint(address=IPv4Address("192.0.2.2"), port=5555),
    )
    result = reconstruct(selection)
    if not isinstance(result, TranscriptAccepted):
        raise RuntimeError("Installed transport rejected complete synthetic capture")
    require(result.request == request and result.reply == reply, "Transport byte mismatch")
    require(result.metadata.capture_frames == 6, "Transport frame count differs")
    require(result.metadata.capture_sha256 == hashlib.sha256(encoded).hexdigest(), "Capture hash")
    arguments = [
        "transport",
        "inspect",
        str(capture),
        "--client-address",
        "192.0.2.1",
        "--client-port",
        "41000",
        "--server-address",
        "192.0.2.2",
        "--server-port",
        "5555",
    ]
    run_cli(evidence, "cli-transport", arguments, 0)
    stdout = evidence / "cli-transport.stdout"
    summary = toml(stdout)
    require(summary["capture_frames"] == 6, "CLI transport frame count differs")
    require(summary["request_sha256"] == hashlib.sha256(request).hexdigest(), "CLI request hash")
    require(summary["reply_sha256"] == hashlib.sha256(reply).hexdigest(), "CLI reply hash")
    require(summary["peer_delivery_proven"] is False, "CLI claims peer delivery")
    require(summary["device_execution_proven"] is False, "CLI claims device execution")
    require(b"SYNTHETIC" not in stdout.read_bytes(), "CLI exposed transcript payload")
    capture.write_bytes(encoded[:-1])
    require(isinstance(reconstruct(selection), TranscriptRejected), "Truncation accepted")
    run_cli(evidence, "cli-transport-truncation", arguments, 1)
    (evidence / "synthetic.pcap").write_bytes(encoded)


def recorder_roundtrip(evidence: Path) -> None:
    marker = "SYNTHETIC\x7f RECORDER READY 🕯"
    script = Path.cwd() / "synthetic_recorder.py"
    script.write_text(
        "import signal\nimport sys\nfrom types import FrameType\n"
        "def finish(signum: int, frame: FrameType | None) -> None:\n"
        "    print('3 packets captured', file=sys.stderr, flush=True)\n"
        "    print('3 packets received by filter', file=sys.stderr, flush=True)\n"
        "    print('0 packets dropped by kernel', file=sys.stderr, flush=True)\n"
        "    raise SystemExit(0)\n"
        "signal.signal(signal.SIGINT, finish)\n"
        "print(sys.argv[1], flush=True)\n"
        "while True:\n    signal.pause()\n"
    )
    directory = Path.cwd() / "recorder"
    result = start(
        RecorderRequest(
            executable=Path(sys.executable).resolve(),
            arguments=(str(script), marker),
            evidence_directory=directory,
            ready=ReadyMarker(stream="stdout", line=marker),
        )
    )
    if not isinstance(result, RecorderReady):
        if isinstance(result, RecorderStartFailed):
            reap(result.handle)
        raise RuntimeError("Installed recorder child failed to become ready")
    terminal = stop(result.handle)
    if not isinstance(terminal, RecorderGraceful):
        reap(result.handle)
        raise RuntimeError("Installed recorder did not stop gracefully")
    require(terminal.evidence.reaped, "Installed recorder not reaped")
    require(terminal.evidence.returncode == 0, "Installed recorder exit differs")
    require(stop(result.handle) == terminal, "Repeated stop changed the retained result")
    require(
        (directory / "stderr.bin").read_bytes().endswith(b"0 packets dropped by kernel\n"),
        "Installed child terminal output missing",
    )
    launch = tomllib.loads((directory / "launch.toml").read_text())
    readiness = tomllib.loads((directory / "ready.toml").read_text())
    require(launch["arguments"] == [str(script), marker], "Recorder argument round trip differs")
    require(readiness["marker"] == marker, "Recorder readiness round trip differs")
    terminal_record = tomllib.loads((directory / "terminal.toml").read_text())
    require(terminal_record["reason"] == terminal.evidence.reason, "Terminal reason differs")
    shutil.copytree(directory, evidence / "recorder")
    recorder_diagnostic_roundtrip(script, evidence)


def recorder_diagnostic_roundtrip(script: Path, evidence: Path) -> None:
    """Inject a local signal-submission failure into installed code; retain ownership."""
    directory = Path.cwd() / "recorder-diagnostic"
    result = start(
        RecorderRequest(
            executable=Path(sys.executable).resolve(),
            arguments=(str(script), "READY"),
            evidence_directory=directory,
            ready=ReadyMarker(stream="stdout", line="READY"),
        )
    )
    if not isinstance(result, RecorderReady):
        if isinstance(result, RecorderStartFailed):
            reap(result.handle)
        raise RuntimeError("Installed diagnostic child failed to become ready")
    diagnostic = "synthetic signal failure\x7f 🕯"
    original_signal = lifecycle._signal

    def fail_signal(handle: lifecycle.RecorderHandle, sig: signal.Signals) -> None:
        raise OSError(diagnostic)

    try:
        try:
            lifecycle._signal = fail_signal
            terminal = stop(result.handle)
        finally:
            lifecycle._signal = original_signal
        require(isinstance(terminal, RecorderCleanupUncertain), "Failure lost uncertainty")
        require(not terminal.evidence.reaped, "Synthetic unreaped control differs")
        expected = "; ".join([diagnostic] * 3)
        original = (directory / "terminal.toml").read_bytes()
        require(tomllib.loads(original.decode())["reason"] == expected, "Diagnostic differs")
        result.handle._process.send_signal(signal.SIGINT)
        reconciled = reap(result.handle)
        require(reconciled.evidence.reaped, "Installed diagnostic child not reaped")
        record = tomllib.loads((directory / "reap-1.toml").read_text())
        require(record["reason"] == expected + "; subsequently reaped", "Reap reason differs")
        require((directory / "terminal.toml").read_bytes() == original, "Terminal rewritten")
        shutil.copytree(directory, evidence / "recorder-diagnostic")
    finally:
        if result.handle._process.poll() is None:
            result.handle._process.kill()
            result.handle._process.wait(timeout=2)


class SuppliedMemoryStream:
    """One installed public-protocol consumer; no endpoint or socket involved."""

    def __init__(self, response: bytes) -> None:
        self.response = response
        self.written = b""

    def write(self, data: bytes, timeout: float) -> int:
        require(timeout > 0, "Executor supplied nonpositive timeout")
        self.written += data
        return len(data)

    def read(self, size: int, timeout: float) -> bytes:
        require(timeout > 0, "Executor supplied nonpositive timeout")
        part = self.response[:size]
        self.response = self.response[size:]
        return part


def scpi_roundtrip(evidence: Path) -> None:
    malformed = OptionStatusQuery(selector=OptionSelector.BND)
    object.__setattr__(malformed, "selector", "BND\n*RST")
    untouched = SuppliedMemoryStream(b"")
    bad_plan = SessionRequest.model_construct(queries=(IdentityQuery(), malformed))
    rejected = execute(untouched, bad_plan)
    require(isinstance(rejected, SessionIncomplete), "Installed invalid SCPI plan accepted")
    require(not untouched.written, "Installed invalid SCPI plan submitted bytes")
    request = b"*IDN?\n"
    response = b"Synthetic,Fixture,PRIVATE-SERIAL,opaque-version\r\n"
    decoded = decode_exchange(request, response)
    require(isinstance(decoded, ExchangeAccepted), "Installed SCPI codec rejected control")
    if not isinstance(decoded, ExchangeAccepted):
        raise RuntimeError("SCPI outcome did not narrow")
    observation = decoded.pairs[0].reply.observation
    require(isinstance(observation, IdentityObservation), "Installed identity variant missing")
    stream = SuppliedMemoryStream(response)
    outcome = execute(stream, SessionRequest(queries=(IdentityQuery(),)))
    require(isinstance(outcome, SessionComplete), "Installed executor failed")
    require(stream.written == request, "Installed executor changed query bytes")
    require(not stream.response, "Installed executor failed to consume response")
    request_path = evidence / "scpi-request.bin"
    response_path = evidence / "scpi-response.bin"
    request_path.write_bytes(request)
    response_path.write_bytes(response)
    run_cli(
        evidence,
        "scpi-redacted",
        ["scpi", "inspect", "--requests", str(request_path), "--replies", str(response_path)],
        0,
    )
    rendered = (evidence / "scpi-redacted.stdout").read_text()
    require(
        all(
            value not in rendered
            for value in ("Synthetic", "Fixture", "PRIVATE-SERIAL", "opaque-version")
        ),
        "Default installed CLI disclosed identity",
    )
    require(tomllib.loads(rendered)["query_count"] == 1, "Installed CLI emitted invalid report")
    require("identity_redacted = true" in rendered, "Installed CLI omitted redaction marker")


def review_roundtrip(evidence: Path) -> None:
    root = Path.cwd() / "review-bundle"
    root.mkdir()
    request = b"*IDN?\n"
    response = b"Synthetic,Fixture,PRIVATE-SERIAL,opaque-version\n"
    header = (
        b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00"
        + bytes(8)
        + (65535).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
    )
    capture = (
        header
        + capture_record(100, 2, b"")
        + capture_record(200, 18, b"", reverse=True)
        + capture_record(101, 24, request)
        + capture_record(201, 24, response, reverse=True)
        + capture_record(101 + len(request), 17, b"")
        + capture_record(201 + len(response), 17, b"", reverse=True)
    )
    (root / "capture.pcap").write_bytes(capture)
    (root / "stderr.txt").write_bytes(
        b"6 packets captured\n6 packets received by filter\n0 packets dropped by kernel\n"
    )
    (root / "request.bin").write_bytes(request)
    (root / "response.bin").write_bytes(response)
    manifest = Path.cwd() / "review-manifest.toml"
    sealed = seal(SealRequest(root, manifest))
    if not isinstance(sealed, SealCreated):
        raise RuntimeError("Installed review fixture could not be sealed")
    profile = Path.cwd() / "review-profile.toml"
    profile.write_text("""schema_version = "mho-review.profile/1"
capture = "capture.pcap"
statistics = "stderr.txt"
[client]
address = "192.0.2.1"
port = 41000
[server]
address = "192.0.2.2"
port = 5555
[[transcripts]]
request = "request.bin"
reply = "response.bin"
""")
    parsed = load_profile(profile.read_bytes())
    if not isinstance(parsed, ProfileAccepted):
        raise RuntimeError("Installed role profile rejected")
    result = review(ReviewRequest(root, manifest, Sha256(sealed.manifest_sha256), parsed.profile))
    require(isinstance(result, ReviewAccepted), "Installed composed review rejected")
    arguments = [
        "review",
        "inspect",
        "--root",
        str(root),
        "--manifest",
        str(manifest),
        "--expected-manifest-sha256",
        sealed.manifest_sha256,
        "--profile",
        str(profile),
    ]
    run_cli(evidence, "review-redacted", arguments, 0)
    rendered = (evidence / "review-redacted.stdout").read_text()
    require(
        all(
            value not in rendered
            for value in ("Synthetic", "Fixture", "PRIVATE-SERIAL", "opaque-version", "192.0.2.1")
        ),
        "Review disclosed identity or endpoint",
    )
    require(tomllib.loads(rendered)["capture_frames"] == 6, "Review frame count changed")
    (root / "response.bin").write_bytes(b"foreign\n")
    run_cli(evidence, "review-mixed-input", arguments, 1)
    rejected = tomllib.loads((evidence / "review-mixed-input.stdout").read_text())
    require(rejected["stage"] == "inventory-before", "Mixed input failed at unexpected stage")


def archive_roundtrip(evidence: Path) -> None:
    first = Path.cwd() / "logical-before.tar"
    second = Path.cwd() / "logical-after.tar"
    for path in (first, second):
        with tarfile.open(path, "w", format=tarfile.USTAR_FORMAT) as archive:
            payload = b"SYNTHETIC-PRIVATE-CONTENT"
            member = tarfile.TarInfo("data/stable.bin")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
            if path == second:
                member = tarfile.TarInfo("data/added.bin")
                member.size = 3
                archive.addfile(member, io.BytesIO(b"new"))
    first_pin = hashlib.sha256(first.read_bytes()).hexdigest()
    second_pin = hashlib.sha256(second.read_bytes()).hexdigest()
    before = inspect_archive(ArchiveRequest(first, Sha256(first_pin)))
    after = inspect_archive(ArchiveRequest(second, Sha256(second_pin)))
    if not isinstance(before, ArchiveAccepted) or not isinstance(after, ArchiveAccepted):
        raise RuntimeError("Installed archive inspection rejected")
    delta = compare_inventory(InventoryDiffRequest(before.artifacts, after.artifacts))
    require(isinstance(delta, InventoryDelta), "Installed inventory delta rejected")
    run_cli(
        evidence,
        "archive-delta",
        [
            "archive",
            "diff",
            "--before",
            str(first),
            "--before-sha256",
            first_pin,
            "--after",
            str(second),
            "--after-sha256",
            second_pin,
        ],
        0,
    )
    rendered = (evidence / "archive-delta.stdout").read_text()
    report = tomllib.loads(rendered)
    require(
        report["changed_files"] == 1 and report["unchanged_files"] == 1, "Archive CLI counts differ"
    )
    require("SYNTHETIC-PRIVATE-CONTENT" not in rendered, "Archive CLI exposed payload")
    require(not (Path.cwd() / "data").exists(), "Archive contents were extracted")
    run_cli(
        evidence,
        "archive-wrong-pin",
        ["archive", "inspect", str(first), "--expected-sha256", "0" * 64],
        1,
    )


def adb_frame(command: bytes, local: int, remote: int, payload: bytes = b"") -> bytes:
    word = int.from_bytes(command, "little")
    values = (word, local, remote, len(payload), sum(payload), word ^ 0xFFFFFFFF)
    return b"".join(value.to_bytes(4, "little") for value in values) + payload


def adb_roundtrip(evidence: Path) -> None:
    payload = b"shell:SYNTHETIC-PRIVATE-COMMAND\0"
    client_raw = adb_frame(b"OPEN", 7, 0, payload)
    server_raw = adb_frame(b"OKAY", 9, 7)
    client = decode(client_raw)
    server = decode(server_raw)
    require(isinstance(client, DecodeAccepted), "Installed ADB client decode rejected")
    require(isinstance(server, DecodeAccepted), "Installed ADB server decode rejected")
    if not isinstance(client, DecodeAccepted) or not isinstance(server, DecodeAccepted):
        raise RuntimeError("Installed ADB framing rejected")
    selector = hashlib.sha256(payload).hexdigest()
    matched = match_open(MatchOpenRequest(client, server, Sha256(selector)))
    require(isinstance(matched, StreamReadyMatched), "Installed ADB ready matcher rejected")
    require(isinstance(decode(client_raw[:-1]), DecodeRejected), "ADB truncation accepted")
    first = evidence / "adb-client.bin"
    second = evidence / "adb-server.bin"
    first.write_bytes(client_raw)
    second.write_bytes(server_raw)
    run_cli(
        evidence,
        "adb-inspect",
        ["adb", "inspect", str(first), "--expected-sha256", client.raw_sha256],
        0,
    )
    run_cli(
        evidence,
        "adb-ready",
        [
            "adb",
            "match-open",
            "--client",
            str(first),
            "--client-sha256",
            client.raw_sha256,
            "--server",
            str(second),
            "--server-sha256",
            server.raw_sha256,
            "--payload-sha256",
            selector,
        ],
        0,
    )
    rendered = (evidence / "adb-ready.stdout").read_text()
    report = tomllib.loads(rendered)
    require(report["result"] == "matched" and report["ready_frames"] == 1, "ADB match CLI differs")
    require(report["device_execution_proven"] is False, "ADB report promoted device action")
    require(
        "SYNTHETIC-PRIVATE-COMMAND" not in rendered and str(first) not in rendered,
        "ADB private input exposed",
    )
    run_cli(
        evidence, "adb-pin-reject", ["adb", "inspect", str(first), "--expected-sha256", "0" * 64], 1
    )


def public_walkthrough(checkout: Path, evidence: Path) -> None:
    fixture = Path.cwd() / "public-fixture"
    shutil.copytree(checkout / "examples" / "sealed-review", fixture)
    output = Path.cwd() / "public-walkthrough"
    environment = dict(os.environ)
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    result = subprocess.run(
        ["sh", str(fixture / "walkthrough.sh"), str(output)],
        env=environment,
        capture_output=True,
        timeout=30,
        check=False,
    )
    (evidence / "public-walkthrough.stdout").write_bytes(result.stdout)
    (evidence / "public-walkthrough.stderr").write_bytes(result.stderr)
    require(result.returncode == 0, "Installed public walkthrough failed")
    accepted = toml(output / "accepted.toml")
    changed = toml(output / "changed.toml")
    mixed = toml(output / "mixed.toml")
    require(
        accepted["result"] == "accepted" and accepted["query_count"] == 2,
        "Installed public example acceptance differs",
    )
    require(changed["stage"] == "inventory-before", "Public modified seal was accepted")
    require(
        mixed["stage"] == "transcripts" and mixed["code"] == "tcp-transcript-mismatch",
        "Public resealed mismatch was accepted",
    )
    require(
        "SYNTHETIC-UNIT" not in (output / "accepted.toml").read_text(),
        "Public identity was rendered by default",
    )
    shutil.copytree(fixture, evidence / "public-fixture")
    shutil.copytree(output, evidence / "public-walkthrough")


@dataclass(frozen=True)
class OwnedCase:
    name: str
    exitcode: int
    dropped: int


def owned_recorder_review(checkout: Path, evidence: Path) -> None:
    """Actual owned child lifetime, manufactured capture and counter content."""
    child = Path.cwd() / "owned-review-child.py"
    child.write_text(
        "import signal, shutil, sys\n"
        "from pathlib import Path\n"
        "def finish(signum: int, frame: object) -> None:\n"
        "    print('6 packets captured', file=sys.stderr)\n"
        "    print('6 packets received by filter', file=sys.stderr)\n"
        "    print(sys.argv[4] + ' packets dropped by kernel', file=sys.stderr, flush=True)\n"
        "    raise SystemExit(int(sys.argv[3]))\n"
        "signal.signal(signal.SIGINT, finish)\n"
        "shutil.copytree(Path(sys.argv[1]), Path(sys.argv[2]) / 'data')\n"
        "print('SYNTHETIC REVIEW READY', flush=True)\n"
        "while True:\n    signal.pause()\n"
    )
    profile_raw = b"""schema_version = "mho-review.profile/1"
capture = "data/capture.pcap"
statistics = "stderr.bin"
[client]
address = "192.0.2.1"
port = 41000
[server]
address = "192.0.2.2"
port = 5555
[[transcripts]]
request = "data/queries/00-request.bin"
reply = "data/queries/00-response.bin"
[[transcripts]]
request = "data/queries/01-request.bin"
reply = "data/queries/01-response.bin"
"""
    parsed = load_profile(profile_raw)
    if not isinstance(parsed, ProfileAccepted):
        raise RuntimeError("Owned control profile invalid")
    (evidence / "owned-review-profile.toml").write_bytes(profile_raw)
    lines = [
        'schema_version = "mho900-lab.owned-synthetic-review/1"',
        "synthetic_packets = true",
        "synthetic_counters = true",
        "network_operations = false",
        "instrument_operations = false",
    ]
    for case in (
        OwnedCase("accepted", 0, 0),
        OwnedCase("abnormal", 7, 0),
        OwnedCase("drops", 0, 1),
    ):
        directory = (Path.cwd() / ("owned-review-" + case.name)).resolve()
        manifest = Path.cwd() / ("owned-review-" + case.name + ".toml")
        started = start(
            RecorderRequest(
                executable=Path(sys.executable).resolve(),
                arguments=(
                    str(child),
                    str(checkout / "examples/sealed-review/bundle"),
                    str(directory),
                    str(case.exitcode),
                    str(case.dropped),
                ),
                evidence_directory=directory,
                ready=ReadyMarker(stream="stdout", line="SYNTHETIC REVIEW READY"),
            )
        )
        if not isinstance(started, RecorderReady):
            if isinstance(started, RecorderStartFailed):
                reap(started.handle)
            raise RuntimeError("Owned synthetic control failed readiness")
        try:
            terminal = stop(started.handle)
        finally:
            cleanup = reap(started.handle)
        require(cleanup.evidence.reaped, "Owned child cleanup remained uncertain")
        review_result = "not-run"
        review_stage = "not-run"
        if case.exitcode:
            require(isinstance(terminal, RecorderAbnormal), "Abnormal child promoted to graceful")
            require(not manifest.exists(), "Abnormal child continued to sealing")
        else:
            require(
                isinstance(terminal, RecorderGraceful), "Synthetic child did not stop gracefully"
            )
            sealed = seal(SealRequest(directory, manifest))
            if not isinstance(sealed, SealCreated):
                raise RuntimeError("Owned result sealing failed")
            result = review(
                ReviewRequest(directory, manifest, Sha256(sealed.manifest_sha256), parsed.profile)
            )
            review_result = result.kind
            if case.dropped:
                require(
                    isinstance(result, ReviewRejected), "Observed drop was promoted to acceptance"
                )
                if isinstance(result, ReviewRejected):
                    review_stage = result.issue.stage
                    require(
                        review_stage == "assessment", "Drop control rejected at unexpected stage"
                    )
            else:
                require(isinstance(result, ReviewAccepted), "Owned synthetic review rejected")
                review_stage = "accepted"
            shutil.copyfile(manifest, evidence / manifest.name)
        shutil.copytree(directory, evidence / directory.name)
        lines.extend(
            [
                "",
                "[[cases]]",
                f'name = "{case.name}"',
                f'lifecycle = "{terminal.kind}"',
                f'review = "{review_result}"',
                f'stage = "{review_stage}"',
                "child_reaped = true",
            ]
        )
    (evidence / "owned-review.toml").write_text("\n".join(lines) + "\n")


def unchecked_boundary_controls(evidence: Path) -> None:
    absent = Path.cwd() / "preflight-no-artifacts"
    archive_limits = ArchiveLimits().model_copy(update={"max_source_bytes": None})
    archived = inspect_archive(ArchiveRequest(absent, Sha256("0" * 64), archive_limits))
    require(isinstance(archived, ArchiveRejected), "Installed unchecked archive bound accepted")
    if isinstance(archived, ArchiveRejected):
        require(
            archived.issue.code == "archive-contract", "Archive input consumed before validation"
        )
    limits = VerificationLimits().model_copy(update={"max_entries": float("inf")})
    verified = verify(VerifyRequest(absent, absent, limits))
    require(
        isinstance(verified, VerificationRejected),
        "Installed unchecked verification bound accepted",
    )
    if isinstance(verified, VerificationRejected):
        require(
            verified.issue.code == "invalid-limits", "Verification input consumed before validation"
        )
    request = RecorderRequest(
        executable=absent,
        evidence_directory=absent,
        ready=ReadyMarker(stream="stdout", line="NOT RUN"),
    ).model_copy(update={"startup_timeout": float("inf")})
    started = start(request)
    if isinstance(started, (RecorderReady, RecorderStartFailed)):
        stop(started.handle)
        reap(started.handle)
        raise RuntimeError("Installed invalid recorder request launched a child")
    require(isinstance(started, RecorderStartRejected), "Invalid recorder request not rejected")
    require(started.directory is None and not absent.exists(), "Invalid recorder created evidence")
    (evidence / "boundary-controls.toml").write_text(
        'result = "accepted"\nunchecked_artifact_limits_rejected = true\n'
        "unchecked_recorder_rejected_before_directory = true\n"
    )


def rf_receive_roundtrip(evidence: Path) -> None:
    """Installed NumPy-backed library and independent offline CLI use the same RAW evidence."""
    points = 100_000
    directory = Path.cwd() / "rf-receive-input"
    directory.mkdir()
    preamble = b"2,2,100000,1,2.5e-10,0,0,6e-6,0,32768\n"
    before, data, after = directory / "before.txt", directory / "data.txt", directory / "after.txt"
    before.write_bytes(preamble)
    after.write_bytes(preamble)
    acquisition = RawAcquisition(
        actual_sample_rate_hz=4e9, memory_points=points, start=1, stop=points
    )
    for case in ("qualified", "wrong-global"):
        values = (
            0.12 * math.sin(2 * math.pi * 600e6 * n / 4e9)
            if case == "qualified"
            else 0.052 * math.sin(2 * math.pi * 600e6 * n / 4e9)
            + 0.1 * math.sin(2 * math.pi * 1.2e9 * n / 4e9)
            for n in range(points)
        )
        waveform = (",".join(f"{value:.16e}" for value in values) + "\n").encode()
        data.write_bytes(waveform)
        parsed = parse_ascii(
            WaveformInputs(preamble_before=preamble, waveform=waveform, preamble_after=preamble)
        )
        require(isinstance(parsed, ParsedWaveform), "Installed RF waveform failed parsing")
        if not isinstance(parsed, ParsedWaveform):
            raise RuntimeError("RF parsed variant missing")
        raw = qualify_raw(parsed, acquisition)
        require(isinstance(raw, RawQualified), "Installed RF raw qualification failed")
        if not isinstance(raw, RawQualified):
            raise RuntimeError("RF raw variant missing")
        result = qualify_receive(ReceiveRequest(record=raw, command_frequency_hz=600e6))
        expected = 0 if case == "qualified" else 1
        run_cli(
            evidence,
            "rf-receive-" + case,
            [
                "rf",
                "receive-inspect",
                "--preamble-before",
                str(before),
                "--data",
                str(data),
                "--preamble-after",
                str(after),
                "--actual-rate-hz",
                "4000000000",
                "--memory-points",
                "100000",
                "--start",
                "1",
                "--stop",
                "100000",
                "--command-frequency-hz",
                "600000000",
            ],
            expected,
        )
        receipt = toml(evidence / ("rf-receive-" + case + ".stdout"))
        require(receipt["result"] == result.kind, "Installed RF library/CLI result differs")
        require(receipt["physical_origin_proven"] is False, "RF origin claim changed")
        require(receipt["final_fit_validity_proven"] is False, "RF fit claim changed")
        if case == "qualified":
            require(isinstance(result, ReceiveQualified), "Installed valid RF record rejected")
        else:
            require(isinstance(result, ReceiveRejected), "Installed wrong-global carrier accepted")
            if isinstance(result, ReceiveRejected):
                require(result.issue.code == "global-peak-frequency", "RF rejection reason differs")
        require(result.spectrum is not None, "Installed RF spectrum missing")
        if result.spectrum is not None:
            require(
                receipt["energy_fraction"] == result.spectrum.energy_fraction,
                "Installed RF library/CLI energy differs",
            )
        require(
            receipt["waveform_sha256"] == hashlib.sha256(waveform).hexdigest(),
            "Installed RF receipt hash differs",
        )
    (evidence / "rf-receive.toml").write_text(
        'result = "accepted"\nlibrary_cli_qualified_match = true\n'
        "wrong_global_carrier_rejected = true\nphysical_origin_proven = false\n"
    )


def main() -> int:
    checkout = Path(os.environ["MHO_PACKAGE_CHECKOUT"]).resolve()
    evidence = Path(os.environ["MHO_PACKAGE_EVIDENCE"]).resolve()
    require(sys.flags.isolated == 1, "Interpreter must use -I")
    require(not Path.cwd().resolve().is_relative_to(checkout), "Working directory inside checkout")
    require(not Path(__file__).resolve().is_relative_to(checkout), "Smoke module inside checkout")
    require(not Path(sys.prefix).resolve().is_relative_to(checkout), "Environment inside checkout")
    require(
        all(not Path(p).resolve().is_relative_to(checkout) for p in sys.path),
        "Checkout appears on isolated import path",
    )
    packages = installed_packages(checkout, evidence)
    unchecked_boundary_controls(evidence)
    rf_receive_roundtrip(evidence)
    evidence_roundtrip(evidence)
    recorder_roundtrip(evidence)
    transport_roundtrip(evidence)
    scpi_roundtrip(evidence)
    review_roundtrip(evidence)
    archive_roundtrip(evidence)
    adb_roundtrip(evidence)
    candidate = PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4)
    require(encode_point(candidate).hex() == "ad01010403d0900186a03d", "Source frame mismatch")
    run_cli(
        evidence,
        "source-frame",
        [
            "source",
            "frame",
            "--frequency-hz",
            "100000000",
            "--reference-hz",
            "25000000",
            "--power-code",
            "4",
        ],
        0,
    )
    require(
        (evidence / "source-frame.stdout").read_text().strip()
        == "AD 01 01 04 03 D0 90 01 86 A0 3D",
        "Installed source CLI differs",
    )
    factory = FactoryPointCommand(frequency_hz=100_250_000, power_code=0)
    require(encode_factory_point(factory).hex() == "555500640019000d0a", "Factory frame mismatch")
    run_cli(
        evidence,
        "factory-frame",
        ["source", "factory-frame", "--frequency-hz", "100250000", "--power-code", "0"],
        0,
    )
    require(
        (evidence / "factory-frame.stdout").read_text().strip() == "55 55 00 64 00 19 00 0D 0A",
        "Installed factory CLI differs",
    )
    public_walkthrough(checkout, evidence)
    owned_recorder_review(checkout, evidence)
    lines = [
        'schema = "mho900-lab.installed-package-check/1"',
        'result = "accepted"',
        "isolated_interpreter = true",
        "noneditable_workspace = true",
        "installed_wheels_rebuilt_from_sdists = true",
        "outside_checkout = true",
        "dependency_versions_locked = true",
        "typing_markers_present = true",
        "library_cli_bytes_equal = true",
        "existing_seal_preserved = true",
        "library_cli_tamper_rejected = true",
        "installed_recorder_ready_and_reaped = true",
        "transport_library_cli_verified = true",
        "transport_payload_not_rendered = true",
        "transport_truncation_rejected = true",
        "scpi_codec_executor_cli_verified = true",
        "sealed_review_library_cli_verified = true",
        "sealed_review_mixed_input_rejected = true",
        "archive_inventory_delta_library_cli_verified = true",
        "archive_extraction_performed = false",
        "adb_frame_match_library_cli_verified = true",
        "public_synthetic_walkthrough_verified = true",
        "owned_synthetic_recorder_review_verified = true",
        "unchecked_public_boundaries_verified = true",
        "source_offline_frame_library_cli_verified = true",
        "factory_offline_frame_library_cli_verified = true",
        "rf_receive_library_cli_qualified_and_rejected_verified = true",
    ]
    for package in packages:
        lines.extend(
            [
                "",
                "[[packages]]",
                "name = " + json.dumps(package.name),
                "version = " + json.dumps(package.version),
                "workspace_member = " + str(package.workspace_member).lower(),
                "modules = " + json.dumps(list(package.modules)),
            ]
        )
    for folder in ("distributions", "wheels"):
        for artifact in sorted((evidence / folder).iterdir()):
            require(artifact.is_file(), "Unexpected build artifact directory")
            lines.extend(
                [
                    "",
                    "[[distributions]]",
                    "path = " + json.dumps(folder + "/" + artifact.name),
                    "sha256 = " + json.dumps(hashlib.sha256(artifact.read_bytes()).hexdigest()),
                ]
            )
    (evidence / "result.toml").write_text("\n".join(lines) + "\n")
    print("Installed wheels, public imports, typing markers, and evidence controls passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
