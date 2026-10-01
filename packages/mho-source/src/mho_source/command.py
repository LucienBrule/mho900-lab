"""Explicit source protocol alternatives sharing one bounded transport."""

from typing import assert_never

from .factory import FactoryPointCommand, encode_factory_point
from .point import PointCommand, encode_point

type Command = PointCommand | FactoryPointCommand


def encode_command(command: Command) -> bytes:
    match command:
        case PointCommand():
            return encode_point(command)
        case FactoryPointCommand():
            return encode_factory_point(command)
        case _:
            assert_never(command)
