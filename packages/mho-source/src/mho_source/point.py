"""Candidate touchscreen protocol; encoding is not hardware qualification."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PointCommand(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always"
    )
    frequency_hz: int = Field(ge=23_500_000, le=6_000_000_000)
    reference_hz: int = Field(ge=5_000_000, le=210_000_000)
    power_code: int = Field(ge=1, le=4)

    @model_validator(mode="after")
    def units(self) -> Self:
        if self.frequency_hz % 1_000 or self.reference_hz % 100:
            raise ValueError("frequency/reference must be exactly representable in wire units")
        return self


def encode_point(command: PointCommand) -> bytes:
    command = PointCommand.model_validate(command)
    body = (
        bytes([0xAD, 1, 1, command.power_code])
        + (command.reference_hz // 100).to_bytes(3, "big")
        + (command.frequency_hz // 1_000).to_bytes(3, "big")
    )
    return body + bytes([sum(body) & 0xFF])
