"""Immutable contracts for supplied-RAW population AC statistics."""

import math
from typing import Literal

from pydantic import Field, model_validator

from mho_waveform import RawQualified, WaveformLimits

from .models import StrictModel


class RawAcStatisticsRequest(StrictModel):
    record: RawQualified
    limits: WaveformLimits = Field(default_factory=WaveformLimits)


class RawStatisticsEvidence(StrictModel):
    preamble_before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    waveform_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preamble_after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RawStatisticsGeometry(StrictModel):
    points: int = Field(ge=1)
    acquisition_count: int = Field(ge=1)
    memory_points: int = Field(ge=1)
    start: int = Field(ge=1)
    stop: int = Field(ge=1)
    actual_sample_rate_hz: float = Field(gt=0)
    interval_sample_rate_hz: float = Field(gt=0)
    interval_relative_tolerance: float = Field(ge=0, le=1e-3)
    x_increment_s: float = Field(gt=0)
    record_duration_s: float = Field(gt=0)
    first_to_last_span_s: float = Field(ge=0)

    @model_validator(mode="after")
    def consistent_geometry(self) -> "RawStatisticsGeometry":
        if not self.start <= self.stop <= self.memory_points:
            raise ValueError("extent must lie within observed memory")
        if self.points != self.stop - self.start + 1:
            raise ValueError("extent must match retained point count")
        if self.interval_sample_rate_hz != 1 / self.x_increment_s:
            raise ValueError("interval rate must match retained increment")
        if self.record_duration_s != self.points * self.x_increment_s:
            raise ValueError("duration must match retained point count and increment")
        if self.first_to_last_span_s != (self.points - 1) * self.x_increment_s:
            raise ValueError("span must match retained point count and increment")
        if (
            abs(self.x_increment_s * self.actual_sample_rate_hz - 1)
            > self.interval_relative_tolerance
        ):
            raise ValueError("observed rate must satisfy retained interval tolerance")
        return self


class RawAcMetrics(StrictModel):
    """Constant flags refer to exact equality of decoded binary64 volts."""

    dc_mean_v: float
    voltage_min_v: float
    voltage_max_v: float
    voltage_vpp_v: float = Field(ge=0)
    ac_rms_v: float = Field(ge=0)
    constant_samples: bool
    zero_sampled_ac: bool

    @model_validator(mode="after")
    def zero_semantics(self) -> "RawAcMetrics":
        if not self.voltage_min_v <= self.dc_mean_v <= self.voltage_max_v:
            raise ValueError("arithmetic DC must lie within retained extrema")
        if self.voltage_vpp_v != self.voltage_max_v - self.voltage_min_v:
            raise ValueError("Vpp must match retained extrema")
        if self.constant_samples != (self.voltage_min_v == self.voltage_max_v):
            raise ValueError("constant flag must agree with exact extrema equality")
        bound = self.voltage_vpp_v / 2
        if self.ac_rms_v > bound and not math.isclose(self.ac_rms_v, bound, rel_tol=2e-15):
            raise ValueError("population AC RMS cannot exceed half the voltage span")
        if self.zero_sampled_ac != (self.ac_rms_v == 0.0):
            raise ValueError("zero flag must agree with sampled AC RMS")
        if self.constant_samples != self.zero_sampled_ac:
            raise ValueError("only exact constants have zero accepted AC RMS")
        return self


class RawStatisticsIssue(StrictModel):
    stage: Literal["input", "raw", "numerical"]
    code: str
    message: str
    token_index: int | None = Field(default=None, ge=0)


class RawAcStatistics(StrictModel):
    kind: Literal["raw-ac-statistics"] = "raw-ac-statistics"
    method: Literal["unwindowed-demeaned-population"] = "unwindowed-demeaned-population"
    evidence: RawStatisticsEvidence
    geometry: RawStatisticsGeometry
    metrics: RawAcMetrics


class RawStatisticsRejected(StrictModel):
    kind: Literal["statistics-rejected"] = "statistics-rejected"
    issue: RawStatisticsIssue
    evidence: RawStatisticsEvidence | None = None


type RawStatisticsResult = RawAcStatistics | RawStatisticsRejected
