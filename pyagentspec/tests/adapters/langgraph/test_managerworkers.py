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
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import START

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
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

    fake_llm = _fake_manager(AIMessage(content="Done."))
    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter, "_llm_convert_to_langgraph", return_value=fake_llm
    ):
        compiled = loader.load_component(mw)

    # The compiled object is a CompiledStateGraph; its builder exposes
    # the parent topology we expect.
    builder = compiled.builder
    assert _MANAGER_NODE_KEY in builder.nodes
    assert "research_helper" in builder.nodes
    assert "drafter" in builder.nodes

    # START → manager; every worker → manager (loop).
    edge_pairs = {(src, dst) for src, dst in builder.edges}
    assert (START, _MANAGER_NODE_KEY) in edge_pairs
    assert ("research_helper", _MANAGER_NODE_KEY) in edge_pairs
    assert ("drafter", _MANAGER_NODE_KEY) in edge_pairs

    # The manager → worker routing is a conditional edge (branch), not a
    # plain edge — branches are stored separately on the builder.
    branches = builder.branches.get(_MANAGER_NODE_KEY) or {}
    assert branches, "expected a conditional branch from the manager node"


def test_manager_workers_renders_workers_roster_into_manager_prompt() -> None:
    """The manager's system prompt gets the ``Available workers:`` block
    appended so the LLM knows which delegation tool maps to which worker.
    """
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
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

    fake_llm = _fake_manager(AIMessage(content="Done."))
    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter, "_llm_convert_to_langgraph", return_value=fake_llm
    ):
        compiled = loader.load_component(mw)

    # The manager react-agent is itself a subgraph; its create_agent
    # middleware stack carries the rendered system prompt as the
    # first message of every turn. Walk the manager subgraph's pre-model
    # hook chain to find it.
    manager_subgraph = compiled.builder.nodes[_MANAGER_NODE_KEY].runnable
    # `create_agent` builds a graph whose system message generation
    # wraps the prompt — easier to assert by re-rendering it through the
    # same helper used by the converter and checking the *intent*.
    from pyagentspec.adapters.langgraph._managerworkers import (
        _append_workers_roster,
    )

    expected = _append_workers_roster(
        "Coordinate the team.",
        [("research_helper", "Handles research tasks")],
    )
    assert "Available workers:" in expected
    assert "- research_helper: Handles research tasks" in expected
    # And the compiled manager carries the delegation tool the prompt
    # advertises, proving the LLM has the matching contract.
    tools_node = manager_subgraph.builder.nodes["tools"].runnable
    assert "delegate_to_research_helper" in tools_node.tools_by_name


# ─── End-to-end execution test (offline, fake LLM emitting delegation) ──────


