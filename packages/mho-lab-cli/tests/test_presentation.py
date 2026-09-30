"""Shared presentation escapes external strings without creating TOML syntax."""

import tomllib

import pytest

from mho_lab_cli.presentation import toml_string


@pytest.mark.parametrize(
    "value",
    [
        "",
        'quote" slash\\',
        "line\nreturn\rtab\t",
        "café 🕯",
        "".join(chr(n) for n in range(32)) + chr(127),
    ],
)
def test_toml_string_roundtrips_supported_unicode(value: str) -> None:
    assert tomllib.loads("value = " + toml_string(value))["value"] == value


def test_lone_surrogate_rejected_without_echo() -> None:
    with pytest.raises(ValueError) as error:
        toml_string("PRIVATE" + chr(0xD800))
    assert "PRIVATE" not in str(error.value)
