"""Common immutable contracts for external evidence values."""

from pydantic import BaseModel, ConfigDict


class EvidenceValue(BaseModel):
    """Reject undeclared fields and coercion at the evidence boundary."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )
