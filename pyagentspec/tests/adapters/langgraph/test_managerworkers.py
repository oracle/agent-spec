# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any
from unittest.mock import patch

import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.managerworkers import ManagerWorkers

# Every test stubs the chat model and never reaches an endpoint, so they run offline
# even under SKIP_LLM_TESTS=1.
pytestmark = pytest.mark.usefixtures("allow_llm_config_construction")


def _agent(name: str, llm_name: str, description: str = "", system_prompt: str = ".") -> Agent:
    return Agent(
        name=name,
        description=description,
        system_prompt=system_prompt,
        llm_config=OpenAiCompatibleConfig(name=llm_name, model_id="fake", url="null"),
    )


def _fake_llm(*ai_responses: Any) -> Any:
    """A FakeMessagesListChatModel subclassed under ChatOpenAI so the react-agent
    treats it as an OpenAI-style chat model."""
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_openai import ChatOpenAI

    class _FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    return _FakeModel(responses=list(ai_responses))


def _load_with_fake_llms(mw: Any, default: Any = None, **fakes_by_llm_name: Any) -> Any:
    """Compile ``mw`` offline, answering each LLM config (keyed by ``llm_config.name``)
    with a queued fake; ``default`` answers any config not named.

    ``bind_tools`` is stubbed to return the same fake because
    ``FakeMessagesListChatModel`` inherits it from ``ChatOpenAI``, which calls OpenAI.
    """
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    def _dispatch(_self: Any, llm_config: Any, *args: Any, **kwargs: Any) -> Any:
        fake = fakes_by_llm_name.get(llm_config.name, default)
        if fake is None:
            raise AssertionError(f"unexpected llm_config: {llm_config.name}")
        return fake

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        autospec=True,
        side_effect=_dispatch,
    ), patch.object(
        FakeMessagesListChatModel, "bind_tools", new=lambda self_obj, *a, **kw: self_obj
    ):
        return loader.load_component(mw)


def test_safe_node_name_normalizes_and_falls_back() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import _safe_node_name

    assert _safe_node_name("Research Helper", "id-1") == "research_helper"
    assert _safe_node_name("My-Worker!! v2", "id-1") == "my_worker_v2"
    # Name slugifies to empty → normalized id; both empty → constant fallback.
    assert _safe_node_name("!!!", "sub-1") == "sub_1"
    assert _safe_node_name("", "") == "worker"


def test_append_workers_roster_renders_one_line_per_worker() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import _append_workers_roster

    out = _append_workers_roster(
        "Coordinate the team.",
        [("research_helper", "Handles research"), ("drafter", "Drafts text")],
    )
    assert out == (
        "Coordinate the team.\n\n"
        "Available workers:\n"
        "- research_helper: Handles research\n"
        "- drafter: Drafts text"
    )
    # Multiline descriptions are flattened so the one-line-per-worker shape survives.
    out = _append_workers_roster("", [("helper", "First line\nsecond line\n  third  line  ")])
    assert out == "Available workers:\n- helper: First line second line third line"


def test_route_manager_to_worker_or_end_returns_end_when_no_delegation() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.graph import END

    from pyagentspec.adapters.langgraph._managerworkers import _route_manager_to_worker_or_end

    not_delegating = AIMessage(content="Done.", tool_calls=[])
    assert _route_manager_to_worker_or_end({"messages": [not_delegating]}) == END
    assert _route_manager_to_worker_or_end({"messages": []}) == END


