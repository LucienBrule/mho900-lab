"""Offline receive controls: explicit sampled-frequency and physical-origin limits."""

import math

import numpy as np
import pytest
from numpy.typing import NDArray
from pydantic import ValidationError

from mho_rf import (
    ReceiveProfile,
    ReceiveQualified,
    ReceiveRejected,
    ReceiveRequest,
    profile_hash,
    qualify_receive,
)
from mho_rf.operations import _strongest
from mho_waveform import (
    ParsedWaveform,
    RawAcquisition,
    RawQualified,
    WaveformInputs,
    WaveformMode,
    parse_ascii,
    qualify_raw,
)

RATE = 4e9
POINTS = 100_000


def tone(frequency: float, amplitude: float = 0.12, points: int = POINTS) -> NDArray[np.float64]:
    return amplitude * np.sin(2 * np.pi * frequency * np.arange(points) / RATE)


def supplied(y: NDArray[np.float64], mode: WaveformMode = WaveformMode.RAW) -> RawQualified:
    preamble = f"2,{mode.value},{y.size},1,2.5e-10,0,0,6e-6,0,32768\n".encode()
    inputs = WaveformInputs(
        preamble_before=preamble,
        waveform=(",".join(f"{float(v):.16e}" for v in y) + "\n").encode(),
        preamble_after=preamble,
    )
    parsed = parse_ascii(inputs)
    assert isinstance(parsed, ParsedWaveform)
    acquisition = RawAcquisition(
        actual_sample_rate_hz=RATE, memory_points=y.size, start=1, stop=y.size
    )
    if mode is not WaveformMode.RAW:
        return RawQualified(
            waveform=parsed,
            acquisition=acquisition,
            record_duration_s=y.size / RATE,
            first_to_last_span_s=(y.size - 1) / RATE,
        )
    qualified = qualify_raw(parsed, acquisition)
    assert isinstance(qualified, RawQualified)
    return qualified


def request(y: NDArray[np.float64], command: float = 600e6) -> ReceiveRequest:
    return ReceiveRequest(record=supplied(y), command_frequency_hz=command)


@pytest.mark.parametrize("offset", [0.0, 12345.0, 20000.0])
def test_on_and_off_bin_qualification(offset: float) -> None:
    result = qualify_receive(request(tone(600e6 + offset) + 0.011))
    assert isinstance(result, ReceiveQualified)
    assert abs(result.spectrum.selected_peak_frequency_hz - (600e6 + offset)) <= 20000
    assert result.spectrum.energy_fraction > 0.999
    assert result.spectrum.fft_bin_spacing_hz == pytest.approx(40000, abs=1e-9)
    assert result.profile_sha256 == profile_hash(ReceiveProfile())
    assert result.input.removed_mean_v == pytest.approx(0.011, abs=1e-5)


def test_periodic_window_and_mean_removal_exact_power_convention() -> None:
    n = 128
    profile = ReceiveProfile(points=n, neighbor_bins=0)
    result = qualify_receive(
        ReceiveRequest(
            record=supplied(tone(500e6, points=n) + 0.03),
            command_frequency_hz=500e6,
            profile=profile,
        )
    )
    assert isinstance(result, ReceiveQualified)
    # An on-bin interior sine under periodic Hann has center and two neighbor bins.
    # Their one-sided weighted energies have ratio 4:1:1. A symmetric window differs.
    assert result.spectrum.energy_fraction == pytest.approx(2 / 3, abs=1e-12)
    assert result.input.removed_mean_v == pytest.approx(0.03, abs=1e-14)


def test_band_limited_selection_does_not_hide_wrong_global_carrier() -> None:
    result = qualify_receive(request(tone(600e6, 0.052) + tone(1.2e9, 0.1)))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "global-peak-frequency"
    assert result.spectrum is not None
    assert result.spectrum.selected_peak_frequency_hz == 600e6
    assert result.spectrum.global_peak_frequency_hz == 1.2e9
    assert result.spectrum.energy_fraction == pytest.approx(0.052**2 / (0.052**2 + 0.1**2))


