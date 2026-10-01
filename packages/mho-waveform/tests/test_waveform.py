"""Known-voltage and adversarial supplied-byte controls; no physical operations."""

import hashlib

import pytest
from pydantic import ValidationError

from mho_waveform import (
    ParsedWaveform,
    RawAcquisition,
    RawQualified,
    WaveformInputs,
    WaveformLimits,
    WaveformRejected,
    parse_ascii,
    qualify_raw,
)

PREAMBLE = b"2,2,3,1,2.500000E-10,-1.000000E-6,2,6.6667E-6,0,32768\n"
DATA = b"+1.25000E-1,-0.25,.003\n"


def inputs(preamble: bytes = PREAMBLE, data: bytes = DATA) -> WaveformInputs:
    return WaveformInputs(preamble_before=preamble, waveform=data, preamble_after=preamble)


def acquisition() -> RawAcquisition:
    return RawAcquisition(actual_sample_rate_hz=4e9, memory_points=3, start=1, stop=3)


def parsed() -> ParsedWaveform:
    result = parse_ascii(inputs())
    assert isinstance(result, ParsedWaveform)
    return result


@pytest.mark.parametrize("ending", [b"\n", b"\r\n"])
def test_exact_voltage_bytes_and_raw_duration_are_preserved(ending: bytes) -> None:
    source = inputs(PREAMBLE[:-1] + ending, DATA[:-1] + ending)
    result = parse_ascii(source)
    assert isinstance(result, ParsedWaveform)
    assert result.volts == (0.125, -0.25, 0.003)  # WORD calibration fields never rescale ASCII.
    assert result.evidence.waveform == source.waveform
    assert result.evidence.preamble_before == source.preamble_before
    assert result.evidence.preamble_after == source.preamble_after
    assert result.evidence.waveform_sha256 == hashlib.sha256(source.waveform).hexdigest()
    assert (
        result.evidence.preamble_before_sha256 == hashlib.sha256(source.preamble_before).hexdigest()
    )
    assert (
        result.evidence.preamble_after_sha256 == hashlib.sha256(source.preamble_after).hexdigest()
    )
    qualified = qualify_raw(result, acquisition())
    assert isinstance(qualified, RawQualified)
    assert qualified.record_duration_s == pytest.approx(7.5e-10)
    assert qualified.first_to_last_span_s == pytest.approx(5e-10)
    assert qualified.waveform.preamble.x_origin_s == -1e-6
    assert qualified.waveform.preamble.x_reference == 2


def test_partial_selected_extent_is_not_confused_with_total_memory() -> None:
    result = qualify_raw(
        parsed(), RawAcquisition(actual_sample_rate_hz=4e9, memory_points=10, start=4, stop=6)
    )
    assert isinstance(result, RawQualified)
    rejected = qualify_raw(
        parsed(), RawAcquisition(actual_sample_rate_hz=4e9, memory_points=10, start=4, stop=7)
    )
    assert isinstance(rejected, WaveformRejected)
    assert rejected.issue.code == "extent-count"


@pytest.mark.parametrize("mode", [b"0", b"1"])
def test_display_or_maximum_mode_can_parse_but_cannot_qualify_raw(mode: bytes) -> None:
    result = parse_ascii(inputs(PREAMBLE.replace(b"2,2,3", b"2," + mode + b",3")))
    assert isinstance(result, ParsedWaveform)
    rejected = qualify_raw(result, acquisition())
    assert isinstance(rejected, WaveformRejected)
    assert rejected.issue.code == "not-raw"


@pytest.mark.parametrize(
    "data,code",
    [
        (DATA[:-1], "line-framing"),
        (DATA + b"\n", "line-framing"),
        (b".1\n,.2,.3\n", "line-framing"),
        (b".1,.2,.3\r", "line-framing"),
        (b".1,.2,.3\x00\n", "non-ascii"),
        (b".1,.2,\xff\n", "non-ascii"),
        (b".1,.2\n", "sample-count"),
        (b".1,.2,.3,.4\n", "sample-count"),
        (b".1,,.3\n", "numeric-token"),
        (b" .1,.2,.3\n", "numeric-token"),
        (b"nan,.2,.3\n", "numeric-token"),
        (b"Infinity,.2,.3\n", "numeric-token"),
        (b"0x1,.2,.3\n", "numeric-token"),
        (b"1_000,.2,.3\n", "numeric-token"),
        (b"9.9e37,.2,.3\n", "nonfinite-or-sentinel"),
        (b"-9.9e37,.2,.3\n", "nonfinite-or-sentinel"),
        (b"1e9999,.2,.3\n", "nonfinite-or-sentinel"),
        (b"#10,.2,.3\n", "numeric-token"),
    ],
)
def test_adversarial_samples_are_typed_rejections(data: bytes, code: str) -> None:
    result = parse_ascii(inputs(data=data))
    assert isinstance(result, WaveformRejected)
    assert result.issue.code == code
    assert result.evidence is not None
    assert result.evidence.waveform == data


