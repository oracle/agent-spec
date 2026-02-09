# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import logging
from typing import Any, Awaitable, Callable, Dict, Literal, Tuple

from pyagentspec.evaluation._utils import _bind_kwargs_to_func
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.metrics.metrics import Metric, MetricValueType

logger = logging.getLogger(__name__)


class _FunctionMetric(Metric[MetricValueType]):
    """Wrap an async function so it behaves like a ``Metric`` instance."""

    def __init__(
        self,
        fn: Callable[..., Awaitable[Tuple[MetricValueType, Dict[str, Any]]]],
        name: str,
        num_retries: int,
        on_failure: Literal["raise", "set_none", "set_zero"] | ExceptionHandlingStrategy,
    ) -> None:
        super().__init__(
            name=name,
            num_retries=num_retries,
            on_failure=on_failure,
            input_mapping=None,
        )
        self.fn = fn

    async def compute_metric(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[MetricValueType, Dict[str, Any]]:
        """Invoke the wrapped function after aligning positional and keyword args."""
        bound_args = _bind_kwargs_to_func(self.fn, *args, **kwargs)
        return await self.fn(*bound_args.args, **bound_args.kwargs)