def test_wrong_in_band_carrier_rejected() -> None:
    result = qualify_receive(request(tone(571.43e6)))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "band-peak-frequency"


@pytest.mark.parametrize("frequency", [594e6, 606e6])
def test_inclusive_one_percent_frequency_bound(frequency: float) -> None:
    result = qualify_receive(request(tone(frequency)))
    assert isinstance(result, ReceiveQualified)


@pytest.mark.parametrize("frequency", [593.96e6, 606.04e6])
def test_next_bin_outside_one_percent_is_rejected(frequency: float) -> None:
    result = qualify_receive(request(tone(frequency)))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "band-peak-frequency"


def test_weak_neighborhood_despite_correct_global_peak() -> None:
    y = tone(600e6, 0.023)
    for frequency in (500e6, 550e6, 650e6, 700e6, 750e6, 800e6):
        y += tone(frequency, 0.021)
    result = qualify_receive(request(y))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "energy-fraction"
    assert result.spectrum is not None
    assert result.spectrum.selected_peak_frequency_hz == 600e6
    assert result.spectrum.global_peak_frequency_hz == 600e6
    assert result.spectrum.energy_fraction < 0.2


def test_seeded_noise_is_not_received_carrier() -> None:
    result = qualify_receive(request(np.random.default_rng(20261001).normal(0, 0.015, POINTS)))
    assert isinstance(result, ReceiveRejected)
    assert result.spectrum is not None
    assert result.spectrum.energy_fraction < 0.01


@pytest.mark.parametrize("command,physical", [(600e6, 3.4e9), (1e9, 3e9)])
def test_out_of_nyquist_physical_tone_can_qualify_sampled_component(
    command: float, physical: float
) -> None:
    result = qualify_receive(request(tone(physical), command))
    assert isinstance(result, ReceiveQualified)
    assert result.spectrum.selected_peak_frequency_hz == command
    # This positive control is the claim limit: no physical carrier origin is identified.


def test_receive_window_does_not_establish_later_fit_validity() -> None:
    frequency = 600.5e6
    result = qualify_receive(request(tone(frequency)))
    assert isinstance(result, ReceiveQualified)
    assert abs(frequency / result.command_frequency_hz - 1) > 1e-4


def test_even_n_nyquist_weight_is_one_and_interior_weight_two() -> None:
    n = 128
    y = tone(500e6, 0.09, n) + 0.055 * np.cos(np.pi * np.arange(n))
    result = qualify_receive(
        ReceiveRequest(
            record=supplied(y), command_frequency_hz=500e6, profile=ReceiveProfile(points=n)
        )
    )
    assert isinstance(result, ReceiveQualified)
    assert result.spectrum.global_peak_frequency_hz == pytest.approx(500e6, abs=1e-6)
    assert result.spectrum.energy_fraction == pytest.approx(
        (0.09**2 / 2) / (0.09**2 / 2 + 0.055**2), abs=1e-12
    )


