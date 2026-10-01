"""Strict immutable sampled-receive contracts; acceptance does not prove physical origin."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mho_waveform import RawQualified, WaveformLimits


class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always", allow_inf_nan=False
    )


class ReceiveProfile(StrictModel):
    """Explicit engineering criteria; defaults are the admitted survey profile."""

    name: Literal["mho-rf.raw-receive/1"] = "mho-rf.raw-receive/1"
    window: Literal["periodic-hann"] = "periodic-hann"
    mean_removal: Literal["arithmetic"] = "arithmetic"
    points: int = Field(default=100_000, ge=8, le=1_000_000)
    acquisition_count: int = Field(default=1, ge=1, le=2**31 - 1)
    sample_rate_hz: float = Field(default=4e9, gt=0, lt=1e30)
    rate_relative_tolerance: float = Field(default=1e-8, ge=0, le=1e-3)
    band_lower_ratio: float = Field(default=0.5, gt=0, le=1)
    band_upper_ratio: float = Field(default=1.5, ge=1, le=4)
    peak_relative_tolerance: float = Field(default=0.01, ge=0, le=0.1)
    minimum_energy_fraction: float = Field(default=0.2, gt=0, le=1)
    neighbor_bins: int = Field(default=2, ge=0, le=16)
    peak_tie_relative_tolerance: float = Field(default=1e-12, ge=0, le=1e-6)
    maximum_abs_voltage_v: float = Field(default=0.18, gt=0, lt=1e30)
    minimum_vpp_v: float = Field(default=0.005, ge=0, lt=1e30)
    maximum_vpp_v: float = Field(default=0.36, gt=0, lt=1e30)

    @model_validator(mode="after")
    def ordered_bounds(self) -> "ReceiveProfile":
        if self.band_lower_ratio >= self.band_upper_ratio:
            raise ValueError("receive search band must be ordered")
        if self.minimum_vpp_v >= self.maximum_vpp_v:
            raise ValueError("receive voltage bounds must be ordered")
        return self


class ReceiveRequest(StrictModel):
    record: RawQualified
    command_frequency_hz: float = Field(gt=0, lt=1e30)
    profile: ReceiveProfile = Field(default_factory=ReceiveProfile)
    limits: WaveformLimits = Field(default_factory=WaveformLimits)


class ReceiveHashes(StrictModel):
    preamble_before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    waveform_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preamble_after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReceiveInput(StrictModel):
    points: int = Field(ge=1)
    actual_sample_rate_hz: float = Field(gt=0)
    memory_points: int = Field(ge=1)
    start: int = Field(ge=1)
    stop: int = Field(ge=1)
    x_increment_s: float = Field(gt=0)
    record_duration_s: float = Field(gt=0)
    first_to_last_span_s: float = Field(ge=0)
    voltage_min_v: float
    voltage_max_v: float
    voltage_vpp_v: float = Field(ge=0)
    removed_mean_v: float


class PeakSelection(StrictModel):
    bin: int = Field(ge=1)
    tie_bins: tuple[int, ...]


class ReceiveSpectrum(StrictModel):
    selected_peak_bin: int = Field(ge=1)
    global_peak_bin: int = Field(ge=1)
    selected_peak_frequency_hz: float = Field(gt=0)
    global_peak_frequency_hz: float = Field(gt=0)
    fft_bin_spacing_hz: float = Field(gt=0)
    energy_fraction: float = Field(ge=0, le=1)
    selected_peak_tie_bins: tuple[int, ...]
    global_peak_tie_bins: tuple[int, ...]


type ReceiveStage = Literal["input", "raw", "profile", "range", "spectrum", "receive"]


class ReceiveIssue(StrictModel):
    stage: ReceiveStage
    code: str
    message: str
    token_index: int | None = Field(default=None, ge=0)


class ReceiveQualified(StrictModel):
    kind: Literal["receive-qualified"] = "receive-qualified"
    command_frequency_hz: float = Field(gt=0)
    profile: ReceiveProfile
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hashes: ReceiveHashes
    input: ReceiveInput
    spectrum: ReceiveSpectrum


class ReceiveRejected(StrictModel):
    kind: Literal["receive-rejected"] = "receive-rejected"
    issue: ReceiveIssue
    command_frequency_hz: float | None = None
    profile: ReceiveProfile | None = None
    profile_sha256: str | None = None
    hashes: ReceiveHashes | None = None
    input: ReceiveInput | None = None
    spectrum: ReceiveSpectrum | None = None


type ReceiveResult = ReceiveQualified | ReceiveRejected
