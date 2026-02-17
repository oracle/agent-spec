# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, Sequence, Tuple

from pyagentspec.evaluation._computers import _AsyncCallablesComputer
from pyagentspec.evaluation._utils import _get_duplicates
from pyagentspec.evaluation.datasets import Dataset
from pyagentspec.evaluation.evaluator.evaluation_results import EvaluationResults
from pyagentspec.evaluation.metrics import Metric


class Evaluator:
    """
    Evaluator orchestrates the execution of a set of metrics over input data,
    supporting optional concurrency control.
    """

    def __init__(
        self,
        metrics: Sequence[Metric[Any]],
        max_concurrency: int = -1,
    ) -> None:
        """
        Initializes the Evaluator with a collection of metrics and concurrency settings.

        Parameters
        ----------
        metrics : Sequence[Metric[Any]]
            Sequence of metric instances to be used for evaluation.

        max_concurrency : int, default -1
            Maximum number of concurrent evaluations.
            Defaults to -1, which indicates no concurrency limit.
            Must be -1 or a positive (>= 1) integer.

        Raises
        ------
        ValueError
            - If the list of metrics is empty, or
            - contains duplicate names, or
            - if max_concurrency is invalid (not an integer, or is less than 1 but not -1).

        """

        if len(metrics) == 0:
            raise ValueError("The `metrics` list cannot be empty.")

        non_unique_metrics_names = _get_duplicates([metric.name for metric in metrics])
        if len(non_unique_metrics_names) != 0:
            raise ValueError(
                f"Duplicate metric names detected in `Evaluator`: {non_unique_metrics_names}."
            )

        if not isinstance(max_concurrency, int):
            raise ValueError(
                f"`max_concurrency` of `Evaluator` must be a positive integer. Found {max_concurrency} instead."
            )

        if not (max_concurrency == -1 or max_concurrency >= 1):
            raise ValueError(
                "`max_concurrency` must be -1 (for disabling control) or a positive (>= 1) integer."
            )

        self.metrics = metrics
        self.max_concurrency = max_concurrency

    async def evaluate(self, dataset: Dataset) -> EvaluationResults:
        """Execute every metric against ``dataset`` and collect the results.

        Parameters
        ----------
        dataset : Dataset
            Dataset exposing async ``ids``/``get_sample`` accessors. Each sample must provide the
            features required by the configured metrics.

        Returns
        -------
        EvaluationResults
            Structured view over the metric values and their associated metadata.

        Notes
        -----
        Metrics run concurrently whenever ``max_concurrency`` permits.
        Any :class:`pyagentspec.evaluation.exceptions.EvaluationException` raised by an underlying
        metric propagates to the caller if the metric ``on_failure`` behavior requires to raise.
        """
        computer = _AsyncCallablesComputer[Tuple[Any, Dict[str, Any]]](
            dataset=dataset,
            callables={metric.name: metric for metric in self.metrics},
            max_concurrency=self.max_concurrency,
        )
        results = await computer.run()
        return EvaluationResults(
            results=results,  # type: ignore
            sample_ids=[id_ async for id_ in dataset.ids()],
            metric_names=[metric.name for metric in self.metrics],
        )
