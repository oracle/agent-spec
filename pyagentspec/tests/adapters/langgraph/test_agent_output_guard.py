# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""How :class:`StructuredOutputGuard` bounds an agent that declares structured output.

These build no LLM config, so unlike the AgentNode flow tests they run rather than skip
under ``SKIP_LLM_TESTS=1``.
"""

from typing import Any, get_args

import pytest

from pyagentspec.adapters.langgraph._agent_output_guard import (
    StructuredOutputGuard,
    StructuredOutputNotProducedError,
)

# ─── after_model budget ───────────────────────────────────────────────────────


def _guard(max_attempts: int = 3) -> StructuredOutputGuard:
    return StructuredOutputGuard(
        agent_name="researcher",
        output_titles=["summary", "confidence"],
        model_id="some-model",
        max_attempts=max_attempts,
    )


def _prose(attempts: int = 0) -> dict:
    """A model turn that answered in prose, so no structured response."""
    from langchain_core.messages import AIMessage, HumanMessage

    return {
        "messages": [HumanMessage(content="q"), AIMessage(content="42")],
        "_pyagentspec_structured_output_attempts": attempts,
    }


def _tool_turn(attempts: int = 0) -> dict:
    from langchain_core.messages import AIMessage

    return {
        "messages": [AIMessage(content="", tool_calls=[{"name": "s", "args": {}, "id": "c1"}])],
        "_pyagentspec_structured_output_attempts": attempts,
    }


def test_prose_turn_increments_until_the_limit() -> None:
    """Prose never satisfies response_format, so the agent cannot exit on its own."""
    guard = _guard(max_attempts=3)

    assert guard.after_model(_prose(0), runtime=None) == {
        "_pyagentspec_structured_output_attempts": 1
    }
    assert guard.after_model(_prose(1), runtime=None) == {
        "_pyagentspec_structured_output_attempts": 2
    }
    with pytest.raises(StructuredOutputNotProducedError):
        guard.after_model(_prose(2), runtime=None)


def test_error_message_names_agent_fields_and_model() -> None:
    """Failing fast is only useful if the message says what to change."""
    with pytest.raises(StructuredOutputNotProducedError) as excinfo:
        _guard(max_attempts=1).after_model(_prose(), runtime=None)

    message = str(excinfo.value)
    assert "researcher" in message
    assert "summary, confidence" in message
    assert "some-model" in message
    # It should point at the actionable escape hatch, not just complain.
    assert "single string output" in message


def test_tool_calling_turn_resets_rather_than_counting() -> None:
    """A tool call is progress. Under ToolStrategy the structured response is itself a
    tool call, so counting these would fail every compliant agent. The reset also keeps a
    long run of mixed prose and tool calls from adding up to a false failure."""
    guard = _guard(max_attempts=2)
    # max_attempts=2 with 1 attempt already banked would raise if this counted.
    assert guard.after_model(_tool_turn(attempts=1), runtime=None) == {
        "_pyagentspec_structured_output_attempts": 0
    }


def test_non_ai_or_empty_last_message_is_ignored() -> None:
    """Only a model turn can be a failed structured response."""
    from langchain_core.messages import ToolMessage

    guard = _guard(max_attempts=1)
    assert guard.after_model({"messages": []}, runtime=None) is None
    assert guard.after_model({}, runtime=None) is None
    assert (
        guard.after_model({"messages": [ToolMessage(content="r", tool_call_id="c1")]}, runtime=None)
        is None
    )


@pytest.mark.anyio
async def test_budget_applies_on_async_runs_via_the_sync_hook() -> None:
    """The guard has no ``aafter_model`` and relies on LangGraph routing async runs to the
    sync hook. Agents do run async, so a silent no-op there would bring the hang back."""
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage, HumanMessage
    from pydantic import BaseModel

    class _Answer(BaseModel):
        summary: str
        confidence: str

    class _ProseOnlyModel(GenericFakeChatModel):
        """Accepts the structured-output tool binding, then ignores it."""

        def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
            return self

    # A model that only ever answers in prose, so no structured response is produced.
    # `response_format` is what makes that a hang rather than a clean exit.
    model = _ProseOnlyModel(messages=iter([AIMessage(content="42")] * 50))
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt="Answer.",
        response_format=_Answer,
        middleware=[_guard(max_attempts=3)],
    )

    with pytest.raises(StructuredOutputNotProducedError):
        await agent.ainvoke({"messages": [HumanMessage(content="6*7?")]})


# ─── after_agent: the silent-exit case the budget cannot see ──────────────────


def test_after_agent_accepts_a_run_that_produced_the_response() -> None:
    """The guard has to stay out of the way of a compliant agent."""
    assert _guard().after_agent({"structured_response": object()}, runtime=None) is None


def test_after_agent_rejects_a_run_that_produced_nothing() -> None:
    """An agent with tools exits after one prose turn, spending no budget, so this hook is
    the only place that failure shows up."""
    from langchain_core.messages import AIMessage

    with pytest.raises(StructuredOutputNotProducedError) as excinfo:
        _guard().after_agent({"messages": [AIMessage(content="42")]}, runtime=None)

    message = str(excinfo.value)
    assert "researcher" in message
    assert "summary, confidence" in message
    assert "some-model" in message
    assert "single string output" in message


def test_agent_with_tools_raises_instead_of_losing_outputs_silently() -> None:
    """Regression for langchain#36349. With at least one real tool, routing treats a
    turn with no tool calls as "done", so the agent used to return no
    ``structured_response`` and the declared outputs came back empty."""
    from langchain.agents import create_agent
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.tools import tool
    from pydantic import BaseModel

    class _Answer(BaseModel):
        summary: str
        confidence: str

    @tool
    def search(q: str) -> str:
        """Search for something."""
        return "a result"

    class _ProseOnlyModel(GenericFakeChatModel):
        def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
            return self

    model = _ProseOnlyModel(messages=iter([AIMessage(content="42")] * 50))
    agent = create_agent(
        model=model,
        tools=[search],
        system_prompt="Answer.",
        response_format=_Answer,
        middleware=[_guard()],
    )

    with pytest.raises(StructuredOutputNotProducedError, match="ended its run without one"):
        agent.invoke({"messages": [HumanMessage(content="6*7?")]})


def test_limiter_state_schema_declares_the_counter() -> None:
    """The counter belongs on the state schema, not the instance, so concurrent runs do
    not share it."""
    from langchain.agents.middleware.types import PrivateStateAttr

    schema: Any = _guard().state_schema
    key = "_pyagentspec_structured_output_attempts"
    assert key in schema.__annotations__
    assert key in schema.__optional_keys__
    assert PrivateStateAttr in get_args(get_args(schema.__annotations__[key])[0])
