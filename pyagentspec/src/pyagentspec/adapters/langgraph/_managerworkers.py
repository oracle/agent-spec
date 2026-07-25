# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Helpers for compiling a ``ManagerWorkers`` into LangGraph.

``AgentSpecToLangGraphConverter._manager_workers_convert_to_langgraph`` orchestrates
these; they live here to keep the converter module from growing further.

Nothing hides the routing protocol. ``delegate_to_<worker>`` calls stream like any
other tool call, because which worker got which task is usually the most useful thing
a run reports. Consumers that would rather not render it can filter on
:func:`is_delegation_tool_name`.
"""

import re
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from pyagentspec.adapters.langgraph._execution_span import patch_with_execution_span
from pyagentspec.adapters.langgraph._types import CompiledStateGraph, langgraph_graph
from pyagentspec.managerworkers import ManagerWorkers as AgentSpecManagerWorkers
from pyagentspec.tracing.events import (
    ManagerWorkersExecutionEnd as AgentSpecManagerWorkersExecutionEnd,
)
from pyagentspec.tracing.events import (
    ManagerWorkersExecutionStart as AgentSpecManagerWorkersExecutionStart,
)
from pyagentspec.tracing.spans import (
    ManagerWorkersExecutionSpan as AgentSpecManagerWorkersExecutionSpan,
)

# Cannot collide with a normalized worker node name, which is always [a-z0-9_].
_MANAGER_NODE_KEY = "__manager__"

#: Prefix the manager's LLM uses to address a delegation tool, suffixed with the
#: normalized worker node name. Public so consumers can recognize the protocol.
DELEGATE_TOOL_PREFIX = "delegate_to_"

# Carried on the per-delegation ``Send`` payload so a worker run knows its task and
# which ``tool_call_id`` its reply must answer. Routing per delegation instead of off
# shared state lets one manager turn delegate to several workers at once.
_DELEGATE_TASK_KEY = "__delegate_task__"
_DELEGATE_CALL_ID_KEY = "__delegate_tool_call_id__"

_WHITESPACE_RE = re.compile(r"\s+")


def is_delegation_tool_name(name: Any) -> bool:
    """True for the synthetic ``delegate_to_<worker>`` tool names a manager emits."""
    return isinstance(name, str) and name.startswith(DELEGATE_TOOL_PREFIX)


def _normalize_identifier(s: str) -> str:
    """Lowercase, collapse non-alphanumerics to underscores, strip leading/trailing ones."""
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _safe_node_name(name: str, fallback_id: str) -> str:
    """Normalize a worker name into a LangGraph node identifier.

    The LLM sees ``delegate_to_<node_name>`` as a tool name and has to emit it
    reliably, so node names stay ASCII identifiers. Falls back to the component id,
    normalized the same way, when the name slugifies to nothing.
    """
    return _normalize_identifier(name) or _normalize_identifier(fallback_id) or "worker"


def _tc_get(tool_call: Any, key: str) -> Any:
    """Read ``key`` off a tool call, which langchain emits as a dict or an object
    depending on the message source."""
    if isinstance(tool_call, dict):
        return tool_call.get(key)
    return getattr(tool_call, key, None)


def _messages_of(state: Any) -> List[Any]:
    """Read ``messages`` off a state, which langgraph injects as a dict or an object."""
    if isinstance(state, dict):
        return list(state.get("messages") or [])
    return list(getattr(state, "messages", []) or [])


def _surface_to_parent_command(state: Any) -> Any:
    """Break out of the manager's react loop, projecting the subgraph's messages onto
    the parent state (including the AIMessage carrying the triggering tool call).

    Carries no ``goto``: routing is the parent graph's job. The ``add_messages``
    reducer dedupes by id, so re-surfacing existing messages is a no-op. Modelled on
    ``langgraph_swarm.create_handoff_tool``.
    """
    from langgraph.types import Command

    return Command(graph=Command.PARENT, update={"messages": _messages_of(state)})


def _append_workers_roster(
    system_prompt: str,
    entries: List[Tuple[str, str]],
) -> str:
    """Append an ``Available workers:`` block listing ``- <name>: <description>``.

    Descriptions are flattened to one line each, since the LLM routes off the block's
    one-line-per-worker shape.
    """
    if not entries:
        return system_prompt
    lines = [
        f"- {name}: {_WHITESPACE_RE.sub(' ', description).strip()}" for name, description in entries
    ]
    roster = "Available workers:\n" + "\n".join(lines)
    return f"{system_prompt}\n\n{roster}" if system_prompt else roster


@lru_cache(maxsize=256)
def _make_worker_delegation_tool(worker_node_name: str) -> Any:
    """Build the ``delegate_to_<worker>`` tool the manager's LLM emits to route to a
    worker.

    The body carries no ``goto``. Routing fans out one ``Send`` per delegation in
    :func:`_route_manager_to_worker_or_end`; a ``goto`` here would collapse several
    same-turn delegations into one parent Command and leave the other
    ``tool_call_id``s unanswered.

    Memoized because the tool depends only on the node name and holds no per-graph
    state. Without it every compile re-runs the ``@tool`` decorator, which costs a
    ``get_type_hints`` pass and a pydantic args-schema build.
    """
    from typing import Annotated

    from langchain_core.tools import InjectedToolCallId, tool
    from langgraph.prebuilt import InjectedState
    from langgraph.types import Command

    tool_name = f"{DELEGATE_TOOL_PREFIX}{worker_node_name}"
    description = (
        f"Delegate a task to the {worker_node_name} worker and receive "
        f"its response. Use this when the task fits the worker's "
        f"described capability."
    )

    @tool(tool_name, description=description)
    def _delegate(
        task: str,
        state: Annotated[Any, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        # Declared for the LLM-facing schema but unused here: executing is only how the
        # call escapes the react subgraph, and the routing edge recovers both off the
        # surfaced AIMessage's tool_calls.
        del task, tool_call_id
        return _surface_to_parent_command(state)

    return _delegate


def _route_manager_to_worker_or_end(state: Dict[str, Any]) -> Any:
    """Route the parent graph off the manager's last AIMessage: one ``Send`` per
    ``delegate_to_<worker>`` tool call, or ``END`` when it emitted none.

    Every delegation gets its own ``Send`` carrying the task and ``tool_call_id``, so
    each is answered independently. An unanswered one breaks the manager's next-turn
    tool-call/result sequence. Plain tool calls already ran inside the react loop.
    """
    from langgraph.types import Send

    messages = state.get("messages") or []
    if not messages:
        return langgraph_graph.END
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    sends = []
    for tc in tool_calls:
        name = _tc_get(tc, "name")
        if is_delegation_tool_name(name):
            args = _tc_get(tc, "args") or {}
            sends.append(
                Send(
                    name[len(DELEGATE_TOOL_PREFIX) :],
                    {
                        _DELEGATE_TASK_KEY: args.get("task") or "",
                        _DELEGATE_CALL_ID_KEY: _tc_get(tc, "id") or "",
                    },
                )
            )
    return sends or langgraph_graph.END


def _worker_input(state: Dict[str, Any]) -> Dict[str, Any]:
    """The single-message context a worker run starts from.

    Passes no explicit config, so the worker inherits this node's ambient run config.
    Its ``checkpoint_ns`` (``<worker_node>:<task_id>``) streams the worker's token
    events under the worker node, and the per-superstep namespace keeps repeated
    delegations isolated without a fresh thread_id.
    """
    from langchain_core.messages import HumanMessage

    return {"messages": [HumanMessage(content=state.get(_DELEGATE_TASK_KEY) or "")]}


def _worker_reply(state: Dict[str, Any], result: Any) -> Dict[str, Any]:
    """The worker's last message, as a ToolMessage answering this delegation."""
    from langchain_core.messages import ToolMessage

    messages = result.get("messages") if isinstance(result, dict) else None
    content = (getattr(messages[-1], "content", "") if messages else "") or ""
    return {
        "messages": [
            ToolMessage(content=content, tool_call_id=state.get(_DELEGATE_CALL_ID_KEY) or "")
        ]
    }


