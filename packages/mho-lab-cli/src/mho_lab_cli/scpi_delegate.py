"""Read bounded preserved byte streams and delegate their SCPI interpretation."""

from dataclasses import dataclass
from pathlib import Path

from mho_lab_cli.inputs import read_bounded_regular
from mho_scpi import CodecLimits, ExchangeAccepted, ExchangeRejected, decode_exchange


@dataclass(frozen=True)
class ScpiInputRejected:
    message: str


def inspect_scpi(
    requests: Path, replies: Path
) -> ExchangeAccepted | ExchangeRejected | ScpiInputRejected:
    limits = CodecLimits()
    try:
        request = read_bounded_regular(requests, limits.max_exchange_bytes)
        response = read_bounded_regular(replies, limits.max_exchange_bytes)
    except (OSError, ValueError):
        # Exception strings can expose private paths or raw evidence; keep presentation structural.
        return ScpiInputRejected("cannot read bounded, unchanged regular transcript files")
    return decode_exchange(request, response, limits)
