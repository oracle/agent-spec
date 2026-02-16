# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Literal, Sequence, Tuple, TypeVar, cast

from pyagentspec.evaluation._utils import _bind_kwargs_to_func, _map_names
from pyagentspec.evaluation.exceptions import EvaluationException
from pyagentspec.evaluation.exceptions.handling_strategies import (
    ExceptionHandlingStrategy,
    Raise,
    SetConstant,
)

logger = logging.getLogger(__name__)

MetricValueType = TypeVar("MetricValueType")


class Metric(ABC, Generic[MetricValueType]):
    """
    The ``Metric`` class serves as the base for implementing both metrics and metric wrappers.
    To define a custom metric, inherit from this class and implement the ``compute_metric`` method.

    The ``Metric`` class is generically typed.
    The generic type parameter should correspond to the return type of the metric.

    .. warning::
        Do not call the ``compute_metric`` method directly; instead, use the instance itself as it is callable.

    """

    def __init__(
        self,
        name: str,
        input_mapping: Dict[str, str] | None,
        num_retries: int,
        on_failure: Literal["raise", "set_none", "set_zero"] | ExceptionHandlingStrategy,
    ) -> None:
        """
        Parameters
        ----------
        name
            The name of the metric.

        input_mapping
            A mapping from dataset feature names (external) to the names expected by the metric.
            This allows alignment between dataset schemas and metric requirements.
            The mapping can be partial, and extra keys not required by the metric will be ignored.
            Pass ``None`` if no mapping is needed.

        num_retries
            The maximum number of additional attempts to compute the metric after the initial failure.
            A total of 1 + ``num_retries`` attempts will be made.
            Must be a non-negative integer. A value of zero means no retries beyond the first attempt.

        on_failure
            Specifies the behavior if all attempts to compute the metric fail.
            Must be an instance of ``ExceptionHandlingStrategy``. Supported strategies include:
                - ``Raise()``: Propagates the exception.
                - ``SetConstant(val)``: Returns ``val``, typically the lowest possible value for the metric.
                - ``"raise"``: Alias for ``Raise()``.
                - ``"set_none"``: Alias for ``SetConstant(None)``.
                - ``"set_zero"``: Alias for ``SetConstant(0)``.
                - a custom instance of ``ExceptionHandlingStrategy``.

            .. note::
                For production-quality code, it is recommended to use ``SetConstant`` directly, providing a constant that matches the metric's return type (e.g., ``0`` vs ``0.0`` vs ``False``).

            .. warning::
                These strategies handle only ``EvaluationException`` instances.
                Exceptions arising from implementation errors will not be caught.

        """

        _on_failure: ExceptionHandlingStrategy | None
        if on_failure == "raise":
            _on_failure = Raise()
        elif on_failure == "set_none":
            _on_failure = SetConstant(None)
        elif on_failure == "set_zero":
            _on_failure = SetConstant(0)
        else:
            _on_failure = on_failure

        if not isinstance(num_retries, int) or num_retries < 0:
            raise ValueError(
                f"`num_retries` must be a non-negative integer for metric {name}. "
                f"Found {num_retries} instead."
            )

        self.name = name
        self.input_mapping = input_mapping
        self.num_retries = num_retries
        self.on_failure = _on_failure

    @abstractmethod
    async def compute_metric(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[MetricValueType, Dict[str, Any]]:
        """
        Implements the logic for computing the metric.

        Parameters
        ----------
        The method signature can take one of the following forms:
            - Accepts the attributes necessary to compute the metric. For example: ``async def compute_metric(self, reference: str, response: str) -> ...``.
            - May be defined as ``async def compute_metric(self, *args: Any, **kwargs: Any) -> ...`` if the metric serves as a wrapper for other metric(s).

        Raises
        ------
        EvaluationException
            Raised if the evaluation attempt fails for any reason. The exception must include an informative message and the underlying error.
            This method must never return None or a placeholder value.

        Returns
        -------
        value
            The computed value of the metric for the input sample.

        value_details
            Additional information about the value, such as justification, reasoning, or further details.
            Keys with a leading double underscore are reserved for system use.

        .. warning::
            Any value returned by this method is considered a valid metric measurement.
            Never return ``None`` or a placeholder value; instead, raise an ``EvaluationException`` and use the ``on_failure`` strategy.
            If you return a value, retries will not be triggered.

        """

        raise NotImplementedError(
            "Method `compute_metric` must be implemented for any subclass of `Metric`."
        )

    def _process_attempts_result(
        self,
        failed_attempts: Sequence[EvaluationException],
        successful_attempt: Tuple[MetricValueType, Dict[str, Any]] | None,
        computation_details: Dict[str, Any] | None = None,
    ) -> Tuple[MetricValueType | None, Dict[str, Any]]:
        injecting_details = {
            "__failed_attempts": failed_attempts,
            "__computation_details": computation_details,
        }

        if successful_attempt is None:
            return cast(MetricValueType | None, self.on_failure(failed_attempts)), injecting_details

        value, details = successful_attempt
        return value, {**details, **injecting_details}

    async def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[MetricValueType | None, Dict[str, Any]]:
        time_start = time.time()

        if self.input_mapping is not None:
            kwargs = _map_names(kwargs, self.input_mapping)

        bound_args = _bind_kwargs_to_func(self.compute_metric, *args, **kwargs)

        failed_attempts: List[EvaluationException] = []
        for attempt_id in range(1 + self.num_retries):
            try:
                time_attempt_start = time.time()
                val, val_details = await self.compute_metric(*bound_args.args, **bound_args.kwargs)
                time_attempt_end = time.time()

                logger.info(
                    f"Computing {self.name} was successful in {1 + attempt_id}/{1 + self.num_retries} attempt.",
                )

                return self._process_attempts_result(
                    failed_attempts=failed_attempts,
                    successful_attempt=(val, val_details),
                    computation_details={
                        "status": "successful",
                        "time_successful_attempt": time_attempt_end - time_attempt_start,
                        "time_total": time_attempt_end - time_start,
                    },
                )
            except EvaluationException as e:
                logger.error(
                    "Computing %s failed in attempt %d/%d. Caused by: %s",
                    self.name,
                    1 + attempt_id,
                    1 + self.num_retries,
                    e,
                    exc_info=True,
                )
                failed_attempts.append(e)

        logger.error(
            f"Computing {self.name} failed after {1 + self.num_retries} attempts.",
        )

        time_end = time.time()

        return self._process_attempts_result(
            failed_attempts=failed_attempts,
            successful_attempt=None,
            computation_details={
                "status": "failed",
                "time_total": time_end - time_start,
            },
        )
