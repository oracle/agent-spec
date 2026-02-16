# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Collection, Dict, Tuple

from pyagentspec.evaluation._utils import _get_duplicates
from pyagentspec.evaluation.aggregators.aggregator import (
    AggregatedValueType,
    Aggregator,
    MetricToAggregateValueType,
)
from pyagentspec.evaluation.metrics.metrics import Metric


class EnsembleMetric(Metric[AggregatedValueType]):
    """
    Computes an ensemble of metrics and aggregates their results.

    EnsembleMetric wraps a collection of underlying metrics and computes each of them using the
    same input. The final result is obtained by aggregating the output values from all metrics
    using the provided aggregator.

    This is useful, for example, when you want to apply the same metric across different large
    language models (LLMs), prompt variants, or model configurations—allowing you to form a "jury"
    of metric results (e.g., multiple perspectives on a single evaluation) and then aggregate them
    into a single summary value.

    EnsembleMetric itself is a ``Metric[AggregatedValueType]``: it returns results of type
    ``AggregatedValueType`` as produced by the aggregator, even if the underlying metrics produce
    a different type ``MetricToAggregateValueType``.

    Notes
    -----
    - ``metrics`` should be a collection of objects following the ``Metric[MetricToAggregateValueType]``
      interface, each returning a tuple ``(value: MetricToAggregateValueType, details: dict)``.
    - ``aggregator`` should be a callable or object that takes an iterable of ``MetricToAggregateValueType``
      values and returns a summary value of type ``AggregatedValueType``.
    - EnsembleMetric is parameterized as ``Metric[AggregatedValueType]``,
      with ``AggregatedValueType`` being the return type after aggregation.

    """

    def __init__(
        self,
        name: str,
        metrics: Collection[Metric[MetricToAggregateValueType]],
        aggregator: Aggregator[MetricToAggregateValueType | Any, AggregatedValueType],
    ) -> None:
        """
        Initialize the EnsembleMetric.

        Parameters
        ----------
        name : str
            The name for this ensemble metric.

        metrics : Collection[Metric[MetricToAggregateValueType]]
            A collection of metrics to compute for each input. Each must implement the Metric[T] interface.

        aggregator : Aggregator[MetricToAggregateValueType, AggregatedValueType]
            Function or object that aggregates the values returned by the ensemble of metrics into a single result.

        Raises
        ------
        ValueError
            If ``metrics`` is empty or if the names of the metrics are not unique.

        """

        if len(metrics) == 0:
            raise ValueError(f"No metric is in `metrics` of `EnsembleMetric` {name}.")

        metrics_names = [metric.name for metric in metrics]
        duplicate_names = _get_duplicates(metrics_names)
        if len(duplicate_names) != 0:
            raise ValueError(
                "``metrics`` of ``EnsembleMetric`` must have unique names. "
                f"Found names {metrics_names} in EnsembleMetric {name}."
            )

        super().__init__(
            name=name,
            input_mapping=None,
            num_retries=0,
            on_failure="raise",
        )
        self.metrics = metrics
        self.aggregator = aggregator

    async def compute_metric(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[AggregatedValueType, Dict[str, Any]]:
        results = {m.name: await m(*args, **kwargs) for m in self.metrics}
        value = self.aggregator([value for value, _ in results.values()])
        return value, {"results": results}