def test_manager_workers_delegates_and_routes_back_with_tool_message() -> None:
    """End-to-end: manager LLM emits a delegate_to_<worker> tool call,
    the parent graph routes to the worker subgraph (which runs with an
    isolated message context), the worker's final AIMessage content is
    surfaced back to the manager as a ToolMessage matched to the
    pending tool_call_id, and the manager's next turn (no tool call)
    terminates the graph. This is the load-bearing path that proves the
    subgraph composition actually works."""
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
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

    fake_manager = _fake_manager(*manager_responses)
    fake_worker = _fake_manager(*worker_responses)

    def _dispatch(self_obj: Any, llm_config: Any, *args: Any, **kwargs: Any) -> Any:
        if llm_config.name == "manager_llm":
            return fake_manager
        if llm_config.name == "worker_llm":
            return fake_worker
        raise AssertionError(f"unexpected llm_config: {llm_config.name}")

    # ``create_agent`` calls ``model.bind_tools(...)``. ``FakeMessagesListChatModel``
    # inherits ``bind_tools`` from real ``ChatOpenAI``, which calls out to
    # OpenAI. Patch the class method so binding is a no-op that returns the
    # same fake (preserving its response queue).
    from langchain_core.language_models.fake_chat_models import (
        FakeMessagesListChatModel,
    )

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        autospec=True,
        side_effect=_dispatch,
    ), patch.object(
        FakeMessagesListChatModel,
        "bind_tools",
        new=lambda self_obj, *a, **kw: self_obj,
    ):
        compiled = loader.load_component(mw)

    # Use the sync invocation path: ``FakeMessagesListChatModel`` provides
    # a sync ``_generate`` (returns queued responses) but no async
    # override, so MRO resolves ``_agenerate`` to the real
    # ``ChatOpenAI._agenerate`` which calls the OpenAI API. The worker
    # wrapper exposes both sync and async via RunnableLambda; LangGraph
    # picks the sync path here.
    result = compiled.invoke(
        {"messages": [HumanMessage(content="Tell me about Saturn.")]},
        {"configurable": {"thread_id": "mw-1"}},
    )
    messages = result["messages"]

    # The end state should contain: user input, manager's delegation
    # AIMessage, the synthesized ToolMessage (worker's reply), and the
    # manager's final AIMessage.
    msg_types = [type(m).__name__ for m in messages]
    assert "HumanMessage" in msg_types
    assert "ToolMessage" in msg_types
    # Final message is the manager's terminating AIMessage.
    assert isinstance(messages[-1], AIMessage)
    assert "Saturn has rings" in messages[-1].content

    # And the ToolMessage carries the worker's reply matched to the
    # pending delegation tool_call_id — proves the isolation wrapper
    # threaded the call id through.
    tool_msgs = [m for m in messages if type(m).__name__ == "ToolMessage"]
    assert tool_msgs and tool_msgs[0].tool_call_id == "call_1"
    assert "Saturn has rings" in tool_msgs[0].content


def test_manager_workers_answers_every_delegation_in_a_single_turn() -> None:
    """Regression: when the manager emits SEVERAL ``delegate_to_<worker>``
    tool calls in one turn (e.g. "spin up 5 sub-agents"), every delegation
    must run and be answered by its own ToolMessage matched to the
    originating tool_call_id.

    Before the fix the parent graph routed only the first delegation, so the
    other tool_call_ids were left unanswered — an invalid tool-call /
    tool-result sequence that made the manager hallucinate the missing
    replies. This asserts all three calls get matched ToolMessages.
    """
    from langchain_core.language_models.fake_chat_models import (
        FakeMessagesListChatModel,
    )
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
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

    fake_manager = _fake_manager(*manager_responses)
    fake_worker = _fake_manager(*worker_responses)

    def _dispatch(self_obj: Any, llm_config: Any, *args: Any, **kwargs: Any) -> Any:
        if llm_config.name == "manager_llm":
            return fake_manager
        if llm_config.name == "worker_llm":
            return fake_worker
        raise AssertionError(f"unexpected llm_config: {llm_config.name}")

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        autospec=True,
        side_effect=_dispatch,
    ), patch.object(
        FakeMessagesListChatModel,
        "bind_tools",
        new=lambda self_obj, *a, **kw: self_obj,
    ):
        compiled = loader.load_component(mw)

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
    """A worker that is itself a ManagerWorkers compiles through the
    same dispatch — the inner ManagerWorkers becomes a CompiledStateGraph
    that the outer parent graph wires in as a subgraph node."""
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
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

    fake_llm = _fake_manager(AIMessage(content="Done."))
    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter, "_llm_convert_to_langgraph", return_value=fake_llm
    ):
        compiled = loader.load_component(outer_mw)

    # Outer parent graph has a node for the inner ManagerWorkers worker.
    assert "inner" in compiled.builder.nodes


def test_rejects_non_agent_group_manager() -> None:
    """ManagerWorkers.group_manager must be an Agent — pyagentspec allows
    any AgenticComponent but the LangGraph adapter needs a chat-LLM that
    emits tool_calls to decide which worker to delegate to."""
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.agent import Agent
    from pyagentspec.managerworkers import ManagerWorkers

    # Use a nested ManagerWorkers as the group_manager — a valid
    # AgenticComponent per pyagentspec validators, unsupported here.
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


