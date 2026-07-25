# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Offline tests for the LangGraph ``ManagerWorkers`` converter.

These cover the hierarchical topology, roster prompt rendering, the
worker-isolation invariant (each worker sees only its delegated task),
and the recursive nesting case. The LLM is stubbed with
``FakeMessagesListChatModel`` so the tests run without network or model
endpoints.
"""

from typing import Any
from unittest.mock import patch

import pytest

# ─── Shared helpers ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _offline(allow_llm_config_construction: None) -> None:
    """Every test in this module stubs the chat model (``_fake_manager`` or an
    explicitly patched ``_llm_convert_to_langgraph``) and never reaches an
    endpoint, so the SKIP_LLM_TESTS construction guard would only hide them."""


def _llm_cfg(name: str) -> Any:
    from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig

    return OpenAiCompatibleConfig(name=name, model_id="fake", url="null")


def _fake_manager(*ai_responses: Any) -> Any:
    """A FakeMessagesListChatModel subclassed under ChatOpenAI so the
    manager's react-agent treats it as an OpenAI-style chat model."""
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_openai import ChatOpenAI

    class _FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    return _FakeModel(responses=list(ai_responses))


def _load_with_fake_llms(mw: Any, default: Any = None, **fakes_by_llm_name: Any) -> Any:
    """Compile ``mw`` offline, answering each LLM config with a queued fake.

    Keys are ``llm_config.name``; ``default`` answers any config not named.

    ``create_agent`` calls ``model.bind_tools(...)``, and ``FakeMessagesListChatModel``
    inherits ``bind_tools`` from the real ``ChatOpenAI``, which calls out to OpenAI.
    Binding is stubbed to return the same fake, preserving its response queue.
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


# ─── Pure-helper unit tests (no LLM) ────────────────────────────────────────


def test_safe_node_name_lowercases_and_collapses_punctuation() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import (
        _safe_node_name,
    )

    assert _safe_node_name("Research Helper", "id-1") == "research_helper"
    assert _safe_node_name("My-Worker!! v2", "id-1") == "my_worker_v2"


def test_safe_node_name_falls_back_to_normalized_id() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import (
        _safe_node_name,
    )

    # Name slugifies to empty → id used (and also normalized).
    assert _safe_node_name("!!!", "sub-1") == "sub_1"
    # Both empty → constant fallback.
    assert _safe_node_name("", "") == "worker"


def test_append_workers_roster_appends_block_after_existing_prompt() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import (
        _append_workers_roster,
    )

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


def test_append_workers_roster_flattens_multiline_descriptions() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import (
        _append_workers_roster,
    )

    out = _append_workers_roster(
        "",
        [("helper", "First line\nsecond line\n  third  line  ")],
    )
    # Whitespace flattened so the one-line-per-worker shape survives.
    assert out == "Available workers:\n- helper: First line second line third line"


def test_route_manager_to_worker_or_end_sends_to_pending_delegation() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.types import Send

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DELEGATE_CALL_ID_KEY,
        _DELEGATE_TASK_KEY,
        _route_manager_to_worker_or_end,
    )

    delegating = AIMessage(
        content="",
        tool_calls=[{"name": "delegate_to_research_helper", "args": {"task": "hi"}, "id": "c1"}],
    )
    sends = _route_manager_to_worker_or_end({"messages": [delegating]})
    # One delegation → a single Send to the worker node carrying the task
    # and the tool_call_id its reply must answer.
    assert isinstance(sends, list) and len(sends) == 1
    assert isinstance(sends[0], Send)
    assert sends[0].node == "research_helper"
    assert sends[0].arg == {_DELEGATE_TASK_KEY: "hi", _DELEGATE_CALL_ID_KEY: "c1"}


def test_route_manager_to_worker_or_end_returns_end_when_no_delegation() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.graph import END

    from pyagentspec.adapters.langgraph._managerworkers import (
        _route_manager_to_worker_or_end,
    )

    not_delegating = AIMessage(content="Done.", tool_calls=[])
    assert _route_manager_to_worker_or_end({"messages": [not_delegating]}) == END
    assert _route_manager_to_worker_or_end({"messages": []}) == END


def test_route_manager_to_worker_or_end_fans_out_every_delegation() -> None:
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
    # Every delegation gets its own Send so each tool_call_id is answered.
    # The non-delegation tool call was already executed inside the manager's
    # react loop and is ignored by routing.
    assert all(isinstance(s, Send) for s in sends)
    assert [s.node for s in sends] == ["drafter", "research_helper"]
    assert [s.arg[_DELEGATE_CALL_ID_KEY] for s in sends] == ["c1", "c2"]
    assert [s.arg[_DELEGATE_TASK_KEY] for s in sends] == ["x", "y"]


# ─── Topology test (no LLM execution; checks compiled graph shape) ──────────


def test_manager_workers_compiles_to_hierarchical_graph_topology() -> None:
    from langchain_core.messages import AIMessage
    from langgraph.graph import START

    from pyagentspec.adapters.langgraph._managerworkers import (
        _MANAGER_NODE_KEY,
    )
    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    manager_agent = Agent(
        name="Coordinator",
        description="Coordinates",
        system_prompt="Coordinate the team.",
        llm_config=_llm_cfg("manager_llm"),
    )
    worker_a = Agent(
        name="Research Helper",
        description="Handles research",
        system_prompt="Research.",
        llm_config=_llm_cfg("worker_a_llm"),
    )
    worker_b = Agent(
        name="Drafter",
        description="Drafts text",
        system_prompt="Draft.",
        llm_config=_llm_cfg("worker_b_llm"),
    )
    mw = ManagerWorkers(
        name="ResearchTeam",
        group_manager=manager_agent,
        workers=[worker_a, worker_b],
    )

    compiled = _load_with_fake_llms(mw, default=_fake_manager(AIMessage(content="Done.")))

    builder = compiled.builder
    assert _MANAGER_NODE_KEY in builder.nodes
    assert "research_helper" in builder.nodes
    assert "drafter" in builder.nodes

    # START → manager; every worker → manager (loop).
    edge_pairs = {(src, dst) for src, dst in builder.edges}
    assert (START, _MANAGER_NODE_KEY) in edge_pairs
    assert ("research_helper", _MANAGER_NODE_KEY) in edge_pairs
    assert ("drafter", _MANAGER_NODE_KEY) in edge_pairs

    # Manager → worker is a conditional edge, and branches live separately from
    # plain edges on the builder.
    branches = builder.branches.get(_MANAGER_NODE_KEY) or {}
    assert branches, "expected a conditional branch from the manager node"


def test_manager_workers_registers_a_delegation_tool_per_worker() -> None:
    """Each worker gets a ``delegate_to_<worker>`` tool on the manager, matching the
    ``Available workers:`` roster the converter renders into its system prompt (the
    roster text itself is covered by the ``_append_workers_roster`` unit tests).
    """
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph._managerworkers import (
        _MANAGER_NODE_KEY,
    )
    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    manager_agent = Agent(
        name="Coordinator",
        description="Coordinates",
        system_prompt="Coordinate the team.",
        llm_config=_llm_cfg("manager_llm"),
    )
    worker = Agent(
        name="Research Helper",
        description="Handles research tasks",
        system_prompt="Research.",
        llm_config=_llm_cfg("worker_llm"),
    )
    mw = ManagerWorkers(
        name="Team",
        group_manager=manager_agent,
        workers=[worker],
    )

    compiled = _load_with_fake_llms(mw, default=_fake_manager(AIMessage(content="Done.")))

    # The manager react-agent is itself a subgraph; the delegation tool the roster
    # advertises is registered on its tools node, so the LLM has the matching contract.
    manager_subgraph = compiled.builder.nodes[_MANAGER_NODE_KEY].runnable
    tools_node = manager_subgraph.builder.nodes["tools"].runnable
    assert "delegate_to_research_helper" in tools_node.tools_by_name


# ─── End-to-end execution test (offline, fake LLM emitting delegation) ──────


def test_manager_workers_delegates_and_routes_back_with_tool_message() -> None:
    """End to end, the path that proves subgraph composition works.

    The manager emits a delegate_to_<worker> call, the parent graph routes to the
    worker subgraph in an isolated message context, the worker's answer comes back
    as a ToolMessage matched to the pending tool_call_id, and the manager's next
    turn terminates the graph.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    manager_agent = Agent(
        name="Coordinator",
        description="Coordinates",
        system_prompt="You coordinate.",
        llm_config=_llm_cfg("manager_llm"),
    )
    worker = Agent(
        name="Research Helper",
        description="Handles research",
        system_prompt="You research.",
        llm_config=_llm_cfg("worker_llm"),
    )
    mw = ManagerWorkers(
        name="Team",
        group_manager=manager_agent,
        workers=[worker],
    )

    # Manager turn 1: delegate to research_helper.
    # Manager turn 2: produce final answer (no tool call → END).
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
    # Worker turn 1: produce its own final answer.
    worker_responses = [AIMessage(content="Saturn has rings.")]

    compiled = _load_with_fake_llms(
        mw,
        manager_llm=_fake_manager(*manager_responses),
        worker_llm=_fake_manager(*worker_responses),
    )

    # Sync invocation only. FakeMessagesListChatModel overrides ``_generate`` but not
    # ``_agenerate``, so the async path would resolve up the MRO to the real
    # ``ChatOpenAI._agenerate`` and call OpenAI.
    result = compiled.invoke(
        {"messages": [HumanMessage(content="Tell me about Saturn.")]},
        {"configurable": {"thread_id": "mw-1"}},
    )
    messages = result["messages"]

    msg_types = [type(m).__name__ for m in messages]
    assert "HumanMessage" in msg_types
    assert "ToolMessage" in msg_types
    assert isinstance(messages[-1], AIMessage)
    assert "Saturn has rings" in messages[-1].content

    # Matching the pending delegation id proves the isolation wrapper threaded the
    # call id through.
    tool_msgs = [m for m in messages if type(m).__name__ == "ToolMessage"]
    assert tool_msgs and tool_msgs[0].tool_call_id == "call_1"
    assert "Saturn has rings" in tool_msgs[0].content


