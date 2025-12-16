# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import uuid
from contextvars import ContextVar
from types import TracebackType
from typing import List, Optional, Type

from pyagentspec.tracing.spanprocessor import SpanProcessor
from pyagentspec.tracing.spans import RootSpan, Span

_TRACE: ContextVar[Optional["Trace"]] = ContextVar("_TRACE", default=None)


def get_trace() -> Optional["Trace"]:
    """
    Get the Trace object active in the current context.

    Returns
    -------
        The active Trace object
    """
    return _TRACE.get()


class Trace:
    """
    The root of a collection of Spans.

    It is used to group together all the spans and events emitted during the execution of an assistant.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        span_processors: Optional[List[SpanProcessor]] = None,
        shutdown_on_exit: bool = True,
        root_span: Optional[Span] = None,
    ):
        """
        Parameters
        ----------
        name: Optional[str]
            The name of the trace
        id: str
            A unique identifier for the trace
        span_processors: List[SpanProcessor]
            The list of SpanProcessors active on this trace
        shutdown_on_exit: bool
            Whether to call shutdown on span processors when the trace context is closed
        root_span: Optional[Span]
            The root span of the trace. If None, a new RootSpan with default values is used.
        """
        self.name = name or "Trace"
        self.id = id or str(uuid.uuid4())
        self.span_processors = span_processors or []
        self.shutdown_on_exit = shutdown_on_exit
        self._root_span = root_span or RootSpan()

    def __enter__(self) -> "Trace":
        self._start()
        return self

    async def __aenter__(self) -> "Trace":
        await self._start_async()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: TracebackType,
    ) -> None:
        self._end()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: TracebackType,
    ) -> None:
        await self._end_async()

    def _start(self) -> None:
        if _TRACE.get() is not None:
            raise RuntimeError("A Trace already exists. Cannot create two nested Traces.")
        _TRACE.set(self)
        for span_processor in self.span_processors:
            span_processor.startup()
        self._root_span.start()

    async def _start_async(self) -> None:
        if _TRACE.get() is not None:
            raise RuntimeError("A Trace already exists. Cannot create two nested Traces.")
        _TRACE.set(self)
        for span_processor in self.span_processors:
            await span_processor.startup_async()
        await self._root_span.start_async()

    def _end(self) -> None:
        self._root_span.end()
        _TRACE.set(None)
        if self.shutdown_on_exit:
            for span_processor in self.span_processors:
                span_processor.shutdown()

    async def _end_async(self) -> None:
        await self._root_span.end_async()
        _TRACE.set(None)
        if self.shutdown_on_exit:
            for span_processor in self.span_processors:
                await span_processor.shutdown_async()
