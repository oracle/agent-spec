# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.property import Property
from pyagentspec.tools import ClientTool


class _StopCreateAgent(Exception):
    """Raised inside the ``create_agent`` spy to short-circuit graph compilation.

    The kwarg-capture tests only care about what ``create_agent`` is called
    with; letting the real call proceed would require valid LangChain
    middleware instances, which these tests deliberately do not construct.
    """


def _spy_create_agent(captured: Dict[str, Any]) -> Callable[..., Any]:
    def spy(**kwargs: Any) -> Any:
        captured.update(kwargs)
        raise _StopCreateAgent()

    return spy


@pytest.fixture
def agent() -> Agent:
    return Agent(
        name="agent",
        system_prompt="You are a helpful agent.",
        llm_config=OpenAiCompatibleConfig(name="llm", model_id="fake", url="null"),
        tools=[
            ClientTool(
                name="ask_user",
                description="Ask the user something",
                inputs=[Property(title="question", json_schema={"type": "string"})],
                outputs=[Property(title="answer", json_schema={})],
            )
        ],
    )


@pytest.fixture
def agent_flow(agent: Agent) -> Flow:
    start_node = StartNode(name="start")
    agent_node = AgentNode(name="agent_node", agent=agent)
    end_node = EndNode(name="end")
    return Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, agent_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_agent", from_node=start_node, to_node=agent_node),
            ControlFlowEdge(name="agent_to_end", from_node=agent_node, to_node=end_node),
        ],
        data_flow_connections=[],
    )


@pytest.fixture
def capture_create_agent_kwargs(
    agent: Agent,
) -> Callable[[Optional[List[Any]]], Dict[str, Any]]:
    """Return a callable that drives a conversion and returns the kwargs ``create_agent`` saw."""

    def _capture(middleware: Optional[List[Any]]) -> Dict[str, Any]:
        from langgraph.checkpoint.memory import MemorySaver

        from pyagentspec.adapters.langgraph._langgraphconverter import (
            AgentSpecToLangGraphConverter,
        )
        from pyagentspec.adapters.langgraph._types import langchain_agents

        captured: Dict[str, Any] = {}
        with patch.object(langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)):
            loader = AgentSpecToLangGraphConverter()
            with pytest.raises(_StopCreateAgent):
                loader.convert(
                    agent,
                    tool_registry={},
                    converted_components={agent.llm_config.id: object()},
                    checkpointer=MemorySaver(),
                    middleware=middleware,
                )
        return captured

    return _capture


@pytest.mark.parametrize(
    "middleware",
    [None, []],
    ids=["none", "empty_list"],
)
def test_omits_middleware_kwarg_when_not_provided(
    capture_create_agent_kwargs: Callable[[Optional[List[Any]]], Dict[str, Any]],
    middleware: Optional[List[Any]],
) -> None:
    """``AgentSpecLoader()`` without ``middleware`` (or with empty list) must not pass ``middleware=``."""
    captured = capture_create_agent_kwargs(middleware)
    assert "middleware" not in captured


def test_middleware_forwarded_in_order(
    capture_create_agent_kwargs: Callable[[Optional[List[Any]]], Dict[str, Any]],
) -> None:
    """A non-empty list reaches ``create_agent`` in the original order."""
    a, b = object(), object()
    captured = capture_create_agent_kwargs([a, b])
    assert captured.get("middleware") == [a, b]


def test_middleware_list_is_copied(
    agent: Agent,
) -> None:
    """Mutating the caller's list after construction must not leak into conversions."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter
    from pyagentspec.adapters.langgraph._types import langchain_agents

    a = object()
    caller_list: List[Any] = [a]
    loader = AgentSpecLoader(checkpointer=MemorySaver(), middleware=caller_list)
    caller_list.append(object())
    caller_list[0] = object()

    captured: Dict[str, Any] = {}
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        return_value=object(),
    ), patch.object(langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)):
        with pytest.raises(_StopCreateAgent):
            loader.load_component(agent)

    assert captured.get("middleware") == [a]


def test_middleware_forwarded_through_flow_agent_node(agent_flow: Flow) -> None:
    """Middleware must reach ``create_agent`` for agents inside flows."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
    from pyagentspec.adapters.langgraph._types import langchain_agents

    agent_llm_id = agent_flow.nodes[1].agent.llm_config.id  # type: ignore[union-attr]
    captured: Dict[str, Any] = {}
    sentinel = object()
    checkpointer = MemorySaver()
    compiled = AgentSpecToLangGraphConverter().convert(
        agent_flow,
        tool_registry={},
        converted_components={agent_llm_id: object()},
        checkpointer=checkpointer,
        middleware=[sentinel],
    )

    with patch.object(langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)):
        # Triggering execution of the AgentNode lazily compiles the inner agent,
        # which is where the middleware kwarg is forwarded.
        with pytest.raises(_StopCreateAgent):
            compiled.invoke(
                {"inputs": {}, "messages": [{"role": "user", "content": ""}]},
                config={"configurable": {"thread_id": "flow-mw-regression"}},
            )

    assert captured.get("middleware") == [sentinel]


def test_middleware_hook_runs_for_flow_agent_node(agent_flow: Flow) -> None:
    """Execution: a middleware instance threaded through a flow's AgentNode is actually invoked.

    A real ``AgentMiddleware`` subclass records each ``before_agent`` call; the
    LLM is injected via ``converted_components`` so we never hit the network
    and the agent finishes after a single ``AIMessage``.
    """
    from langchain.agents.middleware import AgentMiddleware
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    class _FakeModel(FakeMessagesListChatModel):
        def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
            return self

    fake_model = _FakeModel(responses=[AIMessage(content="Done")])

    calls: List[str] = []

    class _RecordingMiddleware(AgentMiddleware):
        def before_agent(self, state: Any, runtime: Any) -> None:  # type: ignore[override]
            calls.append("before_agent")

    middleware_instance = _RecordingMiddleware()
    agent_llm_id = agent_flow.nodes[1].agent.llm_config.id  # type: ignore[union-attr]
    checkpointer = MemorySaver()

    compiled = AgentSpecToLangGraphConverter().convert(
        agent_flow,
        tool_registry={},
        converted_components={agent_llm_id: fake_model},
        checkpointer=checkpointer,
        middleware=[middleware_instance],
    )
    compiled.invoke(
        {"inputs": {}, "messages": [{"role": "user", "content": "hi"}]},
        config={"configurable": {"thread_id": "flow-mw-execution"}},
    )

    assert calls == ["before_agent"]
