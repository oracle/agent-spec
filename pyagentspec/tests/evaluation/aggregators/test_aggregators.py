# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Sequence

import pytest

from pyagentspec.evaluation.aggregators import HarmonicMeanAggregator, MeanAggregator


@pytest.mark.parametrize(
    "values, expected_aggregated_value",
    (
        ((1, 2, 3), 2),
        ((1, 2.0, 3), 2),
        ((1.0, 2.0, 3.0), 2),
        ((True, 2.0, 3.0), 2),
        ((True, 2, 3.0), 2),
        ((False, True, 2.0, 3.0), 1.5),
    ),
)
def test_mean_aggregator(values: Sequence[Any], expected_aggregated_value: int | float) -> None:
    aggregator = MeanAggregator()
    aggregated_value = aggregator(values)
    assert aggregated_value == expected_aggregated_value


def test_mean_aggregator_fails_when_empty() -> None:
    aggregator = MeanAggregator()
    with pytest.raises(ValueError, match="Expected at least one numeric value"):
        aggregator([])


@pytest.mark.parametrize(
    "values, expected_aggregated_value",
    (
        ((1, 2, 3), 1.6363636363636365),
        ((1, 2.0, 3), 1.6363636363636365),
        ((1.0, 2.0, 3.0), 1.6363636363636365),
        ((True, 2.0, 3.0), 1.6363636363636365),
        ((True, 2, 3.0), 1.6363636363636365),
        ((False, True, 2.0, 3.0), 0),
    ),
)
def test_harmonic_mean_aggregator(values: Sequence[Any], expected_aggregated_value: float) -> None:
    aggregator = HarmonicMeanAggregator()
    aggregated_value = aggregator(values)
    assert pytest.approx(aggregated_value) == expected_aggregated_value


def test_harmonic_mean_aggregator_fails_when_empty() -> None:
    aggregator = HarmonicMeanAggregator()
    with pytest.raises(ValueError, match="Expected at least one numeric value"):
        aggregator([])


def test_harmonic_mean_aggregator_fails_when_negative_value_present() -> None:
    aggregator = HarmonicMeanAggregator()
    with pytest.raises(ValueError, match="non-negative"):
        aggregator([1, -1, 2])
