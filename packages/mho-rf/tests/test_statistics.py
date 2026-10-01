"""Original RAW statistical controls, evidence binding and numerical boundaries."""

import hashlib
import math
import statistics
from dataclasses import dataclass

import numpy as np
import pytest
from pydantic import ValidationError

from mho_rf import (
    RawAcMetrics,
    RawAcStatistics,
    RawAcStatisticsRequest,
    RawStatisticsGeometry,
    RawStatisticsRejected,
    measure_raw_ac,
)
from mho_waveform import (
    ParsedWaveform,
    RawAcquisition,
    RawQualified,
    WaveformInputs,
    parse_ascii,
    qualify_raw,
)


def record(volts: tuple[float, ...], start: int = 1, count: int = 1) -> RawQualified:
    preamble = f"2,2,{len(volts)},{count},2.5e-10,0,0,6e-6,0,32768\n".encode()
    parsed = parse_ascii(
        WaveformInputs(
            preamble_before=preamble,
            waveform=(",".join(f"{v:.17g}" for v in volts) + "\n").encode(),
            preamble_after=preamble,
        )
    )
    assert isinstance(parsed, ParsedWaveform)
    raw = qualify_raw(
        parsed,
        RawAcquisition(
            actual_sample_rate_hz=4e9,
            memory_points=start + len(volts) - 1,
            start=start,
            stop=start + len(volts) - 1,
        ),
    )
    assert isinstance(raw, RawQualified)
    return raw


def measured(volts: tuple[float, ...]) -> RawAcStatistics:
    result = measure_raw_ac(RawAcStatisticsRequest(record=record(volts)))
    assert isinstance(result, RawAcStatistics)
    return result


def test_known_sine_dc_geometry_and_original_hashes() -> None:
    n = 1024
    volts = tuple(0.011 + 0.12 * math.sin(2 * math.pi * index / 8) for index in range(n))
    raw = record(volts)
    before = raw.model_dump_json()
    result = measure_raw_ac(RawAcStatisticsRequest(record=raw))
    assert isinstance(result, RawAcStatistics)
    assert result.metrics.dc_mean_v == pytest.approx(0.011, abs=1e-14)
    assert result.metrics.ac_rms_v == pytest.approx(0.12 / math.sqrt(2), abs=1e-14)
    assert result.metrics.voltage_vpp_v == pytest.approx(0.24, abs=1e-14)
    assert result.geometry.points == n
    assert result.geometry.record_duration_s == n / 4e9
    assert result.geometry.first_to_last_span_s == (n - 1) / 4e9
    assert (
        result.evidence.waveform_sha256
        == hashlib.sha256(raw.waveform.evidence.waveform).hexdigest()
    )
    assert raw.model_dump_json() == before


def test_off_bin_matches_finite_sample_population_statistic() -> None:
    volts = tuple(0.031 + 0.07 * math.sin(2 * math.pi * 0.17321 * index) for index in range(701))
    result = measured(volts)
    assert result.metrics.dc_mean_v == pytest.approx(statistics.fmean(volts), abs=1e-15)
    assert result.metrics.ac_rms_v == pytest.approx(statistics.pstdev(volts), rel=1e-14)
    assert result.metrics.ac_rms_v != pytest.approx(0.07 / math.sqrt(2), rel=1e-8)


def test_nonsinusoidal_population_and_no_engineering_gate() -> None:
    result = measured((-0.25, 0.25, 0.25, 0.75))
    assert result.metrics.dc_mean_v == 0.25
    assert result.metrics.ac_rms_v == pytest.approx(math.sqrt(0.125))
    assert result.metrics.voltage_vpp_v == 1.0
    # Statistics do not inherit the receive guard's 180mV engineering boundary.
    partial = measure_raw_ac(RawAcStatisticsRequest(record=record((0.25, 0.5), start=10, count=3)))
    assert isinstance(partial, RawAcStatistics)
    assert partial.geometry.start == 10 and partial.geometry.stop == 11
    assert partial.geometry.acquisition_count == 3


@pytest.mark.parametrize("value", [0.0, 0.1, -0.031, math.ulp(0.0)])
def test_constants_preserve_exact_dc_and_zero(value: float) -> None:
    result = measured((value,) * 7)
    assert result.metrics.dc_mean_v == value
    assert result.metrics.ac_rms_v == 0.0
    assert result.metrics.constant_samples and result.metrics.zero_sampled_ac
    assert result.metrics.voltage_vpp_v == 0.0


@pytest.mark.parametrize("value", [1e-200, 1e-300, math.ulp(0.0)])
def test_tiny_varying_keeps_representable_positive_rms(value: float) -> None:
    result = measured((-value, value) * 4)
    assert result.metrics.ac_rms_v == value
    assert not result.metrics.constant_samples and not result.metrics.zero_sampled_ac
    assert result.metrics.dc_mean_v == 0.0


def test_large_dc_neighboring_floats_preserve_small_ac() -> None:
    high = 1e29
    low = float(np.nextafter(high, -math.inf))
    result = measured((low, high) * 3)
    assert result.metrics.ac_rms_v == (high - low) / 2
    assert result.metrics.dc_mean_v == math.fsum((low, high) * 3) / 6
    assert not result.metrics.constant_samples


