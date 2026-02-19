# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, List, Literal, Tuple

from pyagentspec.evaluation._llm import complete_conversation
from pyagentspec.evaluation.exceptions.handling_strategies import ExceptionHandlingStrategy
from pyagentspec.evaluation.metrics.metrics import Metric, MetricValueType
from pyagentspec.llms import LlmConfig


class LlmBasedMetric(Metric[MetricValueType]):
    """Metric base class for scoring via a Language Model invocation."""

    CONTENT = "content"
    """Key for content in an LLM conversation."""
    ROLE = "role"
    """Key for role in an LLM conversation."""
    SYSTEM = "system"
    """System role in an LLM conversation."""
    USER = "user"
    """User role in an LLM conversation."""

    def __init__(
        self,
        name: str,
        input_mapping: Dict[str, str] | None,
        num_retries: int,
        on_failure: Literal["raise", "set_none", "set_zero"] | ExceptionHandlingStrategy,
        llm_config: LlmConfig,
    ) -> None:
        super().__init__(
            name=name,
            input_mapping=input_mapping,
            num_retries=num_retries,
            on_failure=on_failure,
        )
        self.llm_config = llm_config

    async def _complete_conversation(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send ``conversation`` to the configured LLM and return the raw payload."""
        return await complete_conversation(conversation, self.llm_config)

    async def ask_llm(self, conversation: List[Dict[str, str]]) -> Tuple[str, Tuple[int, int]]:
        """Return the assistant message text and token usage from the LLM provider."""
        response = await self._complete_conversation(conversation)
        if "choices" not in response or len(response["choices"]) == 0:
            raise RuntimeError(
                f"LLM returned an empty response during the computation of {self.name}"
            )
        return (
            response["choices"][0]["message"]["content"],
            (response["usage"]["prompt_tokens"], response["usage"]["completion_tokens"]),
        )
