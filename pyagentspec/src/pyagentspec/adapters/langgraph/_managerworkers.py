# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""ManagerWorkers LangGraph compilation helpers.

Module-level building blocks for compiling a ``ManagerWorkers`` into LangGraph.
The ``AgentSpecToLangGraphConverter`` method
``_manager_workers_convert_to_langgraph`` orchestrates these helpers; the
helpers themselves are pure functions with no dependency on the converter,
which is why they live here rather than bloating the converter module.
"""

import logging
import re
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple

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

# ─── ManagerWorkers helpers ──────────────────────────────────────────────────

# Node key for the manager subgraph in the ManagerWorkers parent StateGraph.
# Chosen so it cannot collide with a normalized worker node name (which is
# always lowercase + [a-z0-9_]).
_MANAGER_NODE_KEY = "__manager__"

# Prefix the manager's LLM uses to address a delegation tool. The suffix is
# the normalized worker node name.
_DELEGATE_TOOL_PREFIX = "delegate_to_"

# Keys carried on the per-delegation ``Send`` payload from the manager's
# routing edge to a worker node, so a worker run knows which task it was
# given and which ``tool_call_id`` its reply ToolMessage must answer. This
# is what lets one manager turn delegate to several workers at once: each
# delegation routes as its own ``Send`` and is answered independently.
_DELEGATE_TASK_KEY = "__delegate_task__"
_DELEGATE_CALL_ID_KEY = "__delegate_tool_call_id__"

# Collapses any run of whitespace to a single space so multi-line worker
# descriptions stay on one roster line.
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_identifier(s: str) -> str:
    """Lowercase, collapse non-alphanumerics to underscores, strip surrounding
    underscores. The single source of truth for turning a spec name into an
    ASCII identifier, so a worker node name and the ``delegate_to_<worker>``
    tool name addressing it always agree."""
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _safe_node_name(name: str, fallback_id: str) -> str:
    """Normalize a worker name into a LangGraph node identifier.

    LangGraph node names must be hashable strings; in practice we want
    ASCII-friendly identifiers that also work as Python attribute-ish
    names (the LLM is going to see ``delegate_to_<node_name>`` as a tool
    name and needs to be able to emit it reliably). We normalize via
    :func:`_normalize_identifier`, and fall back to the (component) id —
    normalized the same way — if the name yields an empty string. Falling
    through both transforms keeps node names internally consistent
    regardless of which input wins.
    """
    return _normalize_identifier(name) or _normalize_identifier(fallback_id) or "worker"


def _tc_get(tool_call: Any, key: str) -> Any:
    """Read ``key`` off a tool call that may be a dict or a pydantic-style
    object (langchain emits either depending on the message source)."""
    if isinstance(tool_call, dict):
        return tool_call.get(key)
    return getattr(tool_call, key, None)


def _messages_of(state: Any) -> List[Any]:
    """Read the ``messages`` list off a state that may be a dict or an
    attribute-bearing object (langgraph injects either into a tool)."""
    if isinstance(state, dict):
        return list(state.get("messages") or [])
    return list(getattr(state, "messages", []) or [])


def _surface_to_parent_command(state: Any) -> Any:
    """The delegation tool's body: break out of the manager's react loop and
    project the subgraph's messages — including the AIMessage carrying the
    triggering tool call — onto the PARENT state, carrying **no** ``goto``
    (routing is the parent graph's job). The ``add_messages`` reducer dedupes
    by id, so re-surfacing existing messages is a no-op. Modelled on
    ``langgraph_swarm.create_handoff_tool``."""
    from langgraph.types import Command

    return Command(graph=Command.PARENT, update={"messages": _messages_of(state)})


def _append_workers_roster(
    system_prompt: str,
    entries: List[Tuple[str, str]],
) -> str:
    """Prepend the manager's system prompt with an ``Available workers:``
    roster block listing ``- <name>: <description>`` per worker.

    Each description has whitespace flattened so multi-line descriptions
    don't corrupt the one-line-per-worker block shape that the LLM relies
    on for routing.
    """
    if not entries:
        return system_prompt
    lines = [
        f"- {name}: {_WHITESPACE_RE.sub(' ', description).strip()}" for name, description in entries
    ]
    roster = "Available workers:\n" + "\n".join(lines)
    return f"{system_prompt}\n\n{roster}" if system_prompt else roster


def _make_worker_delegation_tool(worker_node_name: str) -> Any:
    """Build the ``delegate_to_<worker>`` tool the manager's LLM emits to route to a
    worker. The body carries **no** ``goto`` — routing fans out one ``Send`` per
    delegation (:func:`_route_manager_to_worker_or_end`); a ``goto`` here would
    collapse multiple same-turn delegations into one parent Command, leaving the other
    ``tool_call_id``s unanswered.
    """
    from typing import Annotated

    from langchain_core.tools import InjectedToolCallId, tool
    from langgraph.prebuilt import InjectedState
    from langgraph.types import Command

    tool_name = f"{_DELEGATE_TOOL_PREFIX}{worker_node_name}"

    @tool(tool_name)
    def _delegate(
        task: str,
        state: Annotated[Any, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Delegate a task to the named worker and wait for its reply.

        ``task`` is the natural-language instruction the worker should
        execute. The worker runs in its own isolated message context;
        only this ``task`` is forwarded as the worker's first message.
        """
        del task, tool_call_id  # recovered from the surfaced AIMessage by the routing edge
        return _surface_to_parent_command(state)

    _delegate.description = (
        f"Delegate a task to the {worker_node_name} worker and receive "
        f"its response. Use this when the task fits the worker's "
        f"described capability."
    )
    return _delegate


def _route_manager_to_worker_or_end(state: Dict[str, Any]) -> Any:
    """Inspect the manager's last AIMessage and route the parent graph: one
    ``Send`` per ``delegate_to_<worker>`` tool call, or ``END`` when the manager
    emitted none.

    A single manager turn may emit several ``delegate_to_<worker>`` calls; each gets its
    own ``Send`` carrying the ``task`` + ``tool_call_id``, so every call is answered
    independently (an unanswered delegation breaks the manager's next-turn
    tool-call/result sequence). Multiple ``Send``s to one worker run independently; plain
    tool calls already ran inside the manager's react loop.
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
        if _is_delegate_name(name):
            args = _tc_get(tc, "args") or {}
            sends.append(
                Send(
                    name[len(_DELEGATE_TOOL_PREFIX) :],
                    {
                        _DELEGATE_TASK_KEY: args.get("task") or "",
                        _DELEGATE_CALL_ID_KEY: _tc_get(tc, "id") or "",
                    },
                )
            )
    return sends or langgraph_graph.END


def _wrap_worker_for_subgraph(
    worker_graph: CompiledStateGraph[Any, Any, Any],
    worker_node_name: str,
) -> Any:
    """Wrap a worker subgraph so it runs with an isolated ``messages``
    context (the delegation task only) and its final reply comes back as
    a ToolMessage matched to the manager's pending delegation tool-call.

    This is what makes a ManagerWorkers parent graph hierarchical rather
    than a shared-state Swarm: workers do NOT see each other's messages,
    and only one message — the manager's chosen task — is forwarded to
    each worker run. The worker's last AIMessage content is captured as
    the ToolMessage content so the manager's react-agent loop sees a
    well-formed tool response on the next turn.

    Returns a ``RunnableLambda`` exposing both sync (``func``) and async
    (``afunc``) entrypoints — LangGraph picks the right one based on
    whether the parent graph is invoked via ``invoke`` or ``ainvoke``.
    """
    from langchain_core.messages import HumanMessage, ToolMessage

    from pyagentspec.adapters.langgraph._types import RunnableLambda

    delegate_tool_name = f"{_DELEGATE_TOOL_PREFIX}{worker_node_name}"

    def _extract_pending(state: Dict[str, Any]) -> Tuple[str, str]:
        # Fan-out path: the routing edge's ``Send`` payload carries this
        # delegation's task and its originating tool_call_id directly, so a
        # single manager turn can delegate to this worker more than once
        # without the runs colliding on a shared "first pending call".
        if isinstance(state, dict) and _DELEGATE_CALL_ID_KEY in state:
            return (
                state.get(_DELEGATE_TASK_KEY) or "",
                state.get(_DELEGATE_CALL_ID_KEY) or "",
            )
        # Direct-edge path (a worker wired in without Send): recover task +
        # id from the manager's last AIMessage. Only the first matching call
        # is recoverable this way, which is why routing prefers Send.
        messages = state.get("messages") or []
        if not messages:
            raise RuntimeError(f"Worker '{worker_node_name}' was invoked with empty manager state.")
        last_ai = messages[-1]
        tool_calls = getattr(last_ai, "tool_calls", None) or []
        pending_call = next(
            (tc for tc in tool_calls if _tc_get(tc, "name") == delegate_tool_name),
            None,
        )
        if pending_call is None:
            raise RuntimeError(
                f"Worker '{worker_node_name}' was routed to but the manager's "
                f"last message has no '{delegate_tool_name}' tool call."
            )
        args = _tc_get(pending_call, "args") or {}
        call_id = _tc_get(pending_call, "id") or ""
        return args.get("task") or "", call_id

    def _tool_message_from(reply: str, call_id: str) -> Dict[str, Any]:
        return {"messages": [ToolMessage(content=reply, tool_call_id=call_id)]}

    def _worker_input(task: str) -> Dict[str, Any]:
        # Pass NO explicit config so the worker inherits this node's ambient run config:
        # its ``checkpoint_ns`` (``<worker_node>:<task_id>``) is what streams the worker's
        # token events under the worker node, and the distinct per-superstep namespace
        # keeps repeated delegations isolated without a fresh thread_id.
        return {"messages": [HumanMessage(content=task)]}

    def _last_message_content(result: Any) -> str:
        messages = result.get("messages") if isinstance(result, dict) else None
        if not messages:
            return ""
        return getattr(messages[-1], "content", "") or ""

    def _run_sync(state: Dict[str, Any]) -> Dict[str, Any]:
        task, call_id = _extract_pending(state)
        result = worker_graph.invoke(_worker_input(task))
        return _tool_message_from(_last_message_content(result), call_id)

    async def _run_async(state: Dict[str, Any]) -> Dict[str, Any]:
        task, call_id = _extract_pending(state)
        result = await worker_graph.ainvoke(_worker_input(task))
        return _tool_message_from(_last_message_content(result), call_id)

    return RunnableLambda(
        func=_run_sync,
        afunc=_run_async,
        name=f"worker:{worker_node_name}",
    )


# ─── ManagerWorkers: hide the delegation protocol from astream_events ─────────


def _is_delegate_name(name: Any) -> bool:
    """True if ``name`` is one of the synthetic ``delegate_to_<worker>``
    tool names the manager emits to route to a worker."""
    return isinstance(name, str) and name.startswith(_DELEGATE_TOOL_PREFIX)


def _is_delegate_tool_message(msg: Any, delegate_call_ids: "set") -> bool:
    """True if ``msg`` is the worker's synthetic reply ToolMessage — i.e. a
    ToolMessage answering a (now-hidden) delegation tool-call id."""
    return (
        getattr(msg, "type", None) == "tool"
        and getattr(msg, "tool_call_id", None) in delegate_call_ids
    )


def _scrubbed_ai_message(
    msg: Any,
    delegate_indices: "set",
    delegate_call_ids: "set",
) -> Tuple[Optional[Any], bool]:
    """Return ``(scrubbed_copy_or_None, is_empty)`` for an AIMessage(Chunk),
    removing every ``delegate_to_<worker>`` tool call.

    ``scrubbed_copy_or_None`` is ``None`` when the message carried no
    delegation artifact (the caller emits it unchanged). ``is_empty`` is
    ``True`` when, after removal, nothing renderable remains (no content and
    no other tool calls) — the caller drops the event.

    Never mutates ``msg``: the same object lives in the graph's message
    state, where the manager react loop relies on the delegation
    tool-call / tool-result pair staying intact. ``delegate_indices`` tracks
    streamed tool-call positions so argument-continuation chunks (which
    carry no ``name``) are stripped too; ``delegate_call_ids`` collects the
    call ids so the worker's matching ToolMessage can be dropped later.
    """
    changed = False

    # Provider-native streamed tool calls (e.g. OpenAI) ride along in
    # ``additional_kwargs['tool_calls']`` and stream by index with the name
    # only on the opening delta — match by name or by a known delegate index.
    additional = getattr(msg, "additional_kwargs", None) or {}
    new_additional = additional
    raw_calls = additional.get("tool_calls")
    if raw_calls:
        kept_raw = []
        for tc in raw_calls:
            index = tc.get("index") if isinstance(tc, dict) else None
            function = (tc.get("function") or {}) if isinstance(tc, dict) else {}
            fname = function.get("name")
            if _is_delegate_name(fname) or (not fname and index in delegate_indices):
                if index is not None:
                    delegate_indices.add(index)
                if isinstance(tc, dict) and tc.get("id"):
                    delegate_call_ids.add(tc["id"])
                changed = True
            else:
                kept_raw.append(tc)
        if len(kept_raw) != len(raw_calls):
            new_additional = dict(additional)
            if kept_raw:
                new_additional["tool_calls"] = kept_raw
            else:
                new_additional.pop("tool_calls", None)

    # AIMessageChunk: ``tool_call_chunks`` is the source of truth and
    # ``tool_calls`` / ``invalid_tool_calls`` are *derived* from it, so we
    # rebuild the chunk (which re-runs that derivation) rather than copying —
    # otherwise a stale derived ``tool_calls`` entry survives the strip.
    if hasattr(msg, "tool_call_chunks"):
        kept_chunks = []
        for chunk in getattr(msg, "tool_call_chunks", None) or []:
            cname, cindex = chunk.get("name"), chunk.get("index")
            if _is_delegate_name(cname) or (cname is None and cindex in delegate_indices):
                if cindex is not None:
                    delegate_indices.add(cindex)
                if chunk.get("id"):
                    delegate_call_ids.add(chunk["id"])
                changed = True
            else:
                kept_chunks.append(chunk)
        if not changed:
            return None, False
        scrubbed = type(msg)(
            content=msg.content,
            additional_kwargs=new_additional,
            response_metadata=getattr(msg, "response_metadata", None) or {},
            tool_call_chunks=kept_chunks,
            id=getattr(msg, "id", None),
            name=getattr(msg, "name", None),
            usage_metadata=getattr(msg, "usage_metadata", None),
        )
        has_remaining = (
            bool(scrubbed.content)
            or bool(scrubbed.tool_call_chunks)
            or bool((scrubbed.additional_kwargs or {}).get("tool_calls"))
        )
        return scrubbed, not has_remaining

    # Full AIMessage: ``tool_calls`` is the source of truth.
    update: Dict[str, Any] = {}
    for attr in ("tool_calls", "invalid_tool_calls"):
        items = getattr(msg, attr, None)
        if items:
            kept = []
            for tc in items:
                if _is_delegate_name(_tc_get(tc, "name")):
                    cid = _tc_get(tc, "id")
                    if cid:
                        delegate_call_ids.add(cid)
                    changed = True
                else:
                    kept.append(tc)
            if len(kept) != len(items):
                update[attr] = kept
    if new_additional is not additional:
        update["additional_kwargs"] = new_additional
    if not changed:
        return None, False

    scrubbed = msg.model_copy(update=update)
    has_remaining = (
        bool(getattr(scrubbed, "content", None))
        or bool(getattr(scrubbed, "tool_calls", None))
        or bool((getattr(scrubbed, "additional_kwargs", None) or {}).get("tool_calls"))
    )
    return scrubbed, not has_remaining


def _scrub_payload_messages(
    payload: Any,
    delegate_call_ids: "set",
) -> Tuple[Any, bool]:
    """For a node / state payload shaped ``{"messages": [...]}``, remove the
    whole delegation protocol so it never surfaces in a consumer-facing
    message snapshot: drop the worker's synthetic reply ToolMessage(s) AND
    strip the synthetic ``delegate_to_<worker>`` tool calls off the manager's
    AIMessage(s), dropping an AIMessage that is left empty (a pure delegation
    turn).

    Stripping the tool calls — not just the ToolMessages — is what keeps a
    downstream message snapshot consistent. A consumer that builds its
    message history from an ``on_chain_end`` state payload (e.g. the AG-UI
    MESSAGES_SNAPSHOT) reads ``tool_calls`` straight off the AIMessage; if we
    dropped only the reply ToolMessages, the snapshot would carry delegate
    tool calls whose results are gone, which renders as a "tool call with no
    result". Messages are walked in order, so a delegation AIMessage records
    its call ids before its reply ToolMessages are tested for removal.

    Returns ``(payload, drop_event)``: ``payload`` is a new dict when
    anything changed (the original is never mutated), otherwise the object
    passed in. ``drop_event`` is ``True`` when scrubbing empties the
    ``messages`` list, so the caller drops the whole event.
    """
    if not isinstance(payload, dict):
        return payload, False
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return payload, False
    kept: List[Any] = []
    changed = False
    for m in messages:
        # The worker's reply ToolMessage — pure delegation plumbing.
        if _is_delegate_tool_message(m, delegate_call_ids):
            changed = True
            continue
        # An AIMessage may carry delegate tool calls; strip them and drop the
        # message if nothing renderable remains. Non-delegation messages
        # (real tool calls/results, plain content) are left untouched.
        if hasattr(m, "tool_calls"):
            scrubbed, is_empty = _scrubbed_ai_message(m, set(), delegate_call_ids)
            if scrubbed is not None:
                changed = True
                if not is_empty:
                    kept.append(scrubbed)
                continue
        kept.append(m)
    if not changed:
        return payload, False
    new_payload = dict(payload)
    new_payload["messages"] = kept
    return new_payload, len(kept) == 0


class _DelegationEventFilter:
    """Stateful scrubber for a single ``astream_events`` stream.

    Removes the synthetic ``delegate_to_<worker>`` routing protocol — the
    delegation tool calls, their ``on_tool_*`` lifecycle events, and the
    worker's matching reply ToolMessage — from the consumer-facing event
    view. The graph's message state is never touched, so the manager react
    loop still sees its well-formed tool-call / tool-result exchange.
    """

    def __init__(self) -> None:
        # Streamed tool-call positions per chat-model run that belong to a
        # delegation call, so argument-continuation chunks (name=None) are
        # stripped along with the opening chunk.
        self._delegate_indices_by_run: Dict[str, "set"] = {}
        # Delegate tool-call ids seen so far, so the worker's reply
        # ToolMessage can be dropped when it surfaces downstream.
        self._delegate_call_ids: "set" = set()

    def scrub(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        etype = event.get("event")
        name = event.get("name", "")

        # 1. Drop the tool lifecycle events for the delegation tools.
        if etype in ("on_tool_start", "on_tool_end", "on_tool_error") and _is_delegate_name(name):
            return None

        data = event.get("data") or {}

        # 2. Strip delegate tool calls from streamed / final manager AIMessages.
        if etype in ("on_chat_model_stream", "on_chat_model_end"):
            key = "chunk" if etype == "on_chat_model_stream" else "output"
            msg = data.get(key)
            if msg is not None and hasattr(msg, "tool_calls"):
                run_id = event.get("run_id", "")
                indices = self._delegate_indices_by_run.setdefault(run_id, set())
                scrubbed, is_empty = _scrubbed_ai_message(msg, indices, self._delegate_call_ids)
                if scrubbed is not None:
                    # A streamed chunk that became empty is pure delegation
                    # plumbing — drop it. A final ``on_chat_model_end`` is kept
                    # (scrubbed) so consumers still get a turn-end marker.
                    if is_empty and etype == "on_chat_model_stream":
                        return None
                    new_data = dict(data)
                    new_data[key] = scrubbed
                    new_event = dict(event)
                    new_event["data"] = new_data
                    return new_event
            return event

        # 3. Drop the worker's synthetic reply ToolMessage wherever it
        #    surfaces in a node payload.
        new_data: Optional[Dict[str, Any]] = None
        should_drop = False
        for key in ("chunk", "output", "input"):
            if key in data:
                scrubbed_payload, drop_event = _scrub_payload_messages(
                    data[key], self._delegate_call_ids
                )
                if scrubbed_payload is not data[key]:
                    if new_data is None:
                        new_data = dict(data)
                    new_data[key] = scrubbed_payload
                if drop_event:
                    should_drop = True
        if should_drop:
            return None
        if new_data is not None:
            new_event = dict(event)
            new_event["data"] = new_data
            return new_event
        return event


def _patch_hide_delegation_in_astream_events(
    compiled_graph: CompiledStateGraph[Any, Any, Any],
) -> None:
    """Wrap ``astream_events`` so the synthetic ``delegate_to_<worker>``
    routing protocol never reaches the consumer.

    ManagerWorkers routes by having the manager react-agent emit a
    ``delegate_to_<worker>`` tool call, which the worker answers with a
    ToolMessage matched to that call id. That pair is load-bearing for the
    manager's react loop (it must observe a well-formed tool-call /
    tool-result exchange) but it is internal plumbing the consumer should
    never see as phantom tool calls. We filter only the emitted events; the
    graph's message state is untouched, so the loop is unaffected. The
    workers' real LLM/token events still propagate (they reach the consumer
    via callback propagation through the isolated worker run), so this
    strips the routing noise without hiding the workers' actual output.
    """
    original_astream_events = compiled_graph.astream_events

    async def patched_astream_events(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, None]:
        event_filter = _DelegationEventFilter()
        async for event in original_astream_events(*args, **kwargs):
            if not isinstance(event, dict):
                yield event
                continue
            # Fail open: a scrubbing bug must never tear down the stream
            # (which would swallow every later event — notably the worker
            # events that follow the manager's delegation turn). On error we
            # emit the event unfiltered rather than dropping the rest.
            try:
                kept = event_filter.scrub(event)
            except Exception:  # noqa: BLE001 — defensive, see above
                logging.getLogger("pyagentspec.adapters.langgraph").warning(
                    "ManagerWorkers astream_events delegation filter raised; "
                    "passing the event through unfiltered.",
                    exc_info=True,
                )
                yield event
                continue
            if kept is not None:
                yield kept

    compiled_graph.astream_events = patched_astream_events  # type: ignore[assignment]


def _patch_with_manager_workers_execution_span(
    compiled_graph: CompiledStateGraph[Any, Any, Any],
    mw: AgentSpecManagerWorkers,
) -> None:
    """Wrap ``stream`` / ``astream`` so each ManagerWorkers run emits a
    ``ManagerWorkersExecutionSpan`` with Start/End events. Mirrors the
    patches applied to Agent and Flow compiled graphs elsewhere in this
    converter.
    """
    original_stream = compiled_graph.stream
    original_astream = compiled_graph.astream

    def _coerce_inputs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        inputs = kwargs.get("input", {})
        return inputs if isinstance(inputs, dict) else {}

    def patched_stream(*args: Any, **kwargs: Any) -> Generator[Any, Any, None]:
        span_name = f"ManagerWorkersExecution[{mw.name}]"
        inputs = _coerce_inputs(kwargs)
        with AgentSpecManagerWorkersExecutionSpan(name=span_name, managerworkers=mw) as span:
            span.add_event(AgentSpecManagerWorkersExecutionStart(managerworkers=mw, inputs=inputs))
            last_chunk: Dict[str, Any] = {}
            for chunk in original_stream(*args, **kwargs):
                yield chunk
                if isinstance(chunk, tuple) and isinstance(chunk[1], dict):
                    last_chunk = chunk[1]
            span.add_event(
                AgentSpecManagerWorkersExecutionEnd(
                    managerworkers=mw,
                    outputs={"messages": last_chunk.get("messages", [])},
                )
            )

    async def patched_astream(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, Any]:
        span_name = f"ManagerWorkersExecution[{mw.name}]"
        inputs = _coerce_inputs(kwargs)
        span = AgentSpecManagerWorkersExecutionSpan(name=span_name, managerworkers=mw)
        try:
            await span.start_async()
        except NotImplementedError:
            span.start()
        try:
            start_event = AgentSpecManagerWorkersExecutionStart(managerworkers=mw, inputs=inputs)
            try:
                await span.add_event_async(start_event)
            except NotImplementedError:
                span.add_event(start_event)
            last_chunk: Dict[str, Any] = {}
            async for chunk in original_astream(*args, **kwargs):
                yield chunk
                if isinstance(chunk, tuple) and isinstance(chunk[1], dict):
                    last_chunk = chunk[1]
            end_event = AgentSpecManagerWorkersExecutionEnd(
                managerworkers=mw,
                outputs={"messages": last_chunk.get("messages", [])},
            )
            try:
                await span.add_event_async(end_event)
            except NotImplementedError:
                span.add_event(end_event)
        finally:
            try:
                await span.end_async()
            except NotImplementedError:
                span.end()

    compiled_graph.stream = patched_stream  # type: ignore[assignment]
    compiled_graph.astream = patched_astream  # type: ignore[assignment]