@pytest.mark.parametrize(
    "preamble,code",
    [
        (PREAMBLE[:-1], "line-framing"),
        (PREAMBLE + b"\n", "line-framing"),
        (PREAMBLE.replace(b",32768", b""), "field-count"),
        (PREAMBLE.replace(b",32768", b",32768,0"), "field-count"),
        (PREAMBLE.replace(b"2,2,3", b"9,2,3"), "preamble-values"),
        (PREAMBLE.replace(b"2,2,3", b"2,9,3"), "preamble-values"),
        (PREAMBLE.replace(b"2,2,3", b"0,2,3"), "unsupported-format"),
        (PREAMBLE.replace(b"2,2,3", b"1,2,3"), "unsupported-format"),
        (PREAMBLE.replace(b"2,2,3", b"2,2,0"), "preamble-values"),
        (PREAMBLE.replace(b",3,1,", b",3,0,"), "preamble-values"),
        (PREAMBLE.replace(b",3,1,", b",3.0,1,"), "integer-token"),
        (PREAMBLE.replace(b"2.500000E-10", b"0"), "preamble-values"),
        (PREAMBLE.replace(b"2.500000E-10", b"-1e-10"), "preamble-values"),
        (PREAMBLE.replace(b"2.500000E-10", b"9.9e37"), "nonfinite-or-sentinel"),
        (PREAMBLE.replace(b"32768", b"nan"), "numeric-token"),
    ],
)
def test_invalid_preamble_fields_are_rejected(preamble: bytes, code: str) -> None:
    result = parse_ascii(inputs(preamble=preamble))
    assert isinstance(result, WaveformRejected)
    assert result.issue.code == code


def test_changed_preamble_including_framing_is_rejected() -> None:
    result = parse_ascii(
        WaveformInputs(
            preamble_before=PREAMBLE, waveform=DATA, preamble_after=PREAMBLE[:-1] + b"\r\n"
        )
    )
    assert isinstance(result, WaveformRejected)
    assert result.issue.code == "preamble-changed"


@pytest.mark.parametrize(
    "limits,code",
    [
        (WaveformLimits(max_preamble_bytes=10), "byte-limit"),
        (WaveformLimits(max_waveform_bytes=10), "byte-limit"),
        (WaveformLimits(max_points=2), "point-limit"),
        (WaveformLimits(max_numeric_bytes=5), "numeric-token"),
    ],
)
def test_limits_apply_before_large_split(limits: WaveformLimits, code: str) -> None:
    result = parse_ascii(inputs(), limits)
    assert isinstance(result, WaveformRejected)
    assert result.issue.code == code


def test_rate_mismatch_rejects_even_if_count_and_raw_mode_match() -> None:
    result = qualify_raw(
        parsed(), RawAcquisition(actual_sample_rate_hz=2e9, memory_points=3, start=1, stop=3)
    )
    assert isinstance(result, WaveformRejected)
    assert result.issue.code == "interval-rate"


def test_tolerance_is_explicit_and_bounded() -> None:
    record = parsed()
    rate = 4e9 * (1 + 5e-7)
    tight = qualify_raw(
        record, RawAcquisition(actual_sample_rate_hz=rate, memory_points=3, start=1, stop=3)
    )
    assert isinstance(tight, WaveformRejected)
    relaxed = qualify_raw(
        record,
        RawAcquisition(
            actual_sample_rate_hz=rate,
            memory_points=3,
            start=1,
            stop=3,
            interval_relative_tolerance=1e-6,
        ),
    )
    assert isinstance(relaxed, RawQualified)
    with pytest.raises(ValidationError):
        RawAcquisition(
            actual_sample_rate_hz=4e9,
            memory_points=3,
            start=1,
            stop=3,
            interval_relative_tolerance=1.0,
        )


def test_single_sample_span_is_zero_while_duration_is_one_interval() -> None:
    result = parse_ascii(inputs(PREAMBLE.replace(b"2,2,3", b"2,2,1"), b".1\n"))
    assert isinstance(result, ParsedWaveform)
    qualified = qualify_raw(
        result, RawAcquisition(actual_sample_rate_hz=4e9, memory_points=1, start=1, stop=1)
    )
    assert isinstance(qualified, RawQualified)
    assert qualified.record_duration_s == 2.5e-10
    assert qualified.first_to_last_span_s == 0


def test_unchecked_models_cannot_forge_parsed_evidence_or_contracts() -> None:
    record = parsed()
    changed = record.model_copy(update={"volts": (0.1, 0.2, 0.3)})
    rejected = qualify_raw(changed, acquisition())
    assert isinstance(rejected, WaveformRejected)
    assert rejected.issue.code == "parsed-evidence-mismatch"
    wrong_hash = record.evidence.model_copy(update={"waveform_sha256": "0" * 64})
    rejected = qualify_raw(record.model_copy(update={"evidence": wrong_hash}), acquisition())
    assert isinstance(rejected, WaveformRejected)
    assert rejected.issue.code == "parsed-evidence-mismatch"
    rejected = qualify_raw(record, acquisition().model_copy(update={"start": 0}))
    assert isinstance(rejected, WaveformRejected)
    assert rejected.issue.code == "invalid-contract"
    parse_rejected = parse_ascii(inputs(), WaveformLimits().model_copy(update={"max_points": None}))
    assert isinstance(parse_rejected, WaveformRejected)
    assert parse_rejected.issue.code == "invalid-contract"


def test_external_models_forbid_coercion_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WaveformInputs.model_validate(
            {"preamble_before": "text", "waveform": DATA, "preamble_after": PREAMBLE}
        )
    with pytest.raises(ValidationError):
        RawAcquisition.model_validate(
            {"actual_sample_rate_hz": "4000000000", "memory_points": 3, "start": 1, "stop": 3}
        )
    with pytest.raises(ValidationError):
        WaveformLimits.model_validate({"unknown_limit": 1})


@pytest.mark.parametrize("attribute", ["volts", "preamble", "evidence"])
def test_parsed_fields_are_immutable(attribute: str) -> None:
    record = parsed()
    with pytest.raises(ValidationError):
        setattr(record, attribute, None)