def test_route_manager_to_worker_or_end_fans_out_one_send_per_delegation() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.types import Send

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DELEGATE_CALL_ID_KEY,
        _DELEGATE_TASK_KEY,
        _route_manager_to_worker_or_end,
    )

    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "some_other_tool", "args": {}, "id": "c0"},
            {"name": "delegate_to_drafter", "args": {"task": "x"}, "id": "c1"},
            {"name": "delegate_to_research_helper", "args": {"task": "y"}, "id": "c2"},
        ],
    )
    sends = _route_manager_to_worker_or_end({"messages": [msg]})
    # Every delegation gets its own Send carrying the task and the tool_call_id its
    # reply must answer. The non-delegation tool call already ran inside the manager's
    # react loop and is ignored by routing.
    assert all(isinstance(s, Send) for s in sends)
    assert [s.node for s in sends] == ["drafter", "research_helper"]
    assert [s.arg[_DELEGATE_TASK_KEY] for s in sends] == ["x", "y"]
    assert [s.arg[_DELEGATE_CALL_ID_KEY] for s in sends] == ["c1", "c2"]


def test_manager_workers_compiles_to_hierarchical_graph_topology() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.graph import START

    from pyagentspec.adapters.langgraph._managerworkers import _MANAGER_NODE_KEY

    mw = ManagerWorkers(
        name="ResearchTeam",
        group_manager=_agent("Coordinator", "manager_llm", system_prompt="Coordinate the team."),
        workers=[
            _agent("Research Helper", "worker_a_llm", description="Handles research"),
            _agent("Drafter", "worker_b_llm", description="Drafts text"),
        ],
    )

    compiled = _load_with_fake_llms(mw, default=_fake_llm(AIMessage(content="Done.")))

    builder = compiled.builder
    assert _MANAGER_NODE_KEY in builder.nodes
    assert "research_helper" in builder.nodes
    assert "drafter" in builder.nodes

    # START → manager; every worker → manager (loop).
    edge_pairs = {(src, dst) for src, dst in builder.edges}
    assert (START, _MANAGER_NODE_KEY) in edge_pairs
    assert ("research_helper", _MANAGER_NODE_KEY) in edge_pairs
    assert ("drafter", _MANAGER_NODE_KEY) in edge_pairs

    # Manager → worker is a conditional edge.
    assert builder.branches.get(_MANAGER_NODE_KEY)


def test_manager_workers_registers_a_delegation_tool_per_worker() -> None:
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph._managerworkers import _MANAGER_NODE_KEY

    mw = ManagerWorkers(
        name="Team",
        group_manager=_agent("Coordinator", "manager_llm"),
        workers=[_agent("Research Helper", "worker_llm", description="Handles research tasks")],
    )

    compiled = _load_with_fake_llms(mw, default=_fake_llm(AIMessage(content="Done.")))

    # The delegation tool the roster advertises is registered on the manager
    # react-agent's tools node, so the LLM has the matching contract.
    manager_subgraph = compiled.builder.nodes[_MANAGER_NODE_KEY].runnable
    tools_node = manager_subgraph.builder.nodes["tools"].runnable
    assert "delegate_to_research_helper" in tools_node.tools_by_name


def test_manager_workers_delegates_and_routes_back_with_tool_message() -> None:
    """The manager delegates, the worker runs in an isolated message context and its
    answer comes back as a ToolMessage matched to the pending tool_call_id, and the
    manager's next turn terminates the graph."""
    from langchain_core.messages import AIMessage, HumanMessage

    mw = ManagerWorkers(
        name="Team",
        group_manager=_agent("Coordinator", "manager_llm", system_prompt="You coordinate."),
        workers=[_agent("Research Helper", "worker_llm", description="Handles research")],
    )

    # Manager turn 1: delegate. Manager turn 2: final answer (no tool call → END).
    manager_responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "delegate_to_research_helper",
                    "args": {"task": "Look up Saturn"},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="The worker reports: Saturn has rings."),
    ]
    worker_responses = [AIMessage(content="Saturn has rings.")]

    compiled = _load_with_fake_llms(
        mw,
        manager_llm=_fake_llm(*manager_responses),
        worker_llm=_fake_llm(*worker_responses),
    )

    # Sync invocation only: FakeMessagesListChatModel overrides ``_generate`` but not
    # ``_agenerate``, so the async path would resolve to ``ChatOpenAI._agenerate``
    # and call OpenAI.
    result = compiled.invoke(
        {"messages": [HumanMessage(content="Tell me about Saturn.")]},
        {"configurable": {"thread_id": "mw-1"}},
    )
    messages = result["messages"]

    assert isinstance(messages[-1], AIMessage)
    assert "Saturn has rings" in messages[-1].content
    tool_msgs = [m for m in messages if type(m).__name__ == "ToolMessage"]
    assert tool_msgs and tool_msgs[0].tool_call_id == "call_1"
    assert "Saturn has rings" in tool_msgs[0].content


