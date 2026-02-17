# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Tests covering the public evaluator API surface."""

from typing import Any, Dict, Tuple

import pytest

from pyagentspec.evaluation import Dataset, EvaluationResults, Evaluator
from pyagentspec.evaluation.metrics import Metric, metric

from .metrics.test_failing_metrics import _FailingMetric


class _EchoMetric(Metric[int]):
    """Simple metric returning the provided integer feature."""

    def __init__(self) -> None:
        super().__init__(name="echo", input_mapping=None, num_retries=0, on_failure="raise")

    async def compute_metric(self, value: int) -> Tuple[int, Dict[str, Any]]:
        return value, {"seen": value}


@metric()
async def decorated_metric(value: int) -> Tuple[int, Dict[str, Any]]:
    """Return the received value to exercise the decorator wrapper."""
    return value * 2, {"doubled": True}


@pytest.fixture()
def dataset() -> Dataset:
    import pandas as pd

    df = pd.DataFrame({"value": [1, 2, 3]})
    return Dataset.from_df(df)


@pytest.mark.anyio
async def test_evaluator_success_paths(dataset: Dataset) -> None:
    import pandas as pd

    evaluator = Evaluator(metrics=[_EchoMetric(), decorated_metric])

    results = await evaluator.evaluate(dataset)

    assert isinstance(results, EvaluationResults)
    assert results.sample_ids == [0, 1, 2]
    assert results.metric_names == ["echo", "decorated_metric"]

    results_dict = results.to_dict()
    assert results_dict[0]["echo"]["value"] == 1
    assert results_dict[0]["decorated_metric"]["value"] == 2
    assert results_dict[1]["echo"]["value"] == 2
    assert results_dict[1]["decorated_metric"]["value"] == 4
    details = results_dict[2]["decorated_metric"]["details"]
    assert details["doubled"] is True

    df = results.to_df()
    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame({"echo": [1, 2, 3], "decorated_metric": [2, 4, 6]}, index=pd.Index([0, 1, 2])),
    )


@pytest.mark.anyio
async def test_evaluator_handles_failures_with_strategy(dataset: Dataset) -> None:
    evaluator = Evaluator(metrics=[_FailingMetric(on_failure="set_zero", num_retries=1)])
    for (sample_id, metric_name), (value, details) in (
        await evaluator.evaluate(dataset)
    ).results.items():
        assert metric_name == "failing"
        assert value == 0
        assert "__failed_attempts" in details and "__computation_details" in details
        assert details["__computation_details"]["status"] == "failed"
        assert len(details["__failed_attempts"]) == 2


@pytest.mark.anyio
async def test_evaluator_exports_failures_to_dict(dataset: Dataset) -> None:
    evaluator = Evaluator(metrics=[_FailingMetric(on_failure="set_zero", num_retries=1)])
    results = await evaluator.evaluate(dataset)

    results_dict = results.to_dict()
    assert set(results_dict.keys()) == {0, 1, 2}

    for sample_id in results_dict:
        failing = results_dict[sample_id]["failing"]
        assert failing["value"] == 0
        assert failing["details"]["__computation_details"]["status"] == "failed"
        assert len(failing["details"]["__failed_attempts"]) == 2


def test_evaluator_validation_errors(dataset: Dataset) -> None:

    with pytest.raises(ValueError, match="cannot be empty"):
        Evaluator(metrics=[])

    metric_instance = _EchoMetric()
    with pytest.raises(ValueError, match="Duplicate metric names"):
        Evaluator(metrics=[metric_instance, metric_instance])

    with pytest.raises(ValueError, match=r"must be -1 \(for disabling control\) or a positive"):
        Evaluator(metrics=[metric_instance], max_concurrency=-2)

    with pytest.raises(ValueError, match="must be a positive integer"):
        Evaluator(metrics=[metric_instance], max_concurrency=1.5)

    evaluator = Evaluator(metrics=[metric_instance], max_concurrency=1)
    assert evaluator.max_concurrency == 1
    assert evaluator.metrics[0].name == "echo"
