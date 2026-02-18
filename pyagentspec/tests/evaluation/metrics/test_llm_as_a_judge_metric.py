# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from contextlib import contextmanager

import pytest

from pyagentspec.evaluation.exceptions import EvaluationException
from pyagentspec.evaluation.metrics.implementations.llm_as_a_judge_metrics import (
    SemanticBinaryMatchMetric,
)
from pyagentspec.evaluation.metrics.llm_as_a_judge_metric import LlmAsAJudgeMetric


@contextmanager
def patch_metric_complete_conversation(metric: LlmAsAJudgeMetric, response: str):
    """Patch ``metric`` so that ``ask_llm`` returns ``response`` without network calls."""

    async def patched_complete_conversation(conversation):
        return {
            "choices": [{"message": {"content": response}}],
            "usage": {"completion_tokens": 2, "prompt_tokens": 1},
        }

    original_complete_conversation = metric._complete_conversation
    metric._complete_conversation = patched_complete_conversation
    try:
        yield
    finally:
        metric._complete_conversation = original_complete_conversation


@pytest.fixture()
def llm_as_judge_metric(big_llm_config) -> LlmAsAJudgeMetric:
    return LlmAsAJudgeMetric(
        name="dummy",
        input_mapping=None,
        num_retries=0,
        on_failure="raise",
        llm_config=big_llm_config,
        system_prompt="You judge stuff.",
        user_prompt_template="Score: {{ score }}",
        value_pattern=r"<result>(.*?)</result>",
    )


@pytest.mark.anyio
async def test_compute_metric_parses_value_and_details(llm_as_judge_metric):
    with patch_metric_complete_conversation(llm_as_judge_metric, "<result>42</result>"):
        value, details = await llm_as_judge_metric(score="irrelevant")

    assert value == "42"
    assert details["tokens"] == {"prompt_tokens": 1, "completion_tokens": 2}
    assert details["__failed_attempts"] == []
    assert details["__computation_details"]["status"] == "successful"


@pytest.mark.anyio
async def test_create_conversation_renders_placeholders(llm_as_judge_metric):
    conversation = llm_as_judge_metric._create_conversation(score="99")
    assert conversation == [
        {
            llm_as_judge_metric.ROLE: llm_as_judge_metric.SYSTEM,
            llm_as_judge_metric.CONTENT: "You judge stuff.",
        },
        {
            llm_as_judge_metric.ROLE: llm_as_judge_metric.USER,
            llm_as_judge_metric.CONTENT: "Score: 99",
        },
    ]


@pytest.mark.anyio
async def test_multiple_pattern_matches_raise_evaluation_exception(llm_as_judge_metric):
    payload = "<result>ok</result><result>nope</result>"
    with patch_metric_complete_conversation(llm_as_judge_metric, payload):
        with pytest.raises(EvaluationException):
            await llm_as_judge_metric(score="valid")


@pytest.mark.anyio
async def test_semantic_binary_match_metric_parses_boolean_and_metadata(big_llm_config):
    metric = SemanticBinaryMatchMetric(llm_config=big_llm_config)

    response_payload = (
        "<justification>Names match ignoring accent.</justification>" "<result>Yes</result>"
    )

    with patch_metric_complete_conversation(metric, response_payload):
        value, details = await metric(reference="Genf", response="Geneva")

    assert value is True
    assert details["justification"] == "Names match ignoring accent."
    assert details["tokens"] == {"prompt_tokens": 1, "completion_tokens": 2}


@pytest.mark.anyio
async def test_semantic_binary_match_metric_runs_with_real_llm(big_llm_config):
    metric = SemanticBinaryMatchMetric(llm_config=big_llm_config)
    value, details = await metric(reference="Geneva", response="Genf")
    assert isinstance(value, bool)
    assert isinstance(details, dict)
