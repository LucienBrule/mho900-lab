"""Bounded supplied-file composition of original RAW AC statistics."""

from pydantic import ValidationError

from mho_rf import (
    RawAcStatisticsRequest,
    RawStatisticsEvidence,
    RawStatisticsIssue,
    RawStatisticsRejected,
    RawStatisticsResult,
    measure_raw_ac,
)
from mho_waveform import WaveformRejected

from .waveform_delegate import WaveformInputRejected, WaveformInspectionRequest, inspect_waveform


def inspect_raw_ac(request: WaveformInspectionRequest) -> RawStatisticsResult:
    try:
        request = WaveformInspectionRequest.model_validate(request)
    except ValidationError:
        return RawStatisticsRejected(
            issue=RawStatisticsIssue(
                stage="input", code="invalid-contract", message="statistics inspection invalid"
            )
        )
    waveform = inspect_waveform(request)
    if isinstance(waveform, WaveformInputRejected):
        return RawStatisticsRejected(
            issue=RawStatisticsIssue(stage="input", code="input-files", message=waveform.message)
        )
    if isinstance(waveform, WaveformRejected):
        source = waveform.evidence
        evidence = (
            None
            if source is None
            else RawStatisticsEvidence(
                preamble_before_sha256=source.preamble_before_sha256,
                waveform_sha256=source.waveform_sha256,
                preamble_after_sha256=source.preamble_after_sha256,
            )
        )
        return RawStatisticsRejected(
            evidence=evidence,
            issue=RawStatisticsIssue(
                stage="raw",
                code=waveform.issue.code,
                message=waveform.issue.message,
                token_index=waveform.issue.token_index,
            ),
        )
    return measure_raw_ac(RawAcStatisticsRequest(record=waveform, limits=request.limits))