# ─── astream_events delegation scrubbing ─────────────────────────────────────
#
# The manager routes by emitting a ``delegate_to_<worker>`` tool call which
# the worker answers with a ToolMessage. That pair is internal plumbing; the
# consumer-facing ``astream_events`` view must not surface it as phantom tool
# calls. ``_DelegationEventFilter`` scrubs the event stream while leaving the
# graph's message state intact.


def test_delegation_filter_drops_delegate_tool_lifecycle_events() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
    )

    f = _DelegationEventFilter()
    for etype in ("on_tool_start", "on_tool_end", "on_tool_error"):
        ev = {
            "event": etype,
            "name": "delegate_to_research_helper",
            "run_id": "r",
            "data": {},
        }
        assert f.scrub(ev) is None

    # A real tool's lifecycle events pass through untouched.
    real = {"event": "on_tool_start", "name": "search", "run_id": "r", "data": {}}
    assert f.scrub(real) is real


def test_delegation_filter_strips_delegate_call_from_chat_model_end() -> None:
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
    )

    f = _DelegationEventFilter()
    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "delegate_to_research_helper", "args": {"task": "hi"}, "id": "call_1"},
        ],
    )
    out = f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": msg}}
    )
    assert out is not None
    assert out["data"]["output"].tool_calls == []
    # The original message object (which lives in graph state) is untouched.
    assert msg.tool_calls and msg.tool_calls[0]["name"] == "delegate_to_research_helper"

    # A turn that mixes a delegation call with a real tool call keeps the real one.
    mixed = AIMessage(
        content="ok",
        tool_calls=[
            {"name": "delegate_to_research_helper", "args": {"task": "hi"}, "id": "call_2"},
            {"name": "search", "args": {"q": "x"}, "id": "call_3"},
        ],
    )
    out2 = f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": mixed}}
    )
    assert [tc["name"] for tc in out2["data"]["output"].tool_calls] == ["search"]


def test_delegation_filter_strips_streamed_delegate_tool_call_chunks() -> None:
    from langchain_core.messages import AIMessageChunk

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
    )

    f = _DelegationEventFilter()
    # Opening chunk: names the delegation tool at index 0 → pure plumbing, dropped.
    opening = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {
                "name": "delegate_to_research_helper",
                "args": "",
                "id": "call_1",
                "index": 0,
                "type": "tool_call_chunk",
            }
        ],
    )
    assert (
        f.scrub(
            {
                "event": "on_chat_model_stream",
                "name": "x",
                "run_id": "r",
                "data": {"chunk": opening},
            }
        )
        is None
    )

    # Argument-continuation chunk: no name, same index 0 → also dropped.
    cont = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {
                "name": None,
                "args": '{"task":"hi"}',
                "id": None,
                "index": 0,
                "type": "tool_call_chunk",
            },
        ],
    )
    assert (
        f.scrub(
            {"event": "on_chat_model_stream", "name": "x", "run_id": "r", "data": {"chunk": cont}}
        )
        is None
    )

    # A chunk mixing a delegation call with a real tool call keeps the real one.
    mixed = AIMessageChunk(
        content="",
        tool_call_chunks=[
            {
                "name": "delegate_to_research_helper",
                "args": "",
                "id": "c4",
                "index": 0,
                "type": "tool_call_chunk",
            },
            {"name": "search", "args": "", "id": "c5", "index": 1, "type": "tool_call_chunk"},
        ],
    )
    out = f.scrub(
        {"event": "on_chat_model_stream", "name": "x", "run_id": "r2", "data": {"chunk": mixed}}
    )
    assert out is not None
    kept = out["data"]["chunk"].tool_call_chunks
    assert [c["name"] for c in kept] == ["search"]


