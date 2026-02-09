# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


from typing import Any, Dict, Literal, Tuple

import pytest

from pyagentspec.evaluation.exceptions import EvaluationException
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.metrics import Metric


class _FailingMetric(Metric[int]):

    def __init__(
        self,
        input_mapping: dict[str, str] | None = None,
        num_retries: int = 1,
        on_failure: Literal["raise", "set_none", "set_zero"] | ExceptionHandlingStrategy = "raise",
    ) -> None:
        super().__init__(
            name="failing",
            input_mapping=input_mapping,
            num_retries=num_retries,
            on_failure=on_failure,
        )

    async def compute_metric(self, value: int) -> Tuple[int, Dict[str, Any]]:
        raise EvaluationException("boom")


@pytest.mark.anyio
async def test_metric_raise_on_failure_strategy():
    metric = _FailingMetric(on_failure="raise")
    with pytest.raises(EvaluationException):
        await metric(value=1)


@pytest.mark.anyio
async def test_metric_set_none_on_failure_strategy():
    metric = _FailingMetric(on_failure="set_none")
    value, extra = await metric(value=1)
    assert value is None


@pytest.mark.anyio
async def test_metric_set_zero_on_failure_strategy():
    metric = _FailingMetric(on_failure="set_zero")
    value, extra = await metric(value=1)
    assert value == 0
