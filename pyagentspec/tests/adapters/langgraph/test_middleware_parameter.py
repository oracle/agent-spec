# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Callable, Dict, List
from unittest.mock import patch

import pytest

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
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
def agent_spec() -> Agent:
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
def agent_flow(agent_spec: Agent) -> Flow:
    start_node = StartNode(name="start")
    agent_node = AgentNode(name="agent_node", agent=agent_spec)
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
    agent_spec: Agent,
) -> Callable[[Callable[[Any], Any]], Dict[str, Any]]:
    """Return a callable that drives a load and returns the kwargs ``create_agent`` saw."""

    def _capture(loader_factory: Callable[[Any], Any]) -> Dict[str, Any]:
        from langgraph.checkpoint.memory import MemorySaver

        from pyagentspec.adapters.langgraph._langgraphconverter import (
            AgentSpecToLangGraphConverter,
        )
        from pyagentspec.adapters.langgraph._types import langchain_agents

        captured: Dict[str, Any] = {}
        with patch.object(
            AgentSpecToLangGraphConverter,
            "_llm_convert_to_langgraph",
            return_value=object(),
        ), patch.object(langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)):
            loader_or_converter = loader_factory(MemorySaver())
            with pytest.raises(_StopCreateAgent):
                loader_or_converter.load_component(agent_spec)
        return captured

    return _capture


def test_default_omits_middleware_kwarg(
    capture_create_agent_kwargs: Callable[[Callable[[Any], Any]], Dict[str, Any]],
) -> None:
    """``AgentSpecLoader()`` without ``middleware`` must not pass ``middleware=``."""
    captured = capture_create_agent_kwargs(lambda cp: AgentSpecLoader(checkpointer=cp))
    assert "middleware" not in captured


def test_empty_list_omits_middleware_kwarg(
    capture_create_agent_kwargs: Callable[[Callable[[Any], Any]], Dict[str, Any]],
) -> None:
    """Passing an empty list is treated the same as omitting the parameter."""
    captured = capture_create_agent_kwargs(
        lambda cp: AgentSpecLoader(checkpointer=cp, middleware=[])
    )
    assert "middleware" not in captured


def test_middleware_forwarded_in_order(
    capture_create_agent_kwargs: Callable[[Callable[[Any], Any]], Dict[str, Any]],
) -> None:
    """A non-empty list reaches ``create_agent`` in the original order."""
    a, b = object(), object()
    captured = capture_create_agent_kwargs(
        lambda cp: AgentSpecLoader(checkpointer=cp, middleware=[a, b])
    )
    assert captured.get("middleware") == [a, b]


def test_converter_accepts_middleware_directly(agent_spec: Agent) -> None:
    """A list passed directly to the converter reaches ``create_agent``."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
    from pyagentspec.adapters.langgraph._types import langchain_agents

    captured: Dict[str, Any] = {}
    sentinel = object()
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        return_value=object(),
    ), patch.object(langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)):
        converter = AgentSpecToLangGraphConverter(middleware=[sentinel])
        with pytest.raises(_StopCreateAgent):
            converter.convert(
                agent_spec,
                tool_registry={},
                checkpointer=MemorySaver(),
            )
    assert captured.get("middleware") == [sentinel]


def test_middleware_list_is_copied(
    capture_create_agent_kwargs: Callable[[Callable[[Any], Any]], Dict[str, Any]],
) -> None:
    """Mutating the caller's list after construction must not leak into conversions."""
    a = object()
    caller_list: List[Any] = [a]

    def make_loader(cp: Any) -> AgentSpecLoader:
        loader = AgentSpecLoader(checkpointer=cp, middleware=caller_list)
        # Post-construction mutation must not affect the loader's behavior.
        caller_list.append(object())
        caller_list[0] = object()
        return loader

    captured = capture_create_agent_kwargs(make_loader)
    assert captured.get("middleware") == [a]


def test_middleware_forwarded_through_flow_agent_node(agent_flow: Flow) -> None:
    """Regression: middleware must reach ``create_agent`` for agents inside flows.

    Before this fix, ``AgentNodeExecutor`` instantiated a fresh
    ``AgentSpecToLangGraphConverter()`` (no middleware), so any middleware
    configured on the outer ``AgentSpecLoader`` was silently dropped for
    agents embedded in flows.
    """
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
    from pyagentspec.adapters.langgraph._types import langchain_agents

    captured: Dict[str, Any] = {}
    sentinel = object()
    compiled = AgentSpecLoader(checkpointer=MemorySaver(), middleware=[sentinel]).load_component(
        agent_flow
    )

    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        return_value=object(),
    ), patch.object(langchain_agents, "create_agent", side_effect=_spy_create_agent(captured)):
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
    LLM is faked via the shared ``make_fake_chat_model`` helper so we never hit
    the network and the agent finishes after a single ``AIMessage``.
    """
    from langchain.agents.middleware import AgentMiddleware
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )

    from .conftest import make_fake_chat_model

    fake_model = make_fake_chat_model(responses=[AIMessage(content="Done")])

    calls: List[str] = []

    class _RecordingMiddleware(AgentMiddleware):
        def before_agent(self, state: Any, runtime: Any) -> None:  # type: ignore[override]
            calls.append("before_agent")

    with patch.object(
        AgentSpecToLangGraphConverter, "_llm_convert_to_langgraph", return_value=fake_model
    ):
        compiled = AgentSpecLoader(
            checkpointer=MemorySaver(), middleware=[_RecordingMiddleware()]
        ).load_component(agent_flow)
        compiled.invoke(
            {"inputs": {}, "messages": [{"role": "user", "content": "hi"}]},
            config={"configurable": {"thread_id": "flow-mw-execution"}},
        )

    assert calls == ["before_agent"]
