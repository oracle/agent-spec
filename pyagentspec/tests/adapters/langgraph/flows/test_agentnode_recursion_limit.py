# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""The agent of a Flow ``AgentNode`` honours the recursion limit of the enclosing run.

``create_agent`` binds ``recursion_limit=9999`` to the agents it compiles. Without the
fix, an agent that never terminates inside a flow made thousands of model calls before
failing, even when the flow run was invoked with a small ``recursion_limit``
(oracle/agent-spec#227).
"""

from contextlib import contextmanager
from typing import Any, Iterator, List
from unittest.mock import patch

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import LlmConfig
from pyagentspec.property import IntegerProperty
from pyagentspec.tools import ServerTool

MULTIPLICATION_TOOL = ServerTool(
    name="multiplication_tool",
    description="Multiplies two integers",
    inputs=[IntegerProperty(title="a"), IntegerProperty(title="b")],
    outputs=[IntegerProperty(title="result")],
)

USER_MESSAGE = {"role": "user", "content": "calculate 3x6 ?"}


def _flow_with_agent_node() -> Flow:
    agent = Agent(
        name="Calculator agent",
        # A generic LlmConfig is not skipped by SKIP_LLM_TESTS; the model is faked anyway
        llm_config=LlmConfig(name="llm", model_id="fake", api_provider="openai"),
        system_prompt="You are a calculator agent.",
        tools=[MULTIPLICATION_TOOL],
    )
    start = StartNode(name="start")
    agent_node = AgentNode(name="agent_node", agent=agent)
    end = EndNode(name="end")
    return Flow(
        name="calculator_flow",
        start_node=start,
        nodes=[start, agent_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_agent", from_node=start, to_node=agent_node),
            ControlFlowEdge(name="agent_to_end", from_node=agent_node, to_node=end),
        ],
    )


def _tool_call_messages(count: int) -> List[Any]:
    from langchain_core.messages import AIMessage

    return [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "multiplication_tool", "args": {"a": 3, "b": 6}, "id": f"call_{index}"}
            ],
        )
        for index in range(count)
    ]


@contextmanager
def _fake_llm(responses: List[Any]) -> Iterator[List[int]]:
    """Answer every LLM config with a fake chat model replaying ``responses``.

    Yields the list of recorded model calls (one entry per call).
    """
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_openai import ChatOpenAI

    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    class _FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        # FakeMessagesListChatModel only overrides the sync generation; without this,
        # async runs would reach ChatOpenAI's real client
        async def _agenerate(self, *args: Any, **kwargs: Any) -> Any:
            return self._generate(*args, **kwargs)

    calls: List[int] = []
    fake = _FakeModel(responses=responses)
    original_generate = FakeMessagesListChatModel._generate

    def _counting_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return original_generate(self, *args, **kwargs)

    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        autospec=True,
        side_effect=lambda _self, _llm_config, *args, **kwargs: fake,
    ), patch.object(
        FakeMessagesListChatModel, "bind_tools", new=lambda self_obj, *args, **kwargs: self_obj
    ), patch.object(
        FakeMessagesListChatModel, "_generate", new=_counting_generate
    ):
        yield calls


def _load(flow: Flow, loader_config: Any = None) -> Any:
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    return AgentSpecLoader(
        tool_registry={"multiplication_tool": lambda a, b: a * b},
        checkpointer=MemorySaver(),
        config=loader_config,
    ).load_component(flow)


def test_agent_node_inherits_the_recursion_limit_of_the_flow_run() -> None:
    from langgraph.errors import GraphRecursionError

    # The model calls the tool forever: the agent never terminates on its own
    with _fake_llm(_tool_call_messages(20_000)) as calls:
        graph = _load(_flow_with_agent_node())
        with pytest.raises(GraphRecursionError):
            graph.invoke(
                {"inputs": {}, "messages": [USER_MESSAGE]},
                config={"configurable": {"thread_id": "1"}, "recursion_limit": 6},
            )
    # Every agent step is a model call or a tool call: 6 steps allow 3 model calls
    assert len(calls) == 3


@pytest.mark.anyio
async def test_agent_node_inherits_the_recursion_limit_of_the_flow_run_async() -> None:
    from langgraph.errors import GraphRecursionError

    with _fake_llm(_tool_call_messages(20_000)) as calls:
        graph = _load(_flow_with_agent_node())
        with pytest.raises(GraphRecursionError):
            await graph.ainvoke(
                {"inputs": {}, "messages": [USER_MESSAGE]},
                config={"configurable": {"thread_id": "1"}, "recursion_limit": 6},
            )
    assert len(calls) == 3


def test_agent_node_keeps_the_loader_recursion_limit_when_configured() -> None:
    from langgraph.errors import GraphRecursionError

    with _fake_llm(_tool_call_messages(20_000)) as calls:
        graph = _load(_flow_with_agent_node(), loader_config={"recursion_limit": 10})
        with pytest.raises(GraphRecursionError):
            graph.invoke(
                {"inputs": {}, "messages": [USER_MESSAGE]},
                config={"configurable": {"thread_id": "1"}, "recursion_limit": 6},
            )
    # The loader config is explicit and wins over the limit of the run: 10 steps, 5 model calls
    assert len(calls) == 5


def test_agent_node_keeps_the_agent_default_limit_when_the_run_uses_the_default() -> None:
    from langchain_core.messages import AIMessage

    # LangChain's default recursion limit is 25 steps. The agent compiled by create_agent
    # allows far more and must keep doing so when the caller did not configure a limit.
    responses = _tool_call_messages(30) + [AIMessage(content="18")]
    with _fake_llm(responses) as calls:
        graph = _load(_flow_with_agent_node())
        result = graph.invoke(
            {"inputs": {}, "messages": [USER_MESSAGE]},
            config={"configurable": {"thread_id": "1"}},
        )
    assert len(calls) == 31
    assert result["messages"][-1].content == "18"