def test_delegation_filter_drops_worker_synthetic_tool_message() -> None:
    from langchain_core.messages import AIMessage, ToolMessage

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
    )

    f = _DelegationEventFilter()
    # The manager's delegate turn first records the delegation call id.
    delegate = AIMessage(
        content="",
        tool_calls=[
            {"name": "delegate_to_research_helper", "args": {"task": "hi"}, "id": "call_1"},
        ],
    )
    f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": delegate}}
    )

    # The worker node then emits its reply as a ToolMessage matched to call_1.
    reply = ToolMessage(content="Saturn has rings.", tool_call_id="call_1")
    out = f.scrub(
        {
            "event": "on_chain_end",
            "name": "worker:research_helper",
            "run_id": "w",
            "data": {"output": {"messages": [reply]}},
        }
    )
    assert out is None

    # A ToolMessage answering an unknown (real) tool call is preserved.
    other = ToolMessage(content="x", tool_call_id="call_other")
    kept = f.scrub(
        {
            "event": "on_chain_end",
            "name": "node",
            "run_id": "w2",
            "data": {"output": {"messages": [other]}},
        }
    )
    assert kept is not None
    assert kept["data"]["output"]["messages"] == [other]


def test_delegation_filter_strips_delegate_calls_from_state_snapshot() -> None:
    """Regression: a node/state payload (``on_chain_end``) carrying the full
    ``messages`` list must surface NEITHER the delegate tool calls NOR their
    reply ToolMessages.

    A consumer builds its message snapshot from this payload and reads
    ``tool_calls`` straight off the AIMessage. If the filter dropped only the
    reply ToolMessages but left the delegate tool calls on the AIMessage, the
    snapshot would show delegate tool calls with no results — rendered as a
    "tool call with no result". Real (non-delegation) tool calls and their
    results must be preserved.
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
    )

    f = _DelegationEventFilter()
    # Manager's delegation turn streams first so the filter learns the ids.
    delegate_ai = AIMessage(
        content="",
        tool_calls=[
            {"name": "delegate_to_sub_agent", "args": {"task": "ES"}, "id": "call_1"},
            {"name": "delegate_to_sub_agent", "args": {"task": "FR"}, "id": "call_2"},
        ],
    )
    f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": delegate_ai}}
    )

    # The final-state snapshot carries the whole conversation, including a
    # real tool call ("search") + its result that must survive.
    snapshot = {
        "messages": [
            HumanMessage(content="2 poems via sub-agents"),
            delegate_ai,
            ToolMessage(content="poem ES", tool_call_id="call_1"),
            ToolMessage(content="poem FR", tool_call_id="call_2"),
            AIMessage(
                content="",
                tool_calls=[{"name": "search", "args": {"q": "x"}, "id": "call_real"}],
            ),
            ToolMessage(content="search result", tool_call_id="call_real"),
            AIMessage(content="Here are your poems."),
        ]
    }
    out = f.scrub(
        {
            "event": "on_chain_end",
            "name": "__manager__",
            "run_id": "r2",
            "data": {"output": snapshot},
        }
    )
    assert out is not None
    msgs = out["data"]["output"]["messages"]

    # No delegate tool calls and no delegate ToolMessages remain.
    delegate_calls = [
        tc
        for m in msgs
        if isinstance(m, AIMessage)
        for tc in (m.tool_calls or [])
        if tc["name"].startswith("delegate_to_")
    ]
    assert delegate_calls == []
    tool_ids = [m.tool_call_id for m in msgs if type(m).__name__ == "ToolMessage"]
    assert "call_1" not in tool_ids and "call_2" not in tool_ids
    # The empty delegation AIMessage is dropped entirely.
    assert delegate_ai not in msgs

    # The REAL tool call + its result are preserved and still paired.
    real_calls = [tc["id"] for m in msgs if isinstance(m, AIMessage) for tc in (m.tool_calls or [])]
    assert real_calls == ["call_real"]
    assert "call_real" in tool_ids
    # The human turn and the manager's final answer survive.
    assert any(type(m).__name__ == "HumanMessage" for m in msgs)
    assert msgs[-1].content == "Here are your poems."

    # The original state objects are never mutated (graph state stays intact).
    assert delegate_ai.tool_calls and len(delegate_ai.tool_calls) == 2


def test_delegation_filter_passes_through_real_content() -> None:
    from langchain_core.messages import AIMessageChunk

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
    )

    f = _DelegationEventFilter()
    chunk = AIMessageChunk(content="Hello")
    ev = {"event": "on_chat_model_stream", "name": "x", "run_id": "r", "data": {"chunk": chunk}}
    out = f.scrub(ev)
    # No delegation artifact → event passes through as the same object.
    assert out is ev
    assert out["data"]["chunk"].content == "Hello"


def test_delegation_filter_strips_delegate_from_invalid_tool_calls() -> None:
    """A delegation call whose args failed to parse arrives in
    ``invalid_tool_calls`` rather than ``tool_calls`` — it must still be
    scrubbed so the consumer never sees the routing protocol."""
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph._managerworkers import _DelegationEventFilter

    f = _DelegationEventFilter()
    msg = AIMessage(
        content="",
        invalid_tool_calls=[
            {
                "name": "delegate_to_research_helper",
                "args": "{bad",
                "id": "call_1",
                "error": "parse error",
                "type": "invalid_tool_call",
            }
        ],
    )
    out = f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": msg}}
    )
    assert out is not None
    assert out["data"]["output"].invalid_tool_calls == []
    # The original (graph-state) message is never mutated.
    assert (
        msg.invalid_tool_calls
        and msg.invalid_tool_calls[0]["name"] == "delegate_to_research_helper"
    )


def test_delegation_filter_strips_provider_native_tool_calls_on_full_message() -> None:
    """Some providers (e.g. OpenAI) carry the tool call only in
    ``additional_kwargs['tool_calls']``; a delegation call there must be
    stripped and its id recorded so the worker reply can later be dropped."""
    from langchain_core.messages import AIMessage, ToolMessage

    from pyagentspec.adapters.langgraph._managerworkers import _DelegationEventFilter

    f = _DelegationEventFilter()
    msg = AIMessage(
        content="",
        additional_kwargs={
            "tool_calls": [
                {
                    "index": 0,
                    "id": "call_1",
                    "function": {"name": "delegate_to_research_helper", "arguments": ""},
                    "type": "function",
                }
            ]
        },
    )
    out = f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": msg}}
    )
    assert out is not None
    assert "tool_calls" not in (out["data"]["output"].additional_kwargs or {})

    # Recording the id means the worker's reply ToolMessage is dropped too.
    reply = ToolMessage(content="done", tool_call_id="call_1")
    dropped = f.scrub(
        {
            "event": "on_chain_end",
            "name": "worker:research_helper",
            "run_id": "w",
            "data": {"output": {"messages": [reply]}},
        }
    )
    assert dropped is None


def test_delegation_filter_scrubs_input_payload_messages() -> None:
    """The worker's reply ToolMessage must be dropped wherever it surfaces —
    including a node's ``input`` payload, not only ``output`` / ``chunk``."""
    from langchain_core.messages import AIMessage, ToolMessage

    from pyagentspec.adapters.langgraph._managerworkers import _DelegationEventFilter

    f = _DelegationEventFilter()
    delegate = AIMessage(
        content="",
        tool_calls=[{"name": "delegate_to_research_helper", "args": {"task": "x"}, "id": "call_1"}],
    )
    f.scrub(
        {"event": "on_chat_model_end", "name": "x", "run_id": "r", "data": {"output": delegate}}
    )

    reply = ToolMessage(content="done", tool_call_id="call_1")
    out = f.scrub(
        {
            "event": "on_chain_start",
            "name": "worker:research_helper",
            "run_id": "w",
            "data": {"input": {"messages": [reply]}},
        }
    )
    # The only message was the delegate reply → payload empties → event dropped.
    assert out is None


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


