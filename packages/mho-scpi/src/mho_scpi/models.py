"""Exact read-only query alternatives and lossless decoded observations."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OptionSelector(StrEnum):
    BND = "BND"
    AFG100 = "AFG100"
    AFG50 = "AFG50"
    AUDIO = "AUDio"
    CAN_FD = "CAN-FD"
    FLEX = "FLEX"
    AERO = "AERO"
    RLU_05 = "RLU-05"
    BWU03T05 = "BWU03T05"
    BWU03T08 = "BWU03T08"
    BWU05T08 = "BWU05T08"


class IdentityQuery(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    kind: Literal["identity"] = "identity"


class OptionStatusQuery(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    kind: Literal["option-status"] = "option-status"
    selector: OptionSelector


type Query = IdentityQuery | OptionStatusQuery


class CodecLimits(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    max_line_bytes: int = Field(default=4096, ge=2, le=1024**2)
    max_queries: int = Field(default=128, ge=1, le=4096)
    max_exchange_bytes: int = Field(default=1024**2, ge=2, le=16 * 1024**2)


class OptionState(StrEnum):
    DISABLED = "0"
    ENABLED = "1"


@dataclass(frozen=True)
class IdentityObservation:
    manufacturer: str
    model: str
    serial_number: str
    software_revision: str
    kind: Literal["identity-observation"] = field(default="identity-observation", init=False)


@dataclass(frozen=True)
class OptionStatusObservation:
    selector: OptionSelector
    state: OptionState
    kind: Literal["option-status-observation"] = field(
        default="option-status-observation", init=False
    )


type Observation = IdentityObservation | OptionStatusObservation


@dataclass(frozen=True)
class CodecIssue:
    code: str
    message: str
    query_index: int | None = None


@dataclass(frozen=True)
class ReplyAccepted:
    query: Query
    raw: bytes
    observation: Observation
    kind: Literal["reply-accepted"] = field(default="reply-accepted", init=False)


@dataclass(frozen=True)
class ReplyRejected:
    issue: CodecIssue
    query: Query = field(repr=False)
    raw: bytes = field(repr=False)
    kind: Literal["reply-rejected"] = field(default="reply-rejected", init=False)


@dataclass(frozen=True)
class DecodedPair:
    query: Query
    request: bytes
    reply: ReplyAccepted


@dataclass(frozen=True)
class ExchangeAccepted:
    request: bytes
    response: bytes
    pairs: tuple[DecodedPair, ...]
    kind: Literal["exchange-accepted"] = field(default="exchange-accepted", init=False)


@dataclass(frozen=True)
class ExchangeRejected:
    issue: CodecIssue
    request: bytes = field(repr=False)
    response: bytes = field(repr=False)
    kind: Literal["exchange-rejected"] = field(default="exchange-rejected", init=False)
