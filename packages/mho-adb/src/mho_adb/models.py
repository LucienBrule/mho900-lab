"""Typed frame observations preserve private bytes without default repr disclosure."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DecodeLimits(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    max_stream_bytes: int = Field(default=64 * 1024**2, ge=1, le=1024**3)
    max_frames: int = Field(default=100000, ge=1, le=1000000)
    max_payload_bytes: int = Field(default=1024**2, ge=0, le=64 * 1024**2)


@dataclass(frozen=True)
class FrameData:
    offset: int
    arg0: int
    arg1: int
    checksum: int
    wire: bytes = field(repr=False)
    payload: bytes = field(repr=False)


@dataclass(frozen=True)
class ConnectFrame(FrameData):
    kind: Literal["CNXN"] = field(default="CNXN", init=False)

    @property
    def version(self) -> int:
        return self.arg0

    @property
    def maxdata(self) -> int:
        return self.arg1


@dataclass(frozen=True)
class AuthFrame(FrameData):
    kind: Literal["AUTH"] = field(default="AUTH", init=False)


@dataclass(frozen=True)
class OpenFrame(FrameData):
    kind: Literal["OPEN"] = field(default="OPEN", init=False)

    @property
    def local_id(self) -> int:
        return self.arg0


@dataclass(frozen=True)
class OkayFrame(FrameData):
    kind: Literal["OKAY"] = field(default="OKAY", init=False)

    @property
    def local_id(self) -> int:
        return self.arg0

    @property
    def remote_id(self) -> int:
        return self.arg1


@dataclass(frozen=True)
class CloseFrame(FrameData):
    kind: Literal["CLSE"] = field(default="CLSE", init=False)

    @property
    def local_id(self) -> int:
        return self.arg0

    @property
    def remote_id(self) -> int:
        return self.arg1


@dataclass(frozen=True)
class WriteFrame(FrameData):
    kind: Literal["WRTE"] = field(default="WRTE", init=False)

    @property
    def local_id(self) -> int:
        return self.arg0

    @property
    def remote_id(self) -> int:
        return self.arg1


type Frame = ConnectFrame | AuthFrame | OpenFrame | OkayFrame | CloseFrame | WriteFrame


@dataclass(frozen=True)
class DecodeIssue:
    code: str
    message: str
    byte_offset: int


@dataclass(frozen=True)
class DecodeAccepted:
    raw_sha256: str
    raw_bytes: int
    frames: tuple[Frame, ...]
    raw: bytes = field(repr=False)
    limits: DecodeLimits = field(default_factory=DecodeLimits)
    handshake_compatibility_proven: Literal[False] = False
    state_machine_validated: Literal[False] = False
    physical_origin_proven: Literal[False] = False
    device_execution_proven: Literal[False] = False
    kind: Literal["decode-accepted"] = field(default="decode-accepted", init=False)


@dataclass(frozen=True)
class DecodeRejected:
    issue: DecodeIssue
    prefix: tuple[Frame, ...]
    raw_sha256: str | None
    raw_bytes: int
    raw: bytes = field(repr=False)
    kind: Literal["decode-rejected"] = field(default="decode-rejected", init=False)
