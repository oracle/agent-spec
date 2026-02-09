# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence

from pyagentspec.evaluation._utils import _chain_exceptions
from pyagentspec.evaluation.exceptions import EvaluationException


class ExceptionHandlingStrategy(ABC):
    """Base class of exception handling strategies."""

    @abstractmethod
    def __call__(self, failed_attempts: Sequence[EvaluationException]) -> Any:
        pass


class Raise(ExceptionHandlingStrategy):
    """
    Let the exception(s) to go through the call stack by raising a chain of exceptions caused by them.
    """

    def __call__(self, failed_attempts: Sequence[EvaluationException]) -> Any:
        raise _chain_exceptions(
            [
                *failed_attempts,
                EvaluationException(
                    f"Metric computation failed after {len(failed_attempts)} attempts."
                ),
            ]
        )


@dataclass(frozen=True)
class SetConstant(ExceptionHandlingStrategy):
    """Fill the value of the metric with a constant value."""

    value: Any

    def __call__(self, failed_attempts: Sequence[EvaluationException]) -> Any:
        return self.value
