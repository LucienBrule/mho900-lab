"""Pure original-voltage AC statistics, independent of receive or experiment gates."""

import math

import numpy as np
from pydantic import ValidationError

from mho_waveform import WaveformEvidence, WaveformRejected, qualify_raw

from .statistics_models import (
    RawAcMetrics,
    RawAcStatistics,
    RawAcStatisticsRequest,
    RawStatisticsEvidence,
    RawStatisticsGeometry,
    RawStatisticsIssue,
    RawStatisticsRejected,
    RawStatisticsResult,
)


def _evidence(source: WaveformEvidence) -> RawStatisticsEvidence:
    return RawStatisticsEvidence(
        preamble_before_sha256=source.preamble_before_sha256,
        waveform_sha256=source.waveform_sha256,
        preamble_after_sha256=source.preamble_after_sha256,
    )


def _metrics(volts: tuple[float, ...]) -> RawAcMetrics | RawStatisticsIssue:
    y = np.array(volts, dtype=np.float64)
    minimum = float(np.min(y))
    maximum = float(np.max(y))
    constant = minimum == maximum
    mean_underflow = False
    if constant:
        mean = minimum
        rms = 0.0
    else:
        # Shifting before scaling retains small differences on a large DC offset.
        # Scaling before squaring prevents tiny but varying volts from disappearing.
        differences = y - y[0]
        scale = float(np.max(np.abs(differences)))
        normalized = differences / scale
        normalized_mean = math.fsum(float(value) for value in normalized) / y.size
        centered = normalized - normalized_mean
        normalized_rms = math.sqrt(math.fsum(float(value * value) for value in centered) / y.size)
        rms = scale * normalized_rms
        dc_sum = math.fsum(volts)
        mean = dc_sum / y.size
        mean_underflow = dc_sum != 0.0 and mean == 0.0
    vpp = maximum - minimum
    if (
        not all(math.isfinite(value) for value in (mean, rms, vpp))
        or (not constant and rms == 0.0)
        or mean_underflow
    ):
        return RawStatisticsIssue(
            stage="numerical",
            code="unrepresentable-metrics",
            message="varying AC RMS or nonzero arithmetic DC underflows representable binary64",
        )
    return RawAcMetrics(
        dc_mean_v=mean,
        voltage_min_v=minimum,
        voltage_max_v=maximum,
        voltage_vpp_v=vpp,
        ac_rms_v=rms,
        constant_samples=constant,
        zero_sampled_ac=constant,
    )


def measure_raw_ac(request: RawAcStatisticsRequest) -> RawStatisticsResult:
    """Rebind complete RAW evidence and return unwindowed population AC statistics.

    Supplied acquisition observations do not prove freshness or physical origin.
    Statistics include every retained sampled AC contribution; they do not isolate
    a carrier, calibrate amplitude or apply a receive or engineering threshold.
    """
    try:
        request = RawAcStatisticsRequest.model_validate(request)
    except ValidationError:
        return RawStatisticsRejected(
            issue=RawStatisticsIssue(
                stage="input", code="invalid-contract", message="statistics request invalid"
            )
        )
    rebound = qualify_raw(request.record.waveform, request.record.acquisition, request.limits)
    if isinstance(rebound, WaveformRejected):
        return RawStatisticsRejected(
            evidence=_evidence(rebound.evidence) if rebound.evidence is not None else None,
            issue=RawStatisticsIssue(
                stage="raw",
                code=rebound.issue.code,
                message=rebound.issue.message,
                token_index=rebound.issue.token_index,
            ),
        )
    evidence = _evidence(rebound.waveform.evidence)
    if rebound != request.record:
        return RawStatisticsRejected(
            evidence=evidence,
            issue=RawStatisticsIssue(
                stage="raw",
                code="raw-evidence-mismatch",
                message="full raw qualification must match rebound bytes and observations",
            ),
        )
    # Existing decoding yields binary64 volts. Reject a nonzero decimal token
    # rounded to zero here, without changing the waveform/receive decoder contract.
    tokens = rebound.waveform.evidence.waveform.rstrip(b"\r\n").split(b",")
    for index, token in enumerate(tokens):
        mantissa = token.lower().split(b"e", 1)[0]
        if rebound.waveform.volts[index] == 0.0 and any(
            value in b"123456789" for value in mantissa
        ):
            return RawStatisticsRejected(
                evidence=evidence,
                issue=RawStatisticsIssue(
                    stage="numerical",
                    code="unrepresentable-samples",
                    message="nonzero original decimal sample underflows binary64 volts",
                    token_index=index,
                ),
            )
    metrics = _metrics(rebound.waveform.volts)
    if isinstance(metrics, RawStatisticsIssue):
        return RawStatisticsRejected(evidence=evidence, issue=metrics)
    p = rebound.waveform.preamble
    acquisition = rebound.acquisition
    geometry = RawStatisticsGeometry(
        points=p.points,
        acquisition_count=p.acquisition_count,
        memory_points=acquisition.memory_points,
        start=acquisition.start,
        stop=acquisition.stop,
        actual_sample_rate_hz=acquisition.actual_sample_rate_hz,
        interval_sample_rate_hz=1 / p.x_increment_s,
        interval_relative_tolerance=acquisition.interval_relative_tolerance,
        x_increment_s=p.x_increment_s,
        record_duration_s=rebound.record_duration_s,
        first_to_last_span_s=rebound.first_to_last_span_s,
    )
    return RawAcStatistics(evidence=evidence, geometry=geometry, metrics=metrics)
