"""Pure periodic-Hann sampled-frequency guard; no files, transport or amplitude estimator."""

import hashlib
import math

import numpy as np
from numpy.typing import NDArray
from pydantic import ValidationError

from mho_waveform import RawQualified, WaveformEvidence, WaveformRejected, qualify_raw

from .models import (
    PeakSelection,
    ReceiveHashes,
    ReceiveInput,
    ReceiveIssue,
    ReceiveProfile,
    ReceiveQualified,
    ReceiveRejected,
    ReceiveRequest,
    ReceiveResult,
    ReceiveSpectrum,
    ReceiveStage,
)


def profile_hash(profile: ReceiveProfile) -> str:
    """Hash the validated profile's field-ordered Pydantic JSON bytes, including defaults."""
    profile = ReceiveProfile.model_validate(profile)
    return hashlib.sha256(profile.model_dump_json().encode("utf-8")).hexdigest()


def _strongest(
    energy: NDArray[np.float64], eligible: NDArray[np.int64], tolerance: float
) -> PeakSelection:
    maximum = float(np.max(energy[eligible]))
    tied = eligible[energy[eligible] >= maximum * (1 - tolerance)]
    selected = int(tied[0])
    return PeakSelection(
        bin=selected, tie_bins=tuple(int(index) for index in tied) if tied.size > 1 else ()
    )


def _hashes(evidence: WaveformEvidence) -> ReceiveHashes:
    return ReceiveHashes(
        preamble_before_sha256=evidence.preamble_before_sha256,
        waveform_sha256=evidence.waveform_sha256,
        preamble_after_sha256=evidence.preamble_after_sha256,
    )


def qualify_receive(request: ReceiveRequest) -> ReceiveResult:
    """Rebind the full RAW evidence, then qualify a dominant sampled component near command.

    Frequency bins inherit the supplied sampling interval. Acceptance proves neither
    physical frequency origin, calibrated amplitude nor validity of a later fitted model.
    """
    try:
        request = ReceiveRequest.model_validate(request)
    except ValidationError:
        return ReceiveRejected(
            issue=ReceiveIssue(
                stage="input", code="invalid-contract", message="receive request invalid"
            )
        )
    profile = request.profile
    digest = profile_hash(profile)
    rebound = qualify_raw(request.record.waveform, request.record.acquisition, request.limits)
    if isinstance(rebound, WaveformRejected):
        return ReceiveRejected(
            command_frequency_hz=request.command_frequency_hz,
            profile=profile,
            profile_sha256=digest,
            hashes=_hashes(rebound.evidence) if rebound.evidence is not None else None,
            issue=ReceiveIssue(
                stage="raw",
                code=rebound.issue.code,
                message=rebound.issue.message,
                token_index=rebound.issue.token_index,
            ),
        )
    if rebound != request.record:
        return ReceiveRejected(
            command_frequency_hz=request.command_frequency_hz,
            profile=profile,
            profile_sha256=digest,
            hashes=_hashes(rebound.waveform.evidence),
            issue=ReceiveIssue(
                stage="raw",
                code="raw-evidence-mismatch",
                message="full raw qualification must match rebound bytes and observations",
            ),
        )
    return _inspect_rebound(rebound, request.command_frequency_hz, profile, digest)