def test_manager_workers_answers_every_delegation_in_a_single_turn() -> None:
    """When one manager turn emits several delegations, each must be answered by its
    own ToolMessage matched to the originating tool_call_id; an unanswered one is an
    invalid tool-call/result sequence the manager would hallucinate around."""
    from langchain_core.messages import AIMessage, HumanMessage

    mw = ManagerWorkers(
        name="Team",
        group_manager=_agent("Coordinator", "manager_llm", system_prompt="You coordinate."),
        workers=[_agent("Sub Agent", "worker_llm", description="Writes poems")],
    )

    # Turn 1: three delegations to the same worker in one AIMessage. Turn 2: terminate.
    manager_responses = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "delegate_to_sub_agent", "args": {"task": "Spanish poem"}, "id": "call_1"},
                {"name": "delegate_to_sub_agent", "args": {"task": "French poem"}, "id": "call_2"},
                {"name": "delegate_to_sub_agent", "args": {"task": "German poem"}, "id": "call_3"},
            ],
        ),
        AIMessage(content="Here are your three poems."),
    ]
    worker_responses = [AIMessage(content=f"poem #{i}") for i in range(1, 6)]

    compiled = _load_with_fake_llms(
        mw,
        manager_llm=_fake_llm(*manager_responses),
        worker_llm=_fake_llm(*worker_responses),
    )

    result = compiled.invoke(
        {"messages": [HumanMessage(content="Write 3 poems via sub-agents.")]},
        {"configurable": {"thread_id": "mw-multi"}},
    )
    messages = result["messages"]

    tool_msgs = [m for m in messages if type(m).__name__ == "ToolMessage"]
    answered = sorted(m.tool_call_id for m in tool_msgs)
    assert answered == ["call_1", "call_2", "call_3"]
    assert all(m.content.startswith("poem #") for m in tool_msgs)


def test_nested_manager_workers_compiles_recursively() -> None:
    """A worker that is itself a ManagerWorkers compiles through the same dispatch and
    is wired in as a subgraph node of the outer parent graph."""
    from langchain_core.messages import AIMessage

    inner_mw = ManagerWorkers(
        name="Inner",
        group_manager=_agent("InnerManager", "inner_llm", system_prompt="Manage leaves."),
        workers=[_agent("Leaf", "leaf_llm", description="Leaf task")],
    )
    outer_mw = ManagerWorkers(
        name="Outer",
        group_manager=_agent("OuterManager", "outer_llm", system_prompt="Manage subteams."),
        workers=[inner_mw],
    )

    compiled = _load_with_fake_llms(outer_mw, default=_fake_llm(AIMessage(content="Done.")))

    assert "inner" in compiled.builder.nodes


def test_rejects_non_agent_group_manager() -> None:
    """A nested ManagerWorkers as group_manager is valid per the pyagentspec
    validators, but the adapter needs a chat-LLM emitting tool_calls to route on."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    inner_mw = ManagerWorkers(
        name="Inner",
        group_manager=_agent("Inner", "i"),
        workers=[_agent("Leaf", "l")],
    )
    outer_mw = ManagerWorkers(
        name="Outer",
        group_manager=inner_mw,
        workers=[_agent("Other", "o")],
    )

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with pytest.raises(NotImplementedError, match="group_manager must be an Agent"):
        loader.load_component(outer_mw)


def test_workers_with_name_slug_collision_are_rejected() -> None:
    """Two workers whose names normalize to the same node identifier would silently
    overwrite each other in the parent graph; raise at load time instead."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Both worker names normalize to "helper_a".
    mw = ManagerWorkers(
        name="T",
        group_manager=_agent("M", "m"),
        workers=[_agent("Helper A", "a"), _agent("helper-a", "b")],
    )

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with pytest.raises(ValueError, match="collide after normalization"):
        loader.load_component(mw)