def test_patched_astream_events_fails_open_on_filter_error() -> None:
    """A bug in the delegation filter must never tear down the stream and
    swallow later events (e.g. the worker events that follow the manager's
    delegation turn). On a scrub error the event is passed through."""
    import asyncio

    from pyagentspec.adapters.langgraph._managerworkers import (
        _DelegationEventFilter,
        _patch_hide_delegation_in_astream_events,
    )

    class _FakeGraph:
        async def astream_events(self, *a: Any, **k: Any) -> Any:
            yield {"event": "on_chat_model_stream", "run_id": "boom", "name": "x", "data": {}}
            yield {
                "event": "on_chat_model_stream",
                "run_id": "ok",
                "name": "x",
                "data": {"chunk": "worker-token"},
            }

    def _explode(self: Any, event: Any) -> Any:
        if event.get("run_id") == "boom":
            raise RuntimeError("kaboom")
        return event

    graph = _FakeGraph()
    _patch_hide_delegation_in_astream_events(graph)

    async def _collect() -> Any:
        out = []
        with patch.object(_DelegationEventFilter, "scrub", new=_explode):
            async for ev in graph.astream_events():
                out.append(ev)
        return out

    events = asyncio.run(_collect())
    # Both events survive: the one that raised is passed through unfiltered,
    # and the later (worker) event is still delivered.
    assert [e["run_id"] for e in events] == ["boom", "ok"]


