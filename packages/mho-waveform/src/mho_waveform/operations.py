"""Pure bounded parsing and qualification; no files, transport or numerical estimator."""

import math
import re
from typing import Literal

from pydantic import ValidationError

from .models import (
    ParsedWaveform,
    ParseResult,
    QualificationResult,
    RawAcquisition,
    RawQualified,
    WaveformEvidence,
    WaveformFormat,
    WaveformInputs,
    WaveformIssue,
    WaveformLimits,
    WaveformMode,
    WaveformPreamble,
    WaveformRejected,
)

DEFAULT_LIMITS = WaveformLimits()
NUMBER = re.compile(rb"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?")
INTEGER = re.compile(rb"[0-9]+")
type LiteralStage = Literal["preamble", "waveform"]


class BoundaryFailure(Exception):
    def __init__(self, issue: WaveformIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def require(condition: bool, issue: WaveformIssue) -> None:
    if not condition:
        raise BoundaryFailure(issue)


def line(raw: bytes, stage: LiteralStage) -> bytes:
    require(
        raw.endswith(b"\n") and raw.count(b"\n") == 1,
        WaveformIssue(
            stage=stage, code="line-framing", message="one exact LF or CRLF line required"
        ),
    )
    body = raw[:-2] if raw.endswith(b"\r\n") else raw[:-1]
    require(
        all(32 <= value <= 126 for value in body),
        WaveformIssue(stage=stage, code="non-ascii", message="printable ASCII line required"),
    )
    return body


def numeric(token: bytes, stage: LiteralStage, index: int, limits: WaveformLimits) -> float:
    require(
        0 < len(token) <= limits.max_numeric_bytes and NUMBER.fullmatch(token) is not None,
        WaveformIssue(
            stage=stage,
            code="numeric-token",
            message="bounded decimal number required",
            token_index=index,
        ),
    )
    value = float(token)
    require(
        math.isfinite(value) and abs(value) < 1e30,
        WaveformIssue(
            stage=stage,
            code="nonfinite-or-sentinel",
            message="finite nonsentinel number required",
            token_index=index,
        ),
    )
    return value


def integer(token: bytes, index: int, limits: WaveformLimits) -> int:
    require(
        0 < len(token) <= limits.max_numeric_bytes and INTEGER.fullmatch(token) is not None,
        WaveformIssue(
            stage="preamble",
            code="integer-token",
            message="unsigned decimal integer required",
            token_index=index,
        ),
    )
    return int(token)


def preamble(raw: bytes, limits: WaveformLimits) -> WaveformPreamble:
    fields = line(raw, "preamble").split(b",")
    require(
        len(fields) == 10,
        WaveformIssue(stage="preamble", code="field-count", message="ten preamble fields required"),
    )
    try:
        result = WaveformPreamble(
            format=WaveformFormat(integer(fields[0], 0, limits)),
            mode=WaveformMode(integer(fields[1], 1, limits)),
            points=integer(fields[2], 2, limits),
            acquisition_count=integer(fields[3], 3, limits),
            x_increment_s=numeric(fields[4], "preamble", 4, limits),
            x_origin_s=numeric(fields[5], "preamble", 5, limits),
            x_reference=numeric(fields[6], "preamble", 6, limits),
            y_increment=numeric(fields[7], "preamble", 7, limits),
            y_origin=numeric(fields[8], "preamble", 8, limits),
            y_reference=numeric(fields[9], "preamble", 9, limits),
        )
    except ValueError as error:
        raise BoundaryFailure(
            WaveformIssue(
                stage="preamble",
                code="preamble-values",
                message="format, mode, count or preamble values violate the contract",
            )
        ) from error
    require(
        result.format is WaveformFormat.ASCII,
        WaveformIssue(stage="preamble", code="unsupported-format", message="ASCII format required"),
    )
    require(
        result.points <= limits.max_points,
        WaveformIssue(stage="preamble", code="point-limit", message="preamble exceeds point limit"),
    )
    return result


def parse_ascii(inputs: WaveformInputs, limits: WaveformLimits = DEFAULT_LIMITS) -> ParseResult:
    """Parse supplied line evidence exactly; ASCII sample values already represent volts."""
    evidence: WaveformEvidence | None = None
    try:
        inputs = WaveformInputs.model_validate(inputs)
        limits = WaveformLimits.model_validate(limits)
    except ValidationError:
        return WaveformRejected(
            issue=WaveformIssue(
                stage="input",
                code="invalid-contract",
                message="inputs or limits violate the contract",
            )
        )
    try:
        require(
            0 < len(inputs.preamble_before) <= limits.max_preamble_bytes
            and 0 < len(inputs.preamble_after) <= limits.max_preamble_bytes
            and 0 < len(inputs.waveform) <= limits.max_waveform_bytes,
            WaveformIssue(stage="input", code="byte-limit", message="input exceeds byte bounds"),
        )
        evidence = WaveformEvidence.read(inputs)
        require(
            inputs.preamble_before == inputs.preamble_after,
            WaveformIssue(
                stage="preamble",
                code="preamble-changed",
                message="before and after preamble bytes must match exactly",
            ),
        )
        metadata = preamble(inputs.preamble_before, limits)
        body = line(inputs.waveform, "waveform")
        require(
            body.count(b",") + 1 == metadata.points,
            WaveformIssue(
                stage="waveform",
                code="sample-count",
                message="sample count must equal preamble points",
            ),
        )
        values = tuple(
            numeric(token, "waveform", index, limits)
            for index, token in enumerate(body.split(b","))
        )
        return ParsedWaveform(preamble=metadata, volts=values, evidence=evidence)
    except BoundaryFailure as error:
        return WaveformRejected(issue=error.issue, evidence=evidence)


def qualify_raw(
    waveform: ParsedWaveform,
    acquisition: RawAcquisition,
    limits: WaveformLimits = DEFAULT_LIMITS,
) -> QualificationResult:
    """Qualify a parsed record against explicit observations; no physical origin proof."""
    try:
        waveform = ParsedWaveform.model_validate(waveform)
        acquisition = RawAcquisition.model_validate(acquisition)
        limits = WaveformLimits.model_validate(limits)
    except ValidationError:
        return WaveformRejected(
            issue=WaveformIssue(
                stage="input",
                code="invalid-contract",
                message="parsed record or observations invalid",
            )
        )
    # Rebind public parsed models to retained evidence rather than trusting model_copy/construct.
    parsed = parse_ascii(
        WaveformInputs(
            preamble_before=waveform.evidence.preamble_before,
            waveform=waveform.evidence.waveform,
            preamble_after=waveform.evidence.preamble_after,
        ),
        limits,
    )
    if isinstance(parsed, WaveformRejected):
        return parsed
    if parsed != waveform:
        return WaveformRejected(
            issue=WaveformIssue(
                stage="input",
                code="parsed-evidence-mismatch",
                message="parsed record must match its exact retained evidence",
            ),
            evidence=parsed.evidence,
        )
    try:
        require(
            parsed.preamble.mode is WaveformMode.RAW,
            WaveformIssue(
                stage="acquisition",
                code="not-raw",
                message="display or maximum-mode samples are not raw qualification",
            ),
        )
        require(
            parsed.preamble.points == acquisition.stop - acquisition.start + 1,
            WaveformIssue(
                stage="acquisition",
                code="extent-count",
                message="selected extent must equal retained sample count",
            ),
        )
        rate_product = parsed.preamble.x_increment_s * acquisition.actual_sample_rate_hz
        require(
            math.isfinite(rate_product)
            and abs(rate_product - 1) <= acquisition.interval_relative_tolerance,
            WaveformIssue(
                stage="acquisition",
                code="interval-rate",
                message="raw interval disagrees with observed acquisition rate",
            ),
        )
        return RawQualified(
            waveform=parsed,
            acquisition=acquisition,
            record_duration_s=parsed.preamble.points * parsed.preamble.x_increment_s,
            first_to_last_span_s=(parsed.preamble.points - 1) * parsed.preamble.x_increment_s,
        )
    except BoundaryFailure as error:
        return WaveformRejected(issue=error.issue, evidence=parsed.evidence)
