# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, Literal, Tuple

from pyagentspec.evaluation._utils import _get_callable_name
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.metrics._function_metric import _FunctionMetric
from pyagentspec.evaluation.metrics.metrics import Metric, MetricValueType

logger = logging.getLogger(__name__)


def metric(
    *args: Any,
    name: str | None = None,
    num_retries: int = 0,
    on_failure: ExceptionHandlingStrategy | Literal["raise", "set_none", "set_zero"] = "raise",
) -> Callable[
    [Callable[..., Awaitable[Tuple[MetricValueType, Dict[str, Any]]]]], Metric[MetricValueType]
]:
    """Convert an async function into a fully-fledged ``Metric`` instance.

    The decorator mirrors the API of the wrapped function. When applied, the
    resulting callable honours the same signature but gains retry and
    exception-handling semantics provided by :class:`Metric`.

    Returns
    -------
    An instance of class ``Metric`` that internally calls the decorated function.
    You can use it as you use the function itself, our you can pass the decorated function as a metric to other functions and methods.
    """

    if args:
        raise TypeError(
            "@metric must be called with parentheses, i.e., @metric(), even if no arguments are provided."
        )

    def _decorator(
        fn: Callable[..., Awaitable[Tuple[MetricValueType, Dict[str, Any]]]],
    ) -> Metric[MetricValueType]:
        """Wrap ``fn`` in :class:`_FunctionMetric` after validating its coroutine nature."""
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("The decorated function must be async (use 'async def').")

        return _FunctionMetric[MetricValueType](
            fn=fn,
            name=name or _get_callable_name(fn),
            num_retries=num_retries,
            on_failure=on_failure,
        )

    return _decorator
