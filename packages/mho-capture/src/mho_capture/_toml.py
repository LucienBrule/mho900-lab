"""TOML basic strings for validated Unicode scalar configuration and diagnostics.

UTF-8 publication remains responsible for rejecting unsupported surrogate text
in an OS diagnostic; lifecycle publication catches and preserves that failure.
"""

import json


def string(value: str) -> str:
    # JSON's string escapes are valid in TOML, but its literal DEL is not.
    # Keep non-ASCII scalar values literal to avoid JSON surrogate-pair escapes.
    return json.dumps(value, ensure_ascii=False).replace("\x7f", "\\u007f")


def strings(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(string(value) for value in values) + "]"
