# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Wrap a compiled graph's ``stream``/``astream`` in an Agent Spec execution span.

Agent, Flow and ManagerWorkers graphs all need the same wrapper: open a span, emit a
Start event carrying the invocation inputs, yield the chunks the underlying stream
produces while remembering the last state chunk, then emit an End event built from
that final state. Only the span class and the two event payloads differ, so they come
in as factories. ``invoke``/``ainvoke`` need no patch; they use ``stream``/``astream``
internally.
"""

from typing import Any, AsyncGenerator, Callable, Dict, Generator

from pyagentspec.adapters.langgraph._types import CompiledStateGraph


def _invocation_inputs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """The ``input=`` argument of the patched call, or ``{}`` when it isn't a dict."""
    inputs = kwargs.get("input", {})
    return inputs if isinstance(inputs, dict) else {}


def _final_state(chunk: Any, so_far: Any) -> Any:
    """Fold one streamed chunk into the running "last state seen".

    State arrives as ``(namespace, state)`` tuples; other chunk shapes aren't
    something to build the End event from, so they leave the fold untouched.
    """
    return chunk[1] if isinstance(chunk, tuple) else so_far


async def _async_or_sync(
    async_call: Callable[..., Any], sync_call: Callable[..., Any], *args: Any
) -> None:
    """Await ``async_call``, falling back to ``sync_call`` for spans that don't
    implement the async half of the tracing protocol."""
    try:
        await async_call(*args)
    except NotImplementedError:
        sync_call(*args)


def patch_with_execution_span(
    compiled_graph: CompiledStateGraph[Any, Any, Any],
    *,
    make_span: Callable[[], Any],
    make_start_event: Callable[[Dict[str, Any]], Any],
    make_end_event: Callable[[Dict[str, Any]], Any],
) -> None:
    """Monkey-patch ``compiled_graph.stream`` / ``.astream`` to run inside a span.

    ``make_start_event`` receives the invocation inputs; ``make_end_event``
    receives the final state chunk (``{}`` when the run produced none).
    """
    original_stream = compiled_graph.stream
    original_astream = compiled_graph.astream

    def patched_stream(*args: Any, **kwargs: Any) -> Generator[Any, Any, None]:
        with make_span() as span:
            span.add_event(make_start_event(_invocation_inputs(kwargs)))
            state: Any = {}
            for chunk in original_stream(*args, **kwargs):
                yield chunk
                state = _final_state(chunk, state)
            span.add_event(make_end_event(state if isinstance(state, dict) else {}))

    async def patched_astream(*args: Any, **kwargs: Any) -> AsyncGenerator[Any, Any]:
        span = make_span()
        await _async_or_sync(span.start_async, span.start)
        try:
            start_event = make_start_event(_invocation_inputs(kwargs))
            await _async_or_sync(span.add_event_async, span.add_event, start_event)
            state: Any = {}
            async for chunk in original_astream(*args, **kwargs):
                yield chunk
                state = _final_state(chunk, state)
            end_event = make_end_event(state if isinstance(state, dict) else {})
            await _async_or_sync(span.add_event_async, span.add_event, end_event)
        finally:
            await _async_or_sync(span.end_async, span.end)

    compiled_graph.stream = patched_stream  # type: ignore[assignment]
    compiled_graph.astream = patched_astream  # type: ignore[assignment]
