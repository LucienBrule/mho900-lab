"""Independent synthetic capture bytes and externally sealed review inputs."""

from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path

from mho_evidence import SealCreated, SealRequest, seal

CLIENT_ADDRESS = "192.0.2.10"
SERVER_ADDRESS = "192.0.2.20"
CLIENT_PORT = 43000
SERVER_PORT = 5555
IDENTITY_REQUEST = b"*IDN?\n"
IDENTITY_RESPONSE = b"RIGOL,MHO984,SYNTHETIC,00.01.00\n"
STATUS_REQUEST = b":SYSTem:OPTion:STATus? FLEX\n"
STATUS_RESPONSE = b"1\n"


@dataclass(frozen=True)
class Packet:
    sequence: int
    flags: int
    payload: bytes = b""
    reverse: bool = False


def captured_record(packet: Packet) -> bytes:
    source = IPv4Address(SERVER_ADDRESS if packet.reverse else CLIENT_ADDRESS)
    destination = IPv4Address(CLIENT_ADDRESS if packet.reverse else SERVER_ADDRESS)
    source_port = SERVER_PORT if packet.reverse else CLIENT_PORT
    destination_port = CLIENT_PORT if packet.reverse else SERVER_PORT
    tcp = (
        source_port.to_bytes(2, "big")
        + destination_port.to_bytes(2, "big")
        + packet.sequence.to_bytes(4, "big")
        + bytes(4)
        + bytes([0x50, packet.flags])
        + bytes(6)
        + packet.payload
    )
    ipv4 = (
        b"\x45\0"
        + (20 + len(tcp)).to_bytes(2, "big")
        + bytes(4)
        + b"\x40\x06"
        + bytes(2)
        + source.packed
        + destination.packed
        + tcp
    )
    ethernet = bytes(12) + b"\x08\0" + ipv4
    return bytes(8) + len(ethernet).to_bytes(4, "little") * 2 + ethernet


def capture_bytes(request: bytes, response: bytes) -> bytes:
    header = (
        b"\xd4\xc3\xb2\xa1\x02\0\x04\0"
        + bytes(8)
        + (65535).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
    )
    packets = [
        Packet(sequence=100, flags=2),
        Packet(sequence=200, flags=18, reverse=True),
        Packet(sequence=101, flags=24, payload=request),
        Packet(sequence=201, flags=24, payload=response, reverse=True),
        Packet(sequence=101 + len(request), flags=17),
        Packet(sequence=201 + len(response), flags=17, reverse=True),
    ]
    return header + b"".join(captured_record(packet) for packet in packets)


def terminal_statistics(count: int = 6, dropped: int = 0) -> bytes:
    return (
        f"{count} packets captured\n"
        f"{count} packets received by filter\n"
        f"{dropped} packets dropped by kernel\n"
    ).encode()


@dataclass(frozen=True)
class Bundle:
    root: Path
    manifest: Path
    pin: str


def write_inputs(parent: Path) -> Path:
    root = parent.resolve() / "evidence"
    root.mkdir()
    (root / "capture.pcap").write_bytes(
        capture_bytes(
            IDENTITY_REQUEST + STATUS_REQUEST,
            IDENTITY_RESPONSE + STATUS_RESPONSE,
        )
    )
    (root / "stderr.txt").write_bytes(terminal_statistics())
    (root / "q-0.bin").write_bytes(IDENTITY_REQUEST)
    (root / "r-0.bin").write_bytes(IDENTITY_RESPONSE)
    (root / "q-1.bin").write_bytes(STATUS_REQUEST)
    (root / "r-1.bin").write_bytes(STATUS_RESPONSE)
    return root


def seal_inputs(root: Path, *, label: str = "seal.toml") -> Bundle:
    manifest = root.parent / label
    result = seal(SealRequest(root=root, output=manifest))
    if not isinstance(result, SealCreated):
        raise RuntimeError("synthetic fixture seal failed")
    return Bundle(root=root, manifest=manifest, pin=result.manifest_sha256)
