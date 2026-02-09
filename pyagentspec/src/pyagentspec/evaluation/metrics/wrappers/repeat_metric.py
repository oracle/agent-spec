# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, Tuple

from pyagentspec.evaluation.aggregators.aggregator import (
    AggregatedValueType,
    Aggregator,
    MetricToAggregateValueType,
)
from pyagentspec.evaluation.metrics.metrics import Metric


class RepeatMetric(Metric[AggregatedValueType]):
    """
    Computes a metric multiple times and aggregates the results.

    RepeatMetric wraps an underlying metric and runs it ``num_repeats`` times, collecting the
    results for each repetition. The aggregated result is obtained by applying the provided
    aggregator to the collection of metric outputs.

    This is useful for metrics with stochastic or non-deterministic behavior, allowing robust
    estimation by repeated sampling and aggregation.

    RepeatMetric itself is a ``Metric[U]``: it returns results of type ``U``, as produced by the
    aggregator, even if the underlying metric returns a different type ``T``.

    Notes
    -----
    - ``metric`` is expected to be a callable following the ``Metric[T]`` interface, returning a
      tuple ``(value: T, details: dict)``.
    - ``aggregator`` should be a callable or object that takes an iterable of `T` values and
      returns a summary value of type ``U``.
    - RepeatMetric is parameterized as ``Metric[U]``, with ``U`` being the return type after
      aggregation.

    """

    def __init__(
        self,
        metric: Metric[MetricToAggregateValueType],
        aggregator: Aggregator[Any, AggregatedValueType],
        num_repeats: int,
        name: str | None = None,
    ) -> None:
        """
        Initialize the RepeatMetric.

        Parameters
        ----------
        name : str
            The name for this repeated metric.

        num_repeats : int
            The number of repetitions for the underlying metric (must be >= 1).

        metric : Metric[T]
            The metric to compute on each repetition.

        aggregator : Aggregator[T, U]
            Function or object that aggregates the repeated metric values into a single result.

        Raises
        ------
        ValueError
            If ``num_repeats`` is not a positive integer.

        """

        if (not isinstance(num_repeats, int)) or num_repeats < 1:
            raise ValueError(f"`num_repeats` of `RepeatMetric` {name} must be a positive integer.")

        super().__init__(
            name=name or metric.name,
            input_mapping=None,
            num_retries=0,
            on_failure="raise",
        )
        self.metric = metric
        self.aggregator = aggregator
        self.num_repeats = num_repeats

    async def compute_metric(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[AggregatedValueType, Dict[str, Any]]:
        results = [await self.metric(*args, **kwargs) for _ in range(self.num_repeats)]
        value = self.aggregator([result[0] for result in results])
        return value, {"results": results}