class _WorkerSubgraphNode:
    """Runs one worker subgraph as a node of the ManagerWorkers parent graph.

    Hierarchical rather than shared-state like a Swarm: workers never see each other's
    messages, and each run is handed only the manager's chosen task. The worker's last
    message comes back as the ToolMessage content, so the manager's react loop sees a
    well-formed tool response on its next turn.

    A class rather than a closure, so the long-lived node holds only the graph instead
    of keeping a whole factory frame alive.
    """

    __slots__ = ("_graph",)

    def __init__(self, worker_graph: CompiledStateGraph[Any, Any, Any]) -> None:
        self._graph = worker_graph

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return _worker_reply(state, self._graph.invoke(_worker_input(state)))

    async def arun(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return _worker_reply(state, await self._graph.ainvoke(_worker_input(state)))


def _wrap_worker_for_subgraph(
    worker_graph: CompiledStateGraph[Any, Any, Any],
    worker_node_name: str,
) -> Any:
    """Wrap a worker subgraph as a node exposing sync and async entrypoints.

    LangGraph picks between them depending on whether the parent graph was invoked
    via ``invoke`` or ``ainvoke``.
    """
    from pyagentspec.adapters.langgraph._types import RunnableLambda

    node = _WorkerSubgraphNode(worker_graph)
    return RunnableLambda(func=node.run, afunc=node.arun, name=f"worker:{worker_node_name}")


def _patch_with_manager_workers_execution_span(
    compiled_graph: CompiledStateGraph[Any, Any, Any],
    mw: AgentSpecManagerWorkers,
) -> None:
    """Wrap ``stream``/``astream`` so each run emits a ``ManagerWorkersExecutionSpan``,
    using the same patcher as the Agent and Flow graphs."""
    patch_with_execution_span(
        compiled_graph,
        make_span=lambda: AgentSpecManagerWorkersExecutionSpan(
            name=f"ManagerWorkersExecution[{mw.name}]", managerworkers=mw
        ),
        make_start_event=lambda inputs: AgentSpecManagerWorkersExecutionStart(
            managerworkers=mw, inputs=inputs
        ),
        make_end_event=lambda result: AgentSpecManagerWorkersExecutionEnd(
            managerworkers=mw, outputs={"messages": result.get("messages", [])}
        ),
    )