def _inspect_rebound(
    record: RawQualified, command: float, profile: ReceiveProfile, digest: str
) -> ReceiveResult:
    """Internal operation on a fully rebound record."""
    p = record.waveform.preamble
    acquisition = record.acquisition
    evidence = record.waveform.evidence
    hashes = _hashes(evidence)
    y = np.array(record.waveform.volts, dtype=np.float64)
    minimum = float(np.min(y))
    maximum = float(np.max(y))
    mean = float(np.mean(y))
    inputs = ReceiveInput(
        points=p.points,
        actual_sample_rate_hz=acquisition.actual_sample_rate_hz,
        memory_points=acquisition.memory_points,
        start=acquisition.start,
        stop=acquisition.stop,
        x_increment_s=p.x_increment_s,
        record_duration_s=record.record_duration_s,
        first_to_last_span_s=record.first_to_last_span_s,
        voltage_min_v=minimum,
        voltage_max_v=maximum,
        voltage_vpp_v=maximum - minimum,
        removed_mean_v=mean,
    )

    def reject(stage: ReceiveStage, code: str, message: str) -> ReceiveRejected:
        return ReceiveRejected(
            command_frequency_hz=command,
            profile=profile,
            profile_sha256=digest,
            hashes=hashes,
            input=inputs,
            issue=ReceiveIssue(stage=stage, code=code, message=message),
        )

    if not (
        p.points == profile.points == acquisition.memory_points == acquisition.stop
        and acquisition.start == 1
        and p.acquisition_count == profile.acquisition_count
    ):
        return reject("profile", "geometry", "full raw record differs from receive geometry")
    observed_rate = 1 / p.x_increment_s
    if not (
        math.isclose(observed_rate, profile.sample_rate_hz, rel_tol=profile.rate_relative_tolerance)
        and math.isclose(
            acquisition.actual_sample_rate_hz,
            profile.sample_rate_hz,
            rel_tol=profile.rate_relative_tolerance,
        )
    ):
        return reject("profile", "sample-rate", "raw sample rate differs from receive profile")
    if max(abs(minimum), abs(maximum)) >= profile.maximum_abs_voltage_v:
        return reject("range", "voltage-range", "raw extrema reach or exceed voltage guard")
    if not profile.minimum_vpp_v < maximum - minimum < profile.maximum_vpp_v:
        return reject("range", "vpp-range", "raw peak-to-peak voltage fails receive range")
    n = p.points
    spacing = observed_rate / n
    lower = command * profile.band_lower_ratio
    upper = command * profile.band_upper_ratio
    nyquist = observed_rate / 2
    if not (math.isfinite(lower) and math.isfinite(upper) and 0 < lower < upper <= nyquist):
        return reject(
            "profile", "search-band", "search band must lie within sampled Nyquist extent"
        )
    frequencies = np.fft.rfftfreq(n, d=p.x_increment_s)
    eligible = np.flatnonzero((frequencies >= lower) & (frequencies <= upper) & (frequencies > 0))
    if eligible.size == 0:
        return reject("profile", "empty-band", "search band contains no non-DC FFT bin")
    indices = np.arange(n, dtype=np.float64)
    window = 0.5 - 0.5 * np.cos(2 * np.pi * indices / n)
    transformed = np.fft.rfft(window * (y - mean))
    energy = np.abs(transformed) ** 2
    energy[1:] *= 2
    if n % 2 == 0:
        energy[-1] *= 0.5
    total = float(np.sum(energy[1:]))
    if not math.isfinite(total) or total <= 0 or not np.all(np.isfinite(energy)):
        return reject("spectrum", "non-dc-energy", "finite positive non-DC energy required")
    selected = _strongest(energy, eligible, profile.peak_tie_relative_tolerance)
    global_peak = _strongest(
        energy, np.arange(1, energy.size, dtype=np.int64), profile.peak_tie_relative_tolerance
    )
    left = max(1, selected.bin - profile.neighbor_bins)
    right = min(energy.size, selected.bin + profile.neighbor_bins + 1)
    fraction = min(1.0, float(np.sum(energy[left:right])) / total)
    spectrum = ReceiveSpectrum(
        selected_peak_bin=selected.bin,
        global_peak_bin=global_peak.bin,
        selected_peak_frequency_hz=float(frequencies[selected.bin]),
        global_peak_frequency_hz=float(frequencies[global_peak.bin]),
        fft_bin_spacing_hz=spacing,
        energy_fraction=fraction,
        selected_peak_tie_bins=selected.tie_bins,
        global_peak_tie_bins=global_peak.tie_bins,
    )
    issue: ReceiveIssue | None = None
    frequency_limit = command * profile.peak_relative_tolerance
    if abs(spectrum.selected_peak_frequency_hz - command) > frequency_limit:
        issue = ReceiveIssue(
            stage="receive",
            code="band-peak-frequency",
            message="selected band peak differs from command",
        )
    elif abs(spectrum.global_peak_frequency_hz - command) > frequency_limit:
        issue = ReceiveIssue(
            stage="receive",
            code="global-peak-frequency",
            message="global peak differs from command",
        )
    elif fraction < profile.minimum_energy_fraction:
        issue = ReceiveIssue(
            stage="receive",
            code="energy-fraction",
            message="peak neighborhood lacks required non-DC energy fraction",
        )
    if issue is not None:
        return ReceiveRejected(
            command_frequency_hz=command,
            profile=profile,
            profile_sha256=digest,
            hashes=hashes,
            input=inputs,
            spectrum=spectrum,
            issue=issue,
        )
    return ReceiveQualified(
        command_frequency_hz=command,
        profile=profile,
        profile_sha256=digest,
        hashes=hashes,
        input=inputs,
        spectrum=spectrum,
    )
