# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, Tuple

import pytest

from pyagentspec.evaluation.aggregators.implementations import MeanAggregator
from pyagentspec.evaluation.intermediates import Intermediate
from pyagentspec.evaluation.metrics.metrics import Metric
from pyagentspec.evaluation.metrics.wrappers import EnsembleMetric, RepeatMetric
from pyagentspec.evaluation.metrics.wrappers.with_intermediate_metric import (
    WithIntermediatesMetric,
)


class _CounterMetric(Metric[int]):
    """Counter metric that increments on every invocation."""

    def __init__(self) -> None:
        super().__init__(name="counter", input_mapping=None, num_retries=0, on_failure="raise")
        self.calls: int = 0

    async def compute_metric(self, *, value: int) -> Tuple[int, Dict[str, Any]]:
        """Return the provided value offset by the call count."""
        self.calls += 1
        return value + self.calls, {"call": self.calls}


class _StaticSumMetric(Metric[int]):
    """Metric returning a deterministic offset for aggregation tests."""

    def __init__(self, name: str, constant: int) -> None:
        super().__init__(name=name, input_mapping=None, num_retries=0, on_failure="raise")
        self.constant = constant

    async def compute_metric(self, *, value: int) -> Tuple[int, Dict[str, Any]]:
        """Add the static result to the supplied value."""
        return self.constant + value, {"metric": self.name}


class _DerivedIntermediate(Intermediate[int]):
    """Square the incoming value while tracking invocation count."""

    def __init__(self) -> None:
        super().__init__(name="derived")
        self.calls = 0

    async def compute_value(self, value: int) -> Tuple[int, Dict[str, Any]]:
        """Return the squared value with call metadata."""
        self.calls += 1
        return value * value, {"calls": self.calls}


class _SumMetric(Metric[int]):
    """Metric combining a base value with provided intermediate."""

    def __init__(self) -> None:
        super().__init__(name="sum", input_mapping=None, num_retries=0, on_failure="raise")

    async def compute_metric(self, value: int, derived: int) -> Tuple[int, Dict[str, Any]]:
        """Return the sum of the base value and derived input."""
        return value + derived, {"metric": True}


@pytest.fixture
def aggregator() -> MeanAggregator:
    return MeanAggregator()


@pytest.fixture
def sum_metric() -> _SumMetric:
    return _SumMetric()


@pytest.fixture
def derived_intermediate() -> _DerivedIntermediate:
    return _DerivedIntermediate()


@pytest.mark.anyio
async def test_repeat_metric_repeats_and_aggregates(aggregator) -> None:
    """Ensure RepeatMetric invokes the wrapped metric and aggregates results."""
    metric = _CounterMetric()
    repeat_metric = RepeatMetric(metric=metric, aggregator=aggregator, num_repeats=3, name="repeat")

    value, details = await repeat_metric(value=2)

    # The value returned is value + the number of the call (i.e., 2+1, 2+2, ...)
    assert value == pytest.approx((3 + 4 + 5) / 3)
    assert metric.calls == 3
    assert len(details["results"]) == 3
    for call_id, (result_value, result_details) in enumerate(details["results"], start=1):
        assert result_value == 2 + call_id
        assert result_details["call"] == call_id


@pytest.mark.anyio
async def test_repeat_metric_requires_positive_repeats(aggregator) -> None:
    metric = _CounterMetric()

    with pytest.raises(ValueError, match="must be a positive integer"):
        RepeatMetric(metric=metric, aggregator=aggregator, num_repeats=0, name="invalid")


@pytest.mark.anyio
async def test_ensemble_metric_aggregates_results(aggregator) -> None:
    """Verify EnsembleMetric aggregates member metrics and exposes details."""
    metric_one = _StaticSumMetric(name="metric_one", constant=1)
    metric_two = _StaticSumMetric(name="metric_two", constant=3)

    ensemble = EnsembleMetric(
        name="ensemble", metrics=[metric_one, metric_two], aggregator=aggregator
    )

    value, details = await ensemble(value=2)

    assert value == pytest.approx((3 + 5) / 2)
    assert set(details["results"].keys()) == {"metric_one", "metric_two"}
    for metric_name, (result_value, _) in details["results"].items():
        expected = 3 if metric_name == "metric_one" else 5
        assert result_value == expected


def test_ensemble_metric_requires_unique_metric_names(aggregator) -> None:
    """EnsembleMetric should raise when metrics share identical names."""
    metric_one = _StaticSumMetric(name="duplicate", constant=1)
    metric_two = _StaticSumMetric(name="duplicate", constant=2)

    with pytest.raises(ValueError):
        EnsembleMetric(name="invalid", metrics=[metric_one, metric_two], aggregator=aggregator)


@pytest.mark.anyio
async def test_with_intermediates_metric_computes_and_merges_details(
    sum_metric, derived_intermediate
) -> None:
    """WithIntermediatesMetric should compute intermediates and merge details."""

    wrapper = WithIntermediatesMetric(
        intermediates=[derived_intermediate],
        metric=sum_metric,
        input_mapping=None,
        num_retries=0,
        on_failure="raise",
    )

    value, details = await wrapper(value=3)

    assert value == 3 + 9
    assert details["metric"] is True
    assert details["__intermediates"] == {"derived": 9}
    assert derived_intermediate.calls == 1


@pytest.mark.anyio
async def test_with_intermediates_metric_skips_precomputed_values(
    sum_metric, derived_intermediate
) -> None:
    """Existing keyword values should prevent redundant intermediate execution."""

    wrapper = WithIntermediatesMetric(
        intermediates=[derived_intermediate],
        metric=sum_metric,
        input_mapping=None,
        num_retries=0,
        on_failure="raise",
    )

    # Since `derived` is in the values passed, the intermediate should not be called
    value, details = await wrapper(value=4, derived=10)

    assert value == 14
    assert details["__intermediates"] == {}
    assert derived_intermediate.calls == 0


def test_with_intermediates_metric_requires_unique_names(sum_metric, derived_intermediate) -> None:
    """Duplicate intermediate names must trigger a validation error."""

    with pytest.raises(ValueError):
        WithIntermediatesMetric(
            intermediates=[derived_intermediate, derived_intermediate],
            metric=sum_metric,
            input_mapping=None,
            num_retries=0,
            on_failure="raise",
        )
