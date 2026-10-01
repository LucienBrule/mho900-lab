import pytest
from pydantic import ValidationError

from mho_source import FactoryPointCommand, encode_command, encode_factory_point


@pytest.mark.parametrize(
    "frequency,expected",
    [
        (100_000_000, "55 55 00 64 00 00 00 0D 0A"),
        (100_250_000, "55 55 00 64 00 19 00 0D 0A"),
        (100_100_000, "55 55 00 64 00 0A 00 0D 0A"),
        (23_500_000, "55 55 00 17 00 32 00 0D 0A"),
        (6_000_000_000, "55 55 17 70 00 00 00 0D 0A"),
    ],
)
def test_independent_vectors(frequency: int, expected: str) -> None:
    command = FactoryPointCommand(frequency_hz=frequency, power_code=0)
    assert encode_factory_point(command) == bytes.fromhex(expected)
    assert encode_command(command) == bytes.fromhex(expected)


@pytest.mark.parametrize("power", [0, 1, 2, 3])
def test_raw_power_field(power: int) -> None:
    frame = encode_factory_point(FactoryPointCommand(frequency_hz=100_000_000, power_code=power))
    assert frame[:6] == bytes.fromhex("55 55 00 64 00 00")
    assert frame[6] == power and frame[7:] == b"\r\n"


@pytest.mark.parametrize(
    "field,value",
    [
        ("frequency_hz", "100000000"),
        ("frequency_hz", True),
        ("frequency_hz", 100_000_000.0),
        ("frequency_hz", 23_490_000),
        ("frequency_hz", 6_000_010_000),
        ("frequency_hz", 100_001_000),
        ("frequency_hz", 100_130_000),  # Fractional field CR.
        ("frequency_hz", 269_000_000),  # Whole MHz low byte CR.
        ("frequency_hz", 3_328_000_000),  # Whole MHz high byte CR.
        ("power_code", -1),
        ("power_code", 4),
        ("power_code", True),
        ("reference_hz", 25_000_000),
    ],
)
def test_invalid_input(field: str, value: object) -> None:
    fields: dict[str, object] = {"frequency_hz": 100_000_000, "power_code": 0}
    fields[field] = value
    with pytest.raises(ValidationError):
        FactoryPointCommand.model_validate(fields)


def test_unchecked_copy_revalidated_by_encoder() -> None:
    command = FactoryPointCommand(frequency_hz=100_000_000, power_code=0)
    for update in ({"power_code": 4}, {"frequency_hz": 100_130_000}):
        with pytest.raises(ValidationError):
            encode_command(command.model_copy(update=update))
