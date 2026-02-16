# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import re
import warnings
from typing import Any, Callable, Collection, Dict, List, Literal, Tuple, cast

from pyagentspec.adapters._utils import render_template
from pyagentspec.evaluation.exceptions import EvaluationException
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.metrics.llm_based_metric import LlmBasedMetric
from pyagentspec.evaluation.metrics.metrics import MetricValueType
from pyagentspec.llms import LlmConfig
from pyagentspec.templating import get_placeholders_from_string

RESULT_PATTERN = r"<result>(.*?)</result>"
JUSTIFICATION_PATTERN = r"<justification>(.*?)</justification>"


class LlmAsAJudgeMetric(LlmBasedMetric[MetricValueType]):
    """Base class for metrics that rely on an LLM as the judge.

    The ``system_prompt`` encodes the rubric, whereas ``user_prompt_template`` is
    rendered per sample. Subclasses configure regex patterns for extracting the
    final value and optional metadata fields from the LLM response.
    """

    def __init__(
        self,
        name: str,
        input_mapping: Dict[str, str] | None,
        num_retries: int,
        on_failure: Literal["raise", "set_none", "set_zero"] | ExceptionHandlingStrategy,
        llm_config: LlmConfig,
        system_prompt: str,
        user_prompt_template: str,
        value_pattern: str,
        metadata_patterns: Collection[Tuple[str, str]] = tuple(),
        output_transformer: Callable[[Any], MetricValueType] | None = None,
    ) -> None:
        """Configure shared LLM-as-a-judge behavior used by downstream metrics.

        Parameters
        ----------
        name
            Identifier reported in evaluation summaries.
        input_mapping
            Remaps dataset feature names to the placeholders expected by the
            metric. Pass ``None`` to use dataset names directly.
        num_retries
            Number of retry attempts after the initial completion failure.
        on_failure
            Strategy applied if all attempts raise ``EvaluationException``. Can be
            a literal alias or a custom ``ExceptionHandlingStrategy``.
        llm_config
            Configuration for the LLM deployment used to score samples.
            The ``litellm`` package is used for LLM calls.
        system_prompt
            Instruction block sent as the system message.
            Must not contain template placeholders.
        user_prompt_template
            Jinja-formatted prompt rendered per sample.
            Must define at least one placeholder that aligns with ``input_mapping``.
        value_pattern
            Regular expression capturing the metric value from the LLM response.
        metadata_patterns
            Optional (name, pattern) pairs used to extract extra metadata from
            the LLM response.
        output_transformer
            Callable that converts the extracted value string into the metric's
            return type. If ``None``, the raw match is used.
        """
        user_prompt_template_placeholders = get_placeholders_from_string(user_prompt_template)
        system_prompt_placeholders = get_placeholders_from_string(system_prompt)

        if len(user_prompt_template_placeholders) == 0:
            raise ValueError(
                "`user_prompt_template` must include at least one placeholder (in the form of {{ variable }}). "
                "These placeholders allow sample-specific values. Please ensure the user prompt template is properly parameterized. "
                "Without parameters in user prompt template, the LLM will always generate same text, since its input is always the same."
            )

        if len(system_prompt_placeholders) != 0:
            warnings.warn(
                "`system_prompt` is strictly for providing general instructions to the LLM and must NOT contain any placeholders ({{ variable }}). "
                "The system prompt will be passed to the LLM unrendered. Sample-specific variables should be included only in `user_prompt_template`.",
                UserWarning,
            )

        super().__init__(
            name=name,
            input_mapping=input_mapping,
            num_retries=num_retries,
            on_failure=on_failure,
            llm_config=llm_config,
        )
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self._user_prompt_template_placeholders = user_prompt_template_placeholders
        self.value_pattern = value_pattern
        self.metadata_patterns = dict(metadata_patterns)
        self.output_transformer = output_transformer

    def _create_conversation(self, **kwargs: Any) -> List[Dict[str, str]]:
        """Render the prompts into a conversation compatible with chat models."""
        rendered_user_prompt = render_template(
            self.user_prompt_template,
            {
                placeholder: kwargs[placeholder]
                for placeholder in self._user_prompt_template_placeholders
            },
        )
        return [
            {self.ROLE: self.SYSTEM, self.CONTENT: self.system_prompt},
            {self.ROLE: self.USER, self.CONTENT: rendered_user_prompt},
        ]

    def _get_single_match(self, pattern: str, response: str) -> Any:
        """Extract exactly one match for ``pattern`` or raise ``EvaluationException``."""
        matches = re.findall(pattern, response, re.DOTALL)
        if len(matches) == 0:
            raise EvaluationException(
                f"Pattern `{pattern}` not found in llm completion of {self.name}: {response}"
            )
        if len(matches) > 1:
            raise EvaluationException(
                f"Pattern `{pattern}` found more than once in llm-generated response of {self.name}: {response}"
            )
        return matches[0]

    async def compute_metric(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[MetricValueType, Dict[str, Any]]:
        """Ask the LLM to judge the sample and parse the response into value/details."""
        if args:
            raise ValueError(
                f"All arguments to `LlmAsAJudgeMetric.compute_metric` must be passed as keyword arguments. "
                f"However, an instance of '{self.name}' was called with positional arguments: {args}. "
                "Please use keyword arguments corresponding to placeholders in the user prompt template."
            )

        unbound_placeholders = {
            placeholder
            for placeholder in self._user_prompt_template_placeholders
            if placeholder not in kwargs.keys()
        }
        if len(unbound_placeholders) != 0:
            unbound_placeholders_str = ", ".join(sorted(unbound_placeholders))
            raise ValueError(
                f"The following required placeholders for the user prompt template are missing: {unbound_placeholders_str}. "
                "Please provide values for all placeholders as keyword arguments."
            )

        conversation = self._create_conversation(**kwargs)
        llm_completion, (prompt_tokens, completion_tokens) = await self.ask_llm(conversation)
        extracted_value = self._get_single_match(self.value_pattern, llm_completion)
        final_value = (
            self.output_transformer(extracted_value)
            if self.output_transformer is not None
            else cast(MetricValueType, extracted_value)
        )
        generated_details = {
            name: self._get_single_match(pattern, llm_completion)
            for name, pattern in self.metadata_patterns.items()
        }

        return (
            final_value,
            {
                **generated_details,
                "tokens": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                },
            },
        )
