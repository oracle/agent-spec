# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Helpers for compiling a ``ManagerWorkers`` into LangGraph, orchestrated by
``AgentSpecToLangGraphConverter._manager_workers_convert_to_langgraph``.

The delegation protocol is visible on purpose: ``__delegate_to__<worker>`` calls
stream like any other tool call. Consumers that would rather not render them can
filter on :func:`is_delegation_tool_name`.
"""

import re
from typing import Annotated, Any, Dict, Iterable, List, Tuple

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

# Cannot collide with a worker node name: _normalize_identifier strips leading and
# trailing underscores, so no normalized name ever starts with one.
_MANAGER_NODE_KEY = "__manager__"

#: Prefix of the synthetic ``__delegate_to__<worker>`` tool names the manager's LLM
#: uses to address a worker. The dunder prefix, like the delegation keys below, keeps
#: it from colliding with a real tool named ``delegate_to_<something>``. Re-exported
#: from ``pyagentspec.adapters.langgraph`` so consumers can recognize the protocol.
DELEGATE_TOOL_PREFIX = "__delegate_to__"

# Keys of the per-delegation ``Send`` payload: the task to run, and the tool_call_id
# the worker's reply must answer. Routing per delegation (instead of off shared state)
# lets one manager turn delegate to several workers at once.
_DELEGATE_TASK_KEY = "__delegate_task__"
_DELEGATE_CALL_ID_KEY = "__delegate_tool_call_id__"

_WHITESPACE_RE = re.compile(r"\s+")


def is_delegation_tool_name(name: Any) -> bool:
    """True for the synthetic ``__delegate_to__<worker>`` tool names a manager emits."""
    return isinstance(name, str) and name.startswith(DELEGATE_TOOL_PREFIX)


def _normalize_identifier(s: str) -> str:
    """Lowercase, collapse non-alphanumerics to underscores, strip leading/trailing ones."""
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _safe_node_name(name: str, fallback_id: str) -> str:
    """Normalize a worker name into a LangGraph node identifier.

    The LLM has to emit ``__delegate_to__<node_name>`` reliably as a tool name, so node
    names stay ASCII identifiers. Falls back to the normalized component id when the
    name slugifies to nothing.
    """
    return _normalize_identifier(name) or _normalize_identifier(fallback_id) or "worker"


def _messages_of(state: Any) -> List[Any]:
    """Read ``messages`` off a state, which langgraph injects as a dict or an object."""
    if isinstance(state, dict):
        return list(state.get("messages") or [])
    return list(getattr(state, "messages", []) or [])


def _append_workers_roster(system_prompt: str, entries: List[Tuple[str, str]]) -> str:
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


def _make_worker_delegation_tool(worker_node_name: str) -> Any:
    """Build the ``__delegate_to__<worker>`` tool the manager's LLM emits to route to
    a worker.

    Executing the tool is only how the call escapes the react subgraph: its body
    surfaces the subgraph messages to the parent with ``Command(graph=PARENT)`` and no
    ``goto``. Routing stays in the edge built by :func:`_make_manager_router`; a ``goto`` here
    would collapse several same-turn delegations into one parent Command and leave the
    other ``tool_call_id``s unanswered.
    """
    from langchain_core.tools import InjectedToolCallId, tool
    from langgraph.prebuilt import InjectedState
    from langgraph.types import Command

    tool_name = f"{DELEGATE_TOOL_PREFIX}{worker_node_name}"
    description = (
        f"Delegate a task to the {worker_node_name} worker and receive its response. "
        f"Use this when the task fits the worker's described capability."
    )

    @tool(tool_name, description=description)
    def _delegate(
        task: str,
        state: Annotated[Any, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Any:
        # task and tool_call_id are declared for the LLM-facing schema; the routing
        # edge recovers both off the surfaced AIMessage's tool_calls. The
        # add_messages reducer dedupes by id, so re-surfacing messages is a no-op.
        del task, tool_call_id
        return Command(graph=Command.PARENT, update={"messages": _messages_of(state)})

    return _delegate


def _make_manager_router(worker_node_names: Iterable[str]) -> Any:
    """Build the conditional edge routing the parent graph off the manager's last
    AIMessage: one ``Send`` per ``__delegate_to__<worker>`` tool call, or ``END``
    when it emitted none.

    Every delegation gets its own ``Send``, so each tool_call_id is answered
    independently; an unanswered one breaks the manager's next-turn tool-call/result
    sequence. Plain tool calls already ran inside the react loop; that includes a
    real tool whose name merely starts with the prefix, which is why a suffix that
    is not a worker node is not routed.
    """
    known_workers = frozenset(worker_node_names)

    def _route_manager_to_worker_or_end(state: Dict[str, Any]) -> Any:
        from langgraph.types import Send

        messages = state.get("messages") or []
        last = messages[-1] if messages else None
        sends = []
        for tool_call in getattr(last, "tool_calls", None) or []:
            name = tool_call.get("name")
            if not is_delegation_tool_name(name):
                continue
            worker_node_name = name[len(DELEGATE_TOOL_PREFIX) :]
            if worker_node_name not in known_workers:
                continue
            args = tool_call.get("args") or {}
            sends.append(
                Send(
                    worker_node_name,
                    {
                        _DELEGATE_TASK_KEY: args.get("task") or "",
                        _DELEGATE_CALL_ID_KEY: tool_call.get("id") or "",
                    },
                )
            )
        return sends or langgraph_graph.END

    return _route_manager_to_worker_or_end


def _worker_input(state: Dict[str, Any]) -> Dict[str, Any]:
    """The single-message context a worker run starts from."""
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


def _wrap_worker_for_subgraph(
    worker_graph: CompiledStateGraph[Any, Any, Any],
    worker_node_name: str,
) -> Any:
    """Wrap a worker subgraph as a node of the ManagerWorkers parent graph.

    Hierarchical rather than shared-state like a Swarm: each run is handed only the
    manager's chosen task, and the worker's answer comes back as a ToolMessage so the
    manager's react loop sees a well-formed tool response on its next turn. The worker
    is invoked with no explicit config and inherits this node's ambient run config,
    which streams its token events under the worker node's checkpoint namespace.
    """
    from pyagentspec.adapters.langgraph._types import RunnableLambda

    def run(state: Dict[str, Any]) -> Dict[str, Any]:
        return _worker_reply(state, worker_graph.invoke(_worker_input(state)))

    async def arun(state: Dict[str, Any]) -> Dict[str, Any]:
        return _worker_reply(state, await worker_graph.ainvoke(_worker_input(state)))

    return RunnableLambda(func=run, afunc=arun, name=f"worker:{worker_node_name}")


def _patch_with_manager_workers_execution_span(
    compiled_graph: CompiledStateGraph[Any, Any, Any],
    mw: AgentSpecManagerWorkers,
) -> None:
    """Wrap ``stream``/``astream`` so each run emits a ``ManagerWorkersExecutionSpan``."""
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
