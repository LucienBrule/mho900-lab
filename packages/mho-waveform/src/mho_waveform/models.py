"""Immutable contracts for supplied ASCII volts and explicit acquisition observations."""

import hashlib
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always", allow_inf_nan=False
    )


class WaveformFormat(IntEnum):
    BYTE = 0
    WORD = 1
    ASCII = 2


class WaveformMode(IntEnum):
    NORMAL = 0
    MAXIMUM = 1
    RAW = 2


class WaveformLimits(StrictModel):
    max_preamble_bytes: int = Field(default=1024, ge=2, le=65536)
    max_waveform_bytes: int = Field(default=32 * 1024**2, ge=2, le=128 * 1024**2)
    max_points: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_numeric_bytes: int = Field(default=80, ge=1, le=256)


class WaveformInputs(StrictModel):
    preamble_before: bytes
    waveform: bytes
    preamble_after: bytes


class WaveformEvidence(WaveformInputs):
    preamble_before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    waveform_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preamble_after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def read(cls, inputs: WaveformInputs) -> "WaveformEvidence":
        return cls(
            preamble_before=inputs.preamble_before,
            waveform=inputs.waveform,
            preamble_after=inputs.preamble_after,
            preamble_before_sha256=hashlib.sha256(inputs.preamble_before).hexdigest(),
            waveform_sha256=hashlib.sha256(inputs.waveform).hexdigest(),
            preamble_after_sha256=hashlib.sha256(inputs.preamble_after).hexdigest(),
        )


class WaveformPreamble(StrictModel):
    format: WaveformFormat
    mode: WaveformMode
    points: int = Field(ge=1, le=10_000_000)
    acquisition_count: int = Field(ge=1, le=2**31 - 1)
    x_increment_s: float = Field(gt=0, lt=1e30)
    x_origin_s: float = Field(gt=-1e30, lt=1e30)
    x_reference: float = Field(gt=-1e30, lt=1e30)
    y_increment: float = Field(gt=0, lt=1e30)
    y_origin: float = Field(gt=-1e30, lt=1e30)
    y_reference: float = Field(gt=-1e30, lt=1e30)


class ParsedWaveform(StrictModel):
    kind: Literal["parsed"] = "parsed"
    preamble: WaveformPreamble
    volts: tuple[float, ...]
    evidence: WaveformEvidence


class RawAcquisition(StrictModel):
    actual_sample_rate_hz: float = Field(gt=0, lt=1e30)
    memory_points: int = Field(ge=1, le=10_000_000)
    start: int = Field(ge=1, le=10_000_000)
    stop: int = Field(ge=1, le=10_000_000)
    interval_relative_tolerance: float = Field(default=1e-8, ge=0, le=1e-3)

    @model_validator(mode="after")
    def extent(self) -> "RawAcquisition":
        if not self.start <= self.stop <= self.memory_points:
            raise ValueError("selected extent must be ordered within observed memory")
        return self


class RawQualified(StrictModel):
    kind: Literal["raw-qualified"] = "raw-qualified"
    waveform: ParsedWaveform
    acquisition: RawAcquisition
    record_duration_s: float = Field(gt=0)
    first_to_last_span_s: float = Field(ge=0)


class WaveformIssue(StrictModel):
    stage: Literal["input", "preamble", "waveform", "acquisition"]
    code: str
    message: str
    token_index: int | None = Field(default=None, ge=0)


class WaveformRejected(StrictModel):
    kind: Literal["rejected"] = "rejected"
    issue: WaveformIssue
    evidence: WaveformEvidence | None = None


type ParseResult = ParsedWaveform | WaveformRejected
type QualificationResult = RawQualified | WaveformRejected