def test_odd_n_last_bin_is_not_treated_as_nyquist() -> None:
    n = 2049
    command = 200 * RATE / n
    high = (n // 2) * RATE / n
    result = qualify_receive(
        ReceiveRequest(
            record=supplied(tone(command, 0.074, n) + tone(high, 0.09, n)),
            command_frequency_hz=command,
            profile=ReceiveProfile(points=n),
        )
    )
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "global-peak-frequency"


def test_relative_tie_chooses_lowest_bin_and_retains_diagnostic() -> None:
    energy = np.array([0.0, 1.0, 1 + 0.5e-12, 0.1], dtype=np.float64)
    eligible = np.array([1, 2, 3], dtype=np.int64)
    result = _strongest(energy, eligible, 1e-12)
    assert result.bin == 1
    assert result.tie_bins == (1, 2)
    assert _strongest(energy, eligible, 1e-14).bin == 2


@pytest.mark.parametrize("mode", [WaveformMode.NORMAL, WaveformMode.MAXIMUM])
def test_display_and_maximum_records_cannot_be_promoted(mode: WaveformMode) -> None:
    result = qualify_receive(
        ReceiveRequest(record=supplied(tone(600e6), mode), command_frequency_hz=600e6)
    )
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "not-raw"


@pytest.mark.parametrize("field", ["record_duration_s", "first_to_last_span_s"])
def test_full_raw_qualification_is_rebound_not_only_parsed_samples(field: str) -> None:
    original = request(tone(600e6))
    forged = original.record.model_copy(update={field: 1.0})
    result = qualify_receive(original.model_copy(update={"record": forged}))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "raw-evidence-mismatch"


@pytest.mark.parametrize("component", ["samples", "preamble", "hash", "rate"])
def test_forged_raw_evidence_or_observations_rejected(component: str) -> None:
    original = request(tone(600e6))
    waveform = original.record.waveform
    acquisition = original.record.acquisition
    if component == "samples":
        waveform = waveform.model_copy(update={"volts": (0.01,) * POINTS})
    elif component == "preamble":
        waveform = waveform.model_copy(
            update={"preamble": waveform.preamble.model_copy(update={"x_origin_s": 1.0})}
        )
    elif component == "hash":
        waveform = waveform.model_copy(
            update={"evidence": waveform.evidence.model_copy(update={"waveform_sha256": "0" * 64})}
        )
    else:
        acquisition = acquisition.model_copy(update={"actual_sample_rate_hz": 2e9})
    forged = original.record.model_copy(update={"waveform": waveform, "acquisition": acquisition})
    result = qualify_receive(original.model_copy(update={"record": forged}))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.stage == "raw"


def test_invalid_unchecked_profile_is_rejected_before_numerical_use() -> None:
    original = request(tone(600e6))
    result = qualify_receive(
        original.model_copy(
            update={"profile": original.profile.model_copy(update={"neighbor_bins": -1})}
        )
    )
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "invalid-contract"


@pytest.mark.parametrize("kind", ["above-nyquist", "empty"])
def test_invalid_or_empty_sampled_search_band(kind: str) -> None:
    original = request(tone(600e6))
    profile = ReceiveProfile(band_lower_ratio=0.999999, band_upper_ratio=1.000001)
    candidate = ReceiveRequest(
        record=original.record,
        command_frequency_hz=3e9 if kind == "above-nyquist" else 600.020e6,
        profile=profile,
    )
    result = qualify_receive(candidate)
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == ("search-band" if kind == "above-nyquist" else "empty-band")


def test_geometry_and_rate_profiles_are_explicit() -> None:
    original = request(tone(600e6))
    for profile in (ReceiveProfile(points=99999), ReceiveProfile(sample_rate_hz=2e9)):
        result = qualify_receive(
            ReceiveRequest(record=original.record, command_frequency_hz=600e6, profile=profile)
        )
        assert isinstance(result, ReceiveRejected)
        assert result.issue.stage == "profile"


@pytest.mark.parametrize("value", [0.18, -0.18, 0.181])
def test_strict_voltage_boundary_is_not_accepted(value: float) -> None:
    y = tone(600e6)
    y[0] = value
    result = qualify_receive(request(y))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "voltage-range"


def test_degenerate_constant_record_is_rejected() -> None:
    result = qualify_receive(request(np.full(POINTS, 0.01)))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "vpp-range"


def test_zero_numerical_energy_rejected_without_dividing_by_zero() -> None:
    result = qualify_receive(
        ReceiveRequest(
            record=supplied(tone(600e6, 1e-300)),
            command_frequency_hz=600e6,
            profile=ReceiveProfile(minimum_vpp_v=0.0),
        )
    )
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "non-dc-energy"


def test_small_raw_count_rejected_with_typed_geometry_result() -> None:
    result = qualify_receive(request(np.array([0.01, -0.01, 0.0])))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "geometry"


def test_models_forbid_unknown_fields_coercion_and_nonfinite_profiles() -> None:
    with pytest.raises(ValidationError):
        ReceiveProfile.model_validate({"neighbor_bins": "2"})
    with pytest.raises(ValidationError):
        ReceiveProfile.model_validate({"unexpected": True})
    with pytest.raises(ValidationError):
        ReceiveProfile(sample_rate_hz=math.nan)
    assert profile_hash(ReceiveProfile()) != profile_hash(ReceiveProfile(neighbor_bins=1))