def test_manager_workers_answers_every_delegation_in_a_single_turn() -> None:
    """Regression: when the manager emits SEVERAL ``delegate_to_<worker>``
    tool calls in one turn (e.g. "spin up 5 sub-agents"), every delegation
    must run and be answered by its own ToolMessage matched to the
    originating tool_call_id.

    Before the fix the parent graph routed only the first delegation and left the
    other tool_call_ids unanswered. That is an invalid tool-call/tool-result
    sequence, and the manager hallucinated the missing replies.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    manager_agent = Agent(
        name="Coordinator",
        description="Coordinates",
        system_prompt="You coordinate.",
        llm_config=_llm_cfg("manager_llm"),
    )
    worker = Agent(
        name="Sub Agent",
        description="Writes poems",
        system_prompt="You write poems.",
        llm_config=_llm_cfg("worker_llm"),
    )
    mw = ManagerWorkers(name="Team", group_manager=manager_agent, workers=[worker])

    # Turn 1: three delegations to the SAME worker in one AIMessage.
    # Turn 2: terminate (no tool call).
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
    # Each worker invocation pops one reply; provide enough for the fan-out.
    worker_responses = [AIMessage(content=f"poem #{i}") for i in range(1, 6)]

    compiled = _load_with_fake_llms(
        mw,
        manager_llm=_fake_manager(*manager_responses),
        worker_llm=_fake_manager(*worker_responses),
    )

    result = compiled.invoke(
        {"messages": [HumanMessage(content="Write 3 poems via sub-agents.")]},
        {"configurable": {"thread_id": "mw-multi"}},
    )
    messages = result["messages"]

    # Every delegation tool_call_id must be answered by exactly one ToolMessage.
    requested = {
        tc["id"]
        for m in messages
        if isinstance(m, AIMessage)
        for tc in (m.tool_calls or [])
        if tc["name"].startswith("delegate_to_")
    }
    answered = [m.tool_call_id for m in messages if type(m).__name__ == "ToolMessage"]
    assert requested == {"call_1", "call_2", "call_3"}
    assert sorted(answered) == [
        "call_1",
        "call_2",
        "call_3",
    ], f"unanswered delegations: {requested - set(answered)}"
    # No duplicate replies, and each carries a worker poem.
    assert len(answered) == 3
    tool_msgs = [m for m in messages if type(m).__name__ == "ToolMessage"]
    assert all(m.content.startswith("poem #") for m in tool_msgs)


# ─── Recursive nesting ──────────────────────────────────────────────────────


def test_nested_manager_workers_compiles_recursively() -> None:
    """A worker that is itself a ManagerWorkers compiles through the same dispatch,
    becoming a CompiledStateGraph the outer parent graph wires in as a subgraph node."""
    from langchain_core.messages import AIMessage

    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    leaf = Agent(
        name="Leaf",
        description="Leaf task",
        system_prompt="Leaf.",
        llm_config=_llm_cfg("leaf_llm"),
    )
    inner_manager = Agent(
        name="InnerManager",
        description="Inner",
        system_prompt="Manage leaves.",
        llm_config=_llm_cfg("inner_llm"),
    )
    inner_mw = ManagerWorkers(
        name="Inner",
        group_manager=inner_manager,
        workers=[leaf],
    )
    outer_manager = Agent(
        name="OuterManager",
        description="Outer",
        system_prompt="Manage subteams.",
        llm_config=_llm_cfg("outer_llm"),
    )
    outer_mw = ManagerWorkers(
        name="Outer",
        group_manager=outer_manager,
        workers=[inner_mw],
    )

    compiled = _load_with_fake_llms(outer_mw, default=_fake_manager(AIMessage(content="Done.")))

    # Outer parent graph has a node for the inner ManagerWorkers worker.
    assert "inner" in compiled.builder.nodes


def test_rejects_non_agent_group_manager() -> None:
    """group_manager must be an Agent. Pyagentspec accepts any AgenticComponent, but
    the adapter needs a chat-LLM emitting tool_calls to decide where to delegate."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    # A nested ManagerWorkers as group_manager: valid per the pyagentspec
    # validators, unsupported here.
    leaf = Agent(
        name="Leaf",
        description="L",
        system_prompt="L.",
        llm_config=_llm_cfg("l"),
    )
    inner_manager = Agent(
        name="Inner",
        description="I",
        system_prompt="I.",
        llm_config=_llm_cfg("i"),
    )
    inner_mw = ManagerWorkers(
        name="Inner",
        group_manager=inner_manager,
        workers=[leaf],
    )
    outer_mw = ManagerWorkers(
        name="Outer",
        group_manager=inner_mw,
        workers=[
            Agent(name="Other", description="O", system_prompt="O.", llm_config=_llm_cfg("o")),
        ],
    )
    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with pytest.raises(NotImplementedError, match="group_manager must be an Agent"):
        loader.load_component(outer_mw)