def test_worker_events_stream_natively_namespaced_under_worker_node() -> None:
    """Regression: a worker's token events must stream under the worker node's
    checkpoint namespace so a consumer can attribute them to the sub-agent. The
    wrapper must inherit the ambient run config; a fresh thread_id would detach the
    worker into an unattributable top-level ``agent:<uuid>`` run."""
    import asyncio

    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    from pyagentspec.adapters.langgraph._managerworkers import _wrap_worker_for_subgraph

    # A minimal worker graph that streams some content.
    wmodel = GenericFakeChatModel(messages=iter([AIMessage(content="Saturn has rings")] * 9))
    wb = StateGraph(MessagesState)

    async def _wagent(state: Any) -> Any:
        return {"messages": [await wmodel.ainvoke(state["messages"])]}

    wb.add_node("agent", _wagent)
    wb.add_edge(START, "agent")
    wb.add_edge("agent", END)
    worker_graph = wb.compile()

    # Parent: a plain manager node emits the delegate tool call, then routes to the
    # wrapped worker node.
    pb = StateGraph(MessagesState)

    def _manager(state: Any) -> Any:
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "delegate_to_research_helper",
                            "args": {"task": "Saturn"},
                            "id": "c1",
                        }
                    ],
                )
            ]
        }

    pb.add_node("__manager__", _manager)
    pb.add_node("research_helper", _wrap_worker_for_subgraph(worker_graph, "research_helper"))
    pb.add_edge(START, "__manager__")
    pb.add_edge("__manager__", "research_helper")
    pb.add_edge("research_helper", END)
    parent = pb.compile()

    async def _collect() -> Any:
        namespaces = []
        async for ev in parent.astream_events(
            {"messages": [HumanMessage(content="hi")]},
            {"configurable": {"thread_id": "t"}},
            version="v2",
        ):
            if ev["event"] == "on_chat_model_stream":
                ns = (ev.get("metadata") or {}).get("langgraph_checkpoint_ns", "")
                namespaces.append(ns)
        return namespaces

    namespaces = asyncio.run(_collect())
    assert namespaces, "expected the worker to emit token-stream events"
    assert all(ns.startswith("research_helper:") for ns in namespaces), namespaces


def test_is_delegation_tool_name_matches_only_the_synthetic_prefix() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import (
        DELEGATE_TOOL_PREFIX,
        is_delegation_tool_name,
    )

    assert DELEGATE_TOOL_PREFIX == "delegate_to_"
    assert is_delegation_tool_name("delegate_to_research_helper")
    assert not is_delegation_tool_name("get_weather")
    # A real tool merely *containing* the prefix mid-name is not a delegation.
    assert not is_delegation_tool_name("please_delegate_to_someone")
    assert not is_delegation_tool_name(None)
    assert not is_delegation_tool_name(123)


def test_manager_workers_leaves_astream_events_unwrapped() -> None:
    """The delegation protocol is deliberately visible: only stream/astream are
    patched (for the ManagerWorkersExecutionSpan); nothing wraps ``astream_events``
    to scrub the delegation tool calls."""
    mw = ManagerWorkers(
        name="Team",
        group_manager=_agent("Coordinator", "manager_llm"),
        workers=[_agent("Research Helper", "worker_llm")],
    )

    compiled = _load_with_fake_llms(mw, default=_fake_llm())

    assert "stream" in compiled.__dict__ and "astream" in compiled.__dict__
    assert "astream_events" not in compiled.__dict__
