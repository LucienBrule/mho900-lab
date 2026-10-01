"""Point framing recovered from the pinned public touchscreen firmware image."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

FACTORY_REFERENCE_SHA256 = "a3111637e7cab47fd5045a04c0521c3f525016f1f15d83174cc5f67be8b0b60f"


def _payload(frequency_hz: int, power_code: int) -> bytes:
    whole_mhz, remainder_hz = divmod(frequency_hz, 1_000_000)
    return (
        b"\x55\x55"
        + whole_mhz.to_bytes(2, "big")
        + (remainder_hz // 10_000).to_bytes(2, "big")
        + bytes([power_code])
    )


class FactoryPointCommand(BaseModel):
    """Exact 10 kHz settings; power is the raw two-bit field, not a dBm claim."""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always"
    )
    frequency_hz: int = Field(ge=23_500_000, le=6_000_000_000)
    power_code: int = Field(ge=0, le=3)

    @model_validator(mode="after")
    def framing(self) -> Self:
        if self.frequency_hz % 10_000:
            raise ValueError("frequency must be an exact multiple of 10000 Hz")
        # The recovered ISR treats CR as framing even inside binary fields.
        if b"\r" in _payload(self.frequency_hz, self.power_code):
            raise ValueError("frequency payload contains the receiver's CR delimiter")
        return self


def encode_factory_point(command: FactoryPointCommand) -> bytes:
    command = FactoryPointCommand.model_validate(command)
    return _payload(command.frequency_hz, command.power_code) + b"\r\n"
