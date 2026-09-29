"""Installed-wheel consumer, copied outside the checkout and run with Python -I.

The shell gate supplies locations through explicit environment variables. This
module is not a user CLI and does not import source files from the checkout.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path

from mho_evidence import (
    SealCreated,
    SealRejected,
    SealRequest,
    VerificationAccepted,
    VerificationRejected,
    VerifyRequest,
    load_manifest,
    seal,
    verify,
)
from mho_transport import (
    Endpoint,
    TranscriptAccepted,
    TranscriptRejected,
    TranscriptRequest,
    reconstruct,
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
    evidence_roundtrip(evidence)
    transport_roundtrip(evidence)
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
        "transport_library_cli_verified = true",
        "transport_payload_not_rendered = true",
        "transport_truncation_rejected = true",
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
