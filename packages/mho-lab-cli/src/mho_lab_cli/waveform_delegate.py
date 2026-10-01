"""Bounded supplied-file reads and offline waveform qualification."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mho_waveform import (
    QualificationResult,
    RawAcquisition,
    WaveformInputs,
    WaveformLimits,
    WaveformRejected,
    parse_ascii,
    qualify_raw,
)

from .inputs import read_bounded_regular


class WaveformInspectionRequest(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always"
    )
    preamble_before: Path
    waveform: Path
    preamble_after: Path
    acquisition: RawAcquisition
    limits: WaveformLimits = Field(default_factory=WaveformLimits)


@dataclass(frozen=True)
class WaveformInputRejected:
    message: str
    kind: Literal["input-rejected"] = "input-rejected"


type WaveformInspectionResult = QualificationResult | WaveformInputRejected


def inspect_waveform(request: WaveformInspectionRequest) -> WaveformInspectionResult:
    try:
        request = WaveformInspectionRequest.model_validate(request)
    except ValidationError:
        return WaveformInputRejected("inspection request violates the contract")
    try:
        inputs = WaveformInputs(
            preamble_before=read_bounded_regular(
                request.preamble_before, request.limits.max_preamble_bytes
            ),
            waveform=read_bounded_regular(request.waveform, request.limits.max_waveform_bytes),
            preamble_after=read_bounded_regular(
                request.preamble_after, request.limits.max_preamble_bytes
            ),
        )
    except (OSError, ValueError):
        return WaveformInputRejected("cannot read bounded, unchanged regular waveform files")
    parsed = parse_ascii(inputs, request.limits)
    if isinstance(parsed, WaveformRejected):
        return parsed
    return qualify_raw(parsed, request.acquisition, request.limits)
