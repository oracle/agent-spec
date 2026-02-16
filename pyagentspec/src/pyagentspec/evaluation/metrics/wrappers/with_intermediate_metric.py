# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, Literal, Sequence, Tuple

from pyagentspec.evaluation._utils import _get_duplicates
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.intermediates import Intermediate
from pyagentspec.evaluation.metrics.metrics import Metric, MetricValueType


class WithIntermediatesMetric(Metric[MetricValueType | None]):
    """Compute a metric after injecting intermediate values.

    This wrapper runs one or more ``Intermediate`` callables first, merges their outputs into
    the keyword arguments passed to the wrapped metric, and then executes the wrapped metric.

    Intermediate values are only computed if their ``name`` is not already present in ``kwargs``.
    The returned ``details`` dictionary is augmented with an ``"__intermediates"``
    entry containing the computed intermediate values.

    .. note::
        - Intermediate names must be unique; duplicates raise ``ValueError``.
        - The wrapper is typed as ``Metric[MetricValueType | None]`` to accommodate failure
          strategies that may set the value to ``None``.

    """

    def __init__(
        self,
        intermediates: Sequence[Intermediate[Any]],
        metric: Metric[MetricValueType],
        input_mapping: Dict[str, str] | None,
        num_retries: int,
        on_failure: ExceptionHandlingStrategy | Literal["raise", "set_none", "set_zero"],
        name: str | None = None,
    ) -> None:
        duplicate_intermediates_names = _get_duplicates(
            [intermediate.name for intermediate in intermediates]
        )
        if len(duplicate_intermediates_names) != 0:
            raise ValueError(
                f"Duplicate intermediate names detected: {duplicate_intermediates_names}."
            )

        super().__init__(
            name=name or metric.name,
            input_mapping=input_mapping,
            num_retries=num_retries,
            on_failure=on_failure,
        )
        self.intermediates = intermediates
        self.metric = metric

    async def compute_metric(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[MetricValueType | None, Dict[str, Any]]:
        intermediates_values = {
            intermediate.name: (await intermediate(*args, **kwargs))[0]
            for intermediate in self.intermediates
            if intermediate.name not in kwargs
        }
        combined_kwargs = {**kwargs, **intermediates_values}
        value, details = await self.metric(*args, **combined_kwargs)
        return value, {**details, "__intermediates": intermediates_values}
