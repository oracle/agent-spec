# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Makes an agent fail loudly when its model will not produce structured output.

``create_agent(response_format=...)`` ties the agent's control flow to getting a
parseable structured response. A model that never produces one fails in one of two
ways, depending on whether the agent has real tools:

* no tools: the agent loops. ``create_agent`` sets ``recursion_limit=9999``, so that is
  thousands of model calls before ``GraphRecursionError``.
* with tools: routing treats a turn with no tool calls as "done", so the agent exits
  with no ``structured_response`` and the declared outputs come back empty, with no
  error at all (upstream langchain issue #36349).

:class:`StructuredOutputGuard` covers both. An agent whose only declared output is a
string avoids the problem entirely, since ``response_format`` is skipped for it (see
:func:`pyagentspec.adapters._utils.is_single_string_output`).
"""

from typing import Any, Dict, List, NoReturn, Optional

from typing_extensions import NotRequired

from pyagentspec.adapters.langgraph._types import AgentMiddleware, AgentState

# A compliant run spends at most one turn without a structured response, so a small
# bound separates "model is working on it" from "model will never comply".
DEFAULT_MAX_STRUCTURED_OUTPUT_ATTEMPTS = 3

# Must match the field on _StructuredOutputAttemptState.
_ATTEMPTS_STATE_KEY = "structured_output_attempts"


class StructuredOutputNotProducedError(RuntimeError):
    """Raised when a model will not produce the structured response an agent declares.

    Subclasses ``RuntimeError`` so existing handlers around agent execution still catch it.
    """


class _StructuredOutputAttemptState(AgentState):
    # On the state rather than the instance, so the count is per run and not shared
    # between concurrent ones.
    structured_output_attempts: NotRequired[int]


class StructuredOutputGuard(AgentMiddleware):
    """Fails an agent that cannot produce the structured output it declares.

    Install only when ``response_format`` is set. Without it, a turn with no tool calls
    just means the agent is done and an empty ``structured_response`` is fine.
    """

    state_schema = _StructuredOutputAttemptState

    def __init__(
        self,
        *,
        agent_name: str,
        output_titles: List[str],
        model_id: str,
        max_attempts: int = DEFAULT_MAX_STRUCTURED_OUTPUT_ATTEMPTS,
    ) -> None:
        super().__init__()
        self.agent_name = agent_name
        self.output_titles = output_titles
        self.model_id = model_id
        self.max_attempts = max_attempts

    def _fail(self, detail: str) -> NoReturn:
        raise StructuredOutputNotProducedError(
            f"Agent {self.agent_name!r} did not produce a structured response matching its "
            f"declared outputs ({', '.join(self.output_titles)}). {detail} Model "
            f"{self.model_id!r} may not support structured output. Declare a single string "
            f"output to get the model's free text instead, or use a model that supports "
            f"structured output."
        )

    # No async variants: LangGraph routes async runs to the sync hooks, and both are pure.
    def after_model(self, state: Any, runtime: Any) -> Optional[Dict[str, int]]:
        messages = state.get("messages") or []
        last = messages[-1] if messages else None
        if last is None or getattr(last, "type", None) != "ai":
            return None
        if getattr(last, "tool_calls", None):
            # A tool call is progress, so the bound applies to consecutive failures only.
            # Under ToolStrategy the structured response is itself a tool call.
            return {_ATTEMPTS_STATE_KEY: 0}
        attempts = (state.get(_ATTEMPTS_STATE_KEY) or 0) + 1
        if attempts >= self.max_attempts:
            self._fail(f"It answered in prose {attempts} times instead.")
        return {_ATTEMPTS_STATE_KEY: attempts}

    def after_agent(self, state: Any, runtime: Any) -> None:
        # after_model never sees the silent case: an agent with tools exits on its first
        # prose turn, well before the bound.
        if "structured_response" in state:
            return None
        self._fail("It ended its run without one.")
