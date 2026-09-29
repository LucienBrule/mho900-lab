"""Versioned, immutable values at the TOML boundary."""

import json
import re
import tomllib
from typing import Literal, Self

from pydantic import ConfigDict, Field, RootModel, field_validator, model_validator

from .contracts import EvidenceValue


class ArtifactPath(RootModel[str]):
    """Canonical portable relative name; never a host path."""

    model_config = ConfigDict(frozen=True, strict=True)

    @field_validator("root")
    @classmethod
    def canonical(cls, value: str) -> str:
        if (
            not value
            or any(part in ("", ".", "..") for part in value.split("/"))
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or any(char in value for char in "\\:")
            or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
        ):
            raise ValueError("artifact path must be a canonical relative slash-separated name")
        return value


class Sha256(RootModel[str]):
    """Lowercase SHA-256 hexadecimal digest."""

    model_config = ConfigDict(frozen=True, strict=True)

    @field_validator("root")
    @classmethod
    def hexadecimal(cls, value: str) -> str:
        if re.fullmatch("[0-9a-f]{64}", value) is None:
            raise ValueError("expected a lowercase SHA-256 digest")
        return value


class Artifact(EvidenceValue):
    path: ArtifactPath
    sha256: Sha256
    size_bytes: int = Field(ge=0)


class ManifestV1(EvidenceValue):
    schema_version: Literal["mho-evidence.manifest/1"]
    inventory: Literal["recursive-regular-files"]
    empty_allowed: bool = False
    # TOML arrays arrive as lists; inner model fields still reject coercion.
    artifacts: tuple[Artifact, ...] = Field(strict=False)

    @model_validator(mode="after")
    def inventory_order(self) -> Self:
        paths = [artifact.path.root for artifact in self.artifacts]
        if paths != sorted(set(paths)):
            raise ValueError("artifact paths must be unique and sorted")
        if not paths and not self.empty_allowed:
            raise ValueError("empty inventory requires empty_allowed=true")
        return self


def load_manifest(data: bytes) -> ManifestV1:
    """Validate the untyped TOML edge immediately; no mapping escapes."""
    value: object = tomllib.loads(data.decode("utf-8"))
    return ManifestV1.model_validate(value)


def dump_manifest(manifest: ManifestV1) -> bytes:
    """Emit one deterministic TOML representation, without host metadata."""
    lines = [
        'schema_version = "mho-evidence.manifest/1"',
        'inventory = "recursive-regular-files"',
        "empty_allowed = " + str(manifest.empty_allowed).lower(),
    ]
    if not manifest.artifacts:
        lines.append("artifacts = []")
    for artifact in manifest.artifacts:
        lines.extend(
            [
                "",
                "[[artifacts]]",
                "path = " + json.dumps(artifact.path.root, ensure_ascii=False),
                "sha256 = " + json.dumps(artifact.sha256.root),
                "size_bytes = " + str(artifact.size_bytes),
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")