def test_unrepresentable_positive_rms_rejected_with_evidence() -> None:
    raw = record((0.0, math.ulp(0.0)))
    result = measure_raw_ac(RawAcStatisticsRequest(record=raw))
    assert isinstance(result, RawStatisticsRejected)
    assert result.issue.stage == "numerical" and result.issue.code == "unrepresentable-metrics"
    assert result.evidence is not None


def test_nonzero_arithmetic_dc_underflow_rejected() -> None:
    tiny = math.ulp(0.0)
    result = measure_raw_ac(RawAcStatisticsRequest(record=record((tiny, -tiny, tiny))))
    assert isinstance(result, RawStatisticsRejected)
    assert result.issue.code == "unrepresentable-metrics"


def test_decimal_rounding_constant_flag_refers_to_decoded_binary64() -> None:
    preamble = b"2,2,2,1,2.5e-10,0,0,6e-6,0,32768\n"
    parsed = parse_ascii(
        WaveformInputs(
            preamble_before=preamble,
            waveform=b"0.1000000000000000001,0.1\n",
            preamble_after=preamble,
        )
    )
    assert isinstance(parsed, ParsedWaveform)
    raw = qualify_raw(
        parsed, RawAcquisition(actual_sample_rate_hz=4e9, memory_points=2, start=1, stop=2)
    )
    assert isinstance(raw, RawQualified)
    result = measure_raw_ac(RawAcStatisticsRequest(record=raw))
    assert isinstance(result, RawAcStatistics)
    assert result.metrics.constant_samples and result.metrics.ac_rms_v == 0.0


def test_original_decimal_underflow_cannot_be_promoted_to_constant() -> None:
    preamble = b"2,2,2,1,2.5e-10,0,0,6e-6,0,32768\n"
    parsed = parse_ascii(
        WaveformInputs(preamble_before=preamble, waveform=b"0,1e-400\n", preamble_after=preamble)
    )
    assert isinstance(parsed, ParsedWaveform)
    raw = qualify_raw(
        parsed, RawAcquisition(actual_sample_rate_hz=4e9, memory_points=2, start=1, stop=2)
    )
    assert isinstance(raw, RawQualified)
    result = measure_raw_ac(RawAcStatisticsRequest(record=raw))
    assert isinstance(result, RawStatisticsRejected)
    assert result.issue.code == "unrepresentable-samples" and result.issue.token_index == 1


@pytest.mark.parametrize(
    "component", ["samples", "preamble", "hash", "rate", "duration", "span", "malformed-bytes"]
)
def test_full_raw_rebound_rejects_forged_components(component: str) -> None:
    raw = record((0.1, -0.1, 0.2, -0.2))
    waveform = raw.waveform
    if component == "samples":
        waveform = waveform.model_copy(update={"volts": (0.0,) * 4})
    elif component == "preamble":
        waveform = waveform.model_copy(
            update={"preamble": waveform.preamble.model_copy(update={"x_origin_s": 1.0})}
        )
    elif component == "hash":
        waveform = waveform.model_copy(
            update={"evidence": waveform.evidence.model_copy(update={"waveform_sha256": "0" * 64})}
        )
    elif component == "malformed-bytes":
        waveform = waveform.model_copy(
            update={"evidence": waveform.evidence.model_copy(update={"waveform": b"PRIVATE,bad\n"})}
        )
    elif component == "rate":
        raw = raw.model_copy(
            update={
                "acquisition": raw.acquisition.model_copy(update={"actual_sample_rate_hz": 2e9})
            }
        )
    elif component == "duration":
        raw = raw.model_copy(update={"record_duration_s": 1.0})
    else:
        raw = raw.model_copy(update={"first_to_last_span_s": 1.0})
    raw = raw.model_copy(update={"waveform": waveform})
    result = measure_raw_ac(RawAcStatisticsRequest(record=raw))
    assert isinstance(result, RawStatisticsRejected) and result.issue.stage == "raw"
    assert "PRIVATE" not in result.issue.message


def test_unchecked_request_limits_revalidated() -> None:
    request = RawAcStatisticsRequest(record=record((0.1, -0.1)))
    result = measure_raw_ac(request.model_copy(update={"limits": None}))
    assert isinstance(result, RawStatisticsRejected) and result.issue.stage == "input"
    assert result.evidence is None


@dataclass(frozen=True)
class MetricMutation:
    field: str
    value: float | bool


@dataclass(frozen=True)
class GeometryMutation:
    field: str
    value: float | int


def test_metrics_and_geometry_models_validate_internal_consistency() -> None:
    result = measured((0.25, 0.5))
    metrics = result.metrics
    geometry = result.geometry
    for mutation in (
        MetricMutation("voltage_vpp_v", 1.0),
        MetricMutation("dc_mean_v", 1.0),
        MetricMutation("constant_samples", True),
        MetricMutation("zero_sampled_ac", True),
        MetricMutation("ac_rms_v", 0.2),
    ):
        with pytest.raises(ValidationError):
            RawAcMetrics.model_validate(metrics.model_copy(update={mutation.field: mutation.value}))
    for geometry_mutation in (
        GeometryMutation("start", 3),
        GeometryMutation("record_duration_s", 1.0),
        GeometryMutation("first_to_last_span_s", 1.0),
        GeometryMutation("interval_sample_rate_hz", 2e9),
    ):
        with pytest.raises(ValidationError):
            RawStatisticsGeometry.model_validate(
                geometry.model_copy(update={geometry_mutation.field: geometry_mutation.value})
            )