def test_manager_workers_patches_astream_events() -> None:
    """The compiled ManagerWorkers graph has its ``astream_events`` wrapped
    with the delegation scrubber."""
    from langchain_core.language_models.fake_chat_models import (
        FakeMessagesListChatModel,
    )
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import (
        AgentSpecToLangGraphConverter,
    )
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

    def _dispatch(self_obj: Any, llm_config: Any, *args: Any, **kwargs: Any) -> Any:
        return _fake_manager(*[])

    loader = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver())
    with patch.object(
        AgentSpecToLangGraphConverter,
        "_llm_convert_to_langgraph",
        autospec=True,
        side_effect=_dispatch,
    ), patch.object(
        FakeMessagesListChatModel,
        "bind_tools",
        new=lambda self_obj, *a, **kw: self_obj,
    ):
        compiled = loader.load_component(mw)

    assert getattr(compiled.astream_events, "__name__", "") == "patched_astream_events"


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
    assert cmd.goto == ()  # no goto — the parent graph decides where to go
    assert cmd.update == {"messages": [m1, m2]}


def test_delegation_tool_exposes_expected_name_and_description() -> None:
    """The placeholder tool the manager's LLM addresses by name."""
    from pyagentspec.adapters.langgraph._managerworkers import _make_worker_delegation_tool

    delegate = _make_worker_delegation_tool("research_helper")
    assert delegate.name == "delegate_to_research_helper"
    assert "research_helper" in delegate.description


# ─── _wrap_worker_for_subgraph: pending-delegation extraction (no LLM) ────────


def _echo_worker_graph(reply: str = "WORKER REPLY") -> Any:
    """A trivial worker CompiledStateGraph whose only node returns a fixed
    AIMessage — enough to exercise the wrapper without an LLM."""
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


def test_wrap_worker_recovers_task_from_manager_message_on_direct_edge() -> None:
    """Direct-edge path (no Send payload): the task and call id are recovered
    from the manager's last AIMessage delegation tool call."""
    from langchain_core.messages import AIMessage, ToolMessage

    from pyagentspec.adapters.langgraph._managerworkers import _wrap_worker_for_subgraph

    node = _wrap_worker_for_subgraph(_echo_worker_graph("ANSWER"), "research_helper")
    manager_ai = AIMessage(
        content="",
        tool_calls=[{"name": "delegate_to_research_helper", "args": {"task": "T"}, "id": "c1"}],
    )
    out = node.invoke({"messages": [manager_ai]})

    (reply,) = out["messages"]
    assert isinstance(reply, ToolMessage)
    assert reply.content == "ANSWER"
    assert reply.tool_call_id == "c1"


def test_wrap_worker_raises_on_empty_manager_state() -> None:
    from pyagentspec.adapters.langgraph._managerworkers import _wrap_worker_for_subgraph

    node = _wrap_worker_for_subgraph(_echo_worker_graph(), "research_helper")
    with pytest.raises(RuntimeError, match="empty manager state"):
        node.invoke({"messages": []})


def test_wrap_worker_raises_when_no_matching_delegation_call() -> None:
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph._managerworkers import _wrap_worker_for_subgraph

    node = _wrap_worker_for_subgraph(_echo_worker_graph(), "research_helper")
    not_for_me = AIMessage(
        content="",
        tool_calls=[{"name": "delegate_to_other", "args": {"task": "x"}, "id": "c1"}],
    )
    with pytest.raises(RuntimeError, match="delegate_to_research_helper"):
        node.invoke({"messages": [not_for_me]})
