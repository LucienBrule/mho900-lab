"""Offline supplied-file composition of RAW evidence and sampled receive qualification."""

from pydantic import Field, ValidationError

from mho_rf import (
    ReceiveHashes,
    ReceiveIssue,
    ReceiveProfile,
    ReceiveRejected,
    ReceiveRequest,
    ReceiveResult,
    profile_hash,
)
from mho_rf import qualify_receive as qualify_record
from mho_waveform import WaveformRejected

from .waveform_delegate import (
    WaveformInputRejected,
    WaveformInspectionRequest,
    inspect_waveform,
)


class ReceiveInspectionRequest(WaveformInspectionRequest):
    command_frequency_hz: float = Field(gt=0, lt=1e30)
    profile: ReceiveProfile = Field(default_factory=ReceiveProfile)


def inspect_receive(request: ReceiveInspectionRequest) -> ReceiveResult:
    try:
        request = ReceiveInspectionRequest.model_validate(request)
    except ValidationError:
        return ReceiveRejected(
            issue=ReceiveIssue(
                stage="input", code="invalid-contract", message="receive inspection invalid"
            )
        )
    waveform = inspect_waveform(
        WaveformInspectionRequest(
            preamble_before=request.preamble_before,
            waveform=request.waveform,
            preamble_after=request.preamble_after,
            acquisition=request.acquisition,
            limits=request.limits,
        )
    )
    if isinstance(waveform, WaveformInputRejected):
        return ReceiveRejected(
            command_frequency_hz=request.command_frequency_hz,
            profile=request.profile,
            profile_sha256=profile_hash(request.profile),
            issue=ReceiveIssue(stage="input", code="input-files", message=waveform.message),
        )
    if isinstance(waveform, WaveformRejected):
        hashes: ReceiveHashes | None = None
        if waveform.evidence is not None:
            evidence = waveform.evidence
            hashes = ReceiveHashes(
                preamble_before_sha256=evidence.preamble_before_sha256,
                waveform_sha256=evidence.waveform_sha256,
                preamble_after_sha256=evidence.preamble_after_sha256,
            )
        return ReceiveRejected(
            command_frequency_hz=request.command_frequency_hz,
            profile=request.profile,
            profile_sha256=profile_hash(request.profile),
            hashes=hashes,
            issue=ReceiveIssue(
                stage="raw",
                code=waveform.issue.code,
                message=waveform.issue.message,
                token_index=waveform.issue.token_index,
            ),
        )
    return qualify_record(
        ReceiveRequest(
            record=waveform,
            command_frequency_hz=request.command_frequency_hz,
            profile=request.profile,
            limits=request.limits,
        )
    )
