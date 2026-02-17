# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Regression-style tests exercising intermediate helpers."""

from typing import Any, Dict, Tuple

import pytest

from pyagentspec.evaluation import Dataset
from pyagentspec.evaluation.intermediates import Intermediate, add_intermediates


class _EchoIntermediate(Intermediate[int]):
    """Return the provided value and expose metadata for assertions."""

    def __init__(self, input_mapping: Dict[str, str] | None = None) -> None:
        super().__init__(name="echo", input_mapping=input_mapping)

    async def compute_value(self, idx: int, value: int) -> Tuple[int, Dict[str, Any]]:
        return value, {"idx": idx, "intermediate": True}


class _StatefulIntermediate(Intermediate[str]):
    """Capture invocation order to prove per-sample execution."""

    def __init__(self, input_mapping: Dict[str, str] | None = None) -> None:
        super().__init__(name="stateful", input_mapping=input_mapping)
        self._call_ids: list[int] = []

    async def compute_value(self, idx: int) -> Tuple[str, Dict[str, Any]]:
        self._call_ids.append(idx)
        return f"intermediate-{idx}", {"idx": idx}


@pytest.fixture()
def dataset() -> Dataset:
    data = [
        {"idx": 0, "value": 1},
        {"idx": 1, "value": 2},
        {"idx": 2, "value": 3},
    ]
    return Dataset.from_dict(data)


@pytest.mark.anyio
async def test_intermediate_call_respects_mapping() -> None:
    dataset = Dataset.from_dict(
        [
            {"idx": 0, "external_value": 1},
            {"idx": 1, "external_value": 2},
        ]
    )
    intermediate = _EchoIntermediate(input_mapping={"external_value": "value"})

    augmented = await add_intermediates(dataset, [intermediate])
    augmented_sample = await augmented.get_sample(0)

    assert augmented_sample["external_value"] == 1
    assert augmented_sample["echo"] == 1


@pytest.mark.anyio
async def test_add_multiple_intermediates_merges_samples(dataset: Dataset) -> None:
    intermediates = [_EchoIntermediate(), _StatefulIntermediate()]

    augmented = await add_intermediates(dataset, intermediates, max_concurrency=1)

    first = await augmented.get_sample(0)
    second = await augmented.get_sample(2)

    assert first["value"] == 1
    assert first["echo"] == 1
    assert first["stateful"] == "intermediate-0"

    assert second["value"] == 3
    assert second["echo"] == 3
    assert second["stateful"] == "intermediate-2"


@pytest.mark.anyio
async def test_intermediate_call_argument_binding(dataset: Dataset) -> None:

    class _KwOnlyIntermediate(Intermediate[int]):
        def __init__(self) -> None:
            super().__init__(name="kw_only")

        async def compute_value(self, *, value: int) -> Tuple[int, Dict[str, Any]]:
            return value + 10, {}

    intermediate = _KwOnlyIntermediate()
    augmented = await add_intermediates(dataset, [intermediate])

    sample = await augmented.get_sample(0)
    assert sample["kw_only"] == 11
