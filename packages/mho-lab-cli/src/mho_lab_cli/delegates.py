"""Application operations that remain independent of Click."""

from dataclasses import dataclass
from pathlib import Path

from mho_lab_cli.quality import PolicyViolation, check_paths


@dataclass(frozen=True)
class ToolIdentity:
    """Human-readable identity of this local tool, not an instrument."""

    name: str
    version: str


def identify_tool() -> ToolIdentity:
    return ToolIdentity(name="mho-lab", version="0.1.0")


@dataclass(frozen=True)
class PolicyPassed:
    """No prohibited authored forms were detected."""


@dataclass(frozen=True)
class PolicyRejected:
    """Concrete source findings prevent acceptance."""

    violations: tuple[PolicyViolation, ...]


def check_quality(paths: tuple[Path, ...]) -> PolicyPassed | PolicyRejected:
    violations = check_paths(list(paths))
    return PolicyRejected(tuple(violations)) if violations else PolicyPassed()