# ─── Worker name collision ──────────────────────────────────────────────────


def test_workers_with_name_slug_collision_are_rejected() -> None:
    """Two workers whose names normalize to the same node identifier
    would silently overwrite each other in the parent graph; raise at
    load time instead."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    a = Agent(name="Helper A", description="x", system_prompt=".", llm_config=_llm_cfg("a"))
    b = Agent(name="helper-a", description="x", system_prompt=".", llm_config=_llm_cfg("b"))
    # Both normalize to "helper_a".
    mw = ManagerWorkers(
        name="T",
        group_manager=Agent(
            name="M",
            description="m",
            system_prompt=".",
            llm_config=_llm_cfg("m"),
        ),
        workers=[a, b],
    )

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with pytest.raises(ValueError, match="collide after normalization"):
        loader.load_component(mw)


def test_worker_events_stream_natively_namespaced_under_worker_node() -> None:
    """Regression: a worker's token events must stream under the worker
    node's checkpoint namespace so a consumer can attribute them to the
    sub-agent. The wrapper must inherit the ambient run config (no fresh
    thread_id); a fresh thread_id detaches the worker into a top-level
    ``agent:<uuid>`` run with no worker prefix, which is unattributable."""
    import asyncio

    from langchain_core.language_models.fake_chat_models import (
        GenericFakeChatModel,
    )
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    from pyagentspec.adapters.langgraph._managerworkers import (
        _wrap_worker_for_subgraph,
    )

    # A minimal worker compiled graph that streams some content.
    wmodel = GenericFakeChatModel(messages=iter([AIMessage(content="Saturn has rings")] * 9))
    wb = StateGraph(MessagesState)

    async def _wagent(state: Any) -> Any:
        return {"messages": [await wmodel.ainvoke(state["messages"])]}

    wb.add_node("agent", _wagent)
    wb.add_edge(START, "agent")
    wb.add_edge("agent", END)
    worker_graph = wb.compile()

    # Parent: a plain manager node emits the delegate tool call, then routes
    # to the wrapped worker node named "research_helper".
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
    # Every worker token event is namespaced under the worker node, so a
    # consumer can attribute the stream to the sub-agent.
    assert all(ns.startswith("research_helper:") for ns in namespaces), namespaces


# ─── Shared low-level helper unit tests (no LLM) ─────────────────────────────


def test_normalize_identifier_lowercases_collapses_and_strips() -> None:
    """The single normalization used for both worker node names and
    ``transfer_to_<sibling>`` tool names."""
    from pyagentspec.adapters.langgraph._managerworkers import _normalize_identifier

    assert _normalize_identifier("Research Helper") == "research_helper"
    assert _normalize_identifier("My-Worker!! v2") == "my_worker_v2"
    # Punctuation-only / empty slugify to the empty string (callers add a fallback).
    assert _normalize_identifier("!!!") == ""
    assert _normalize_identifier("") == ""


def test_messages_of_reads_dict_and_object_state() -> None:
    """The delegation tool receives state as a dict or an attribute-bearing
    object depending on the langgraph injection path."""
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph._managerworkers import _messages_of

    msg = AIMessage(content="hi")
    assert _messages_of({"messages": [msg]}) == [msg]
    assert _messages_of({"messages": None}) == []
    assert _messages_of({}) == []

    class _State:
        messages = [msg]

    assert _messages_of(_State()) == [msg]

    class _Empty:
        pass

    assert _messages_of(_Empty()) == []


def test_surface_to_parent_command_projects_messages_with_no_goto() -> None:
    """The placeholder tool's body: break to the parent graph, project the
    subgraph messages, carry no ``goto`` (routing is the parent's job)."""
    from langchain_core.messages import AIMessage
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph._managerworkers import _surface_to_parent_command

    m1, m2 = AIMessage(content="a"), AIMessage(content="b")
    cmd = _surface_to_parent_command({"messages": [m1, m2]})

    assert isinstance(cmd, Command)
    assert cmd.graph == Command.PARENT
    assert cmd.goto == ()  # no goto; the parent graph decides where to go
    assert cmd.update == {"messages": [m1, m2]}


def test_delegation_tool_exposes_expected_name_and_description() -> None:
    """The placeholder tool the manager's LLM addresses by name."""
    from pyagentspec.adapters.langgraph._managerworkers import _make_worker_delegation_tool

    delegate = _make_worker_delegation_tool("research_helper")
    assert delegate.name == "delegate_to_research_helper"
    assert "research_helper" in delegate.description


# ─── _wrap_worker_for_subgraph: pending-delegation extraction (no LLM) ────────


def _echo_worker_graph(reply: str = "WORKER REPLY") -> Any:
    """A worker CompiledStateGraph whose only node returns a fixed AIMessage, enough
    to exercise the wrapper without an LLM."""
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    wb = StateGraph(MessagesState)
    wb.add_node("agent", lambda state: {"messages": [AIMessage(content=reply)]})
    wb.add_edge(START, "agent")
    wb.add_edge("agent", END)
    return wb.compile()


def test_wrap_worker_uses_send_payload_task_and_call_id() -> None:
    """Fan-out path: the routing edge's ``Send`` payload carries the task and
    the originating tool_call_id directly, so the worker reply ToolMessage is
    matched to that call."""
    from langchain_core.messages import ToolMessage

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DELEGATE_CALL_ID_KEY,
        _DELEGATE_TASK_KEY,
        _wrap_worker_for_subgraph,
    )

    node = _wrap_worker_for_subgraph(_echo_worker_graph("DONE"), "research_helper")
    out = node.invoke({_DELEGATE_TASK_KEY: "do it", _DELEGATE_CALL_ID_KEY: "call_9"})

    (reply,) = out["messages"]
    assert isinstance(reply, ToolMessage)
    assert reply.content == "DONE"
    assert reply.tool_call_id == "call_9"


# ─── Delegation visibility: the public consumer-side filter ──────────────────


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
    """The delegation protocol is deliberately visible: nothing wraps
    ``astream_events`` to scrub it. Only stream/astream are patched, for the
    ManagerWorkersExecutionSpan."""

    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    mw = ManagerWorkers(
        name="Team",
        group_manager=Agent(
            name="Coordinator",
            description="c",
            system_prompt=".",
            llm_config=_llm_cfg("manager_llm"),
        ),
        workers=[
            Agent(
                name="Research Helper",
                description="r",
                system_prompt=".",
                llm_config=_llm_cfg("worker_llm"),
            ),
        ],
    )

    compiled = _load_with_fake_llms(mw, default=_fake_manager())

    assert getattr(compiled.astream_events, "__name__", "") != "patched_astream_events"
    # The execution-span patches are still applied.
    assert getattr(compiled.stream, "__name__", "") == "patched_stream"
    assert getattr(compiled.astream, "__name__", "") == "patched_astream"
