"""External values cannot silently coerce or acquire undeclared fields."""

import pytest
from pydantic import ValidationError

from mho_evidence.contracts import EvidenceValue


class SampleValue(EvidenceValue):
    count: int


def test_model_rejects_string_coercion_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SampleValue.model_validate({"count": "1"})
    with pytest.raises(ValidationError):
        SampleValue.model_validate({"count": 1, "undeclared": True})


@pytest.mark.parametrize("field", ["count", "undeclared"])
def test_model_preserves_valid_value_and_rejects_mutation(field: str) -> None:
    value = SampleValue(count=1)
    assert value.count == 1
    with pytest.raises(ValidationError):
        setattr(value, field, 2)
