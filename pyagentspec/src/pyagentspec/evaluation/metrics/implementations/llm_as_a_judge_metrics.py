# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import textwrap
from typing import Literal

from pyagentspec.evaluation.exceptions import EvaluationException
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.metrics.llm_as_a_judge_metric import (
    JUSTIFICATION_PATTERN,
    RESULT_PATTERN,
    LlmAsAJudgeMetric,
)
from pyagentspec.llms import LlmConfig


def transform_yes_no_str_to_boolean(v: str) -> bool:
    v = v.lower().strip()
    if v == "yes":
        return True
    if v == "no":
        return False
    raise EvaluationException("unexpected answer generation from LLM.")


class SemanticBinaryMatchMetric(LlmAsAJudgeMetric[bool]):
    """Evaluate whether a response matches a reference semantically as a binary decision."""

    SYSTEM_PROMPT = textwrap.dedent(
        """
        You are an evaluator who determines if a response refers to the same entity or concept as a given reference, using these criteria:
        - The response and the reference must represent the same entity or concept (for example, the same city, person, or term).
        - Accept minor spelling or linguistic differences, such as typographical errors, alternate spellings, or translations (e.g., "Geneva", "Genève", and "Genf").
        - Do not accept the response if it refers to a different entity or concept, even if the spelling is very similar.
        - Be precise: Only confirm a match if both clearly refer to the same thing.

        For each evaluation, first provide a brief justification, then your final decision in the following XML format:
        <justification>[Brief explanation]</justification>
        <result>Yes/No</result>
        """
    )

    USER_PROMPT_TEMPLATE = textwrap.dedent(
        """
        Reference:
        {{ reference }}

        Response:
        {{ response }}
        """
    )

    def __init__(
        self,
        llm_config: LlmConfig,
        name: str = "SemanticBinaryMatch",
        reference_feature_name: str = "reference",
        response_feature_name: str = "response",
        num_retries: int = 0,
        on_failure: ExceptionHandlingStrategy | Literal["raise", "set_none", "set_zero"] = "raise",
    ) -> None:
        """
        Initialize the metric with prompt templates, field mappings, and retry behavior.

        Parameters
        ----------
        name
            Display name registered for the metric instance.
        llm_config
            Configuration for the LLM deployment used to score samples.
        reference_feature_name
            Dataset feature name mapped to the reference string input.
        response_feature_name
            Dataset feature name mapped to the response string input.
        num_retries
            Number of times to retry the metric in case of failure.
        on_failure
            Failure strategy to adopt if the max number of retries is exceeded.
        """
        super().__init__(
            name=name,
            input_mapping={
                reference_feature_name: "reference",
                response_feature_name: "response",
            },
            num_retries=num_retries,
            on_failure=on_failure,
            llm_config=llm_config,
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt_template=self.USER_PROMPT_TEMPLATE,
            value_pattern=RESULT_PATTERN,
            metadata_patterns=(("justification", JUSTIFICATION_PATTERN),),
            output_transformer=transform_yes_no_str_to_boolean,
        )
