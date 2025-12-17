# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import sys
import time
import traceback
import uuid
from contextvars import ContextVar
from types import TracebackType
from typing import TYPE_CHECKING, Any, List, Optional, Type

from pydantic import ConfigDict, Field, PrivateAttr
from typing_extensions import Self

from pyagentspec.tracing._basemodel import BaseModelWithSensitiveInfo
from pyagentspec.tracing.events.event import Event

if TYPE_CHECKING:
    from pyagentspec.tracing.spanprocessor import SpanProcessor
    from pyagentspec.tracing.trace import Trace


_ACTIVE_SPAN_STACK: ContextVar[List["Span"]] = ContextVar("_ACTIVE_SPAN_STACK", default=[])

# setting it will ensure it's seen by `contextvars.copy_context()`
# because this doesn't use values with default that have not been passed
# this call is used in async <-> sync transitions to ensure propagation of
# context variables updates
_ACTIVE_SPAN_STACK.set([])


def _append_span_to_active_stack(span: "Span") -> None:
    span_stack = get_active_span_stack(return_copy=True)
    span_stack.append(span)
    _ACTIVE_SPAN_STACK.set(span_stack)


def _pop_span_from_active_stack() -> None:
    span_stack = get_active_span_stack(return_copy=True)
    span_stack.pop(-1)
    _ACTIVE_SPAN_STACK.set(span_stack)


def get_active_span_stack(return_copy: bool = True) -> List["Span"]:
    """
    Retrieve the stack of active spans in this context.

    Returns
    -------
        The stack of active spans in this context
    """
    from copy import copy

    span_stack = _ACTIVE_SPAN_STACK.get()
    return copy(span_stack) if return_copy else span_stack


def get_current_span() -> Optional["Span"]:
    """
    Retrieve the currently active span in this context.

    Returns
    -------
        The active span in this context
    """
    span_stack = get_active_span_stack(return_copy=False)
    if len(span_stack) > 0:
        return span_stack[-1]
    return None


class Span(BaseModelWithSensitiveInfo):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), frozen=True)
    """A unique identifier for the event"""
    name: Optional[str] = None
    """The name of the span. If None, the span class name is used."""
    description: str = ""
    """The description of the span."""
    start_time: Optional[int] = None
    """The timestamp of when the span was started"""
    end_time: Optional[int] = None
    """The timestamp of when the span was closed"""
    events: List[Event] = Field(default_factory=list)
    """The list of events recorded in the scope of this span"""
    metadata: dict[str, Any] = Field(default_factory=dict)
    """Metadata related to the span"""
    _parent_span: Optional["Span"] = PrivateAttr(default=None)
    _end_event_was_triggered: bool = PrivateAttr(default=False)
    _span_was_appended_to_active_stack: bool = PrivateAttr(default=False)
    _started_span_processors: List["SpanProcessor"] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        """Set the default name if it is not provided."""
        super().model_post_init(__context)
        if not self.name:
            self.name = self.__class__.__name__

    @property
    def _trace(self) -> Optional["Trace"]:
        """The Trace where this Span is being stored"""
        from pyagentspec.tracing.trace import get_trace

        return get_trace()

    @property
    def _span_processors(self) -> List[Any]:
        """The list of SpanProcessors to which this Span should be forwarded"""
        return self._trace.span_processors if self._trace else []

    def __enter__(self) -> Self:
        self.start()
        return self

    async def __aenter__(self) -> Self:
        await self.start_async()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback_obj: Optional[TracebackType],
    ) -> None:
        if exc_value is not None:
            from pyagentspec.tracing.events import ExceptionRaised

            self.add_event(
                ExceptionRaised(
                    exception_type=exc_type.__name__ if exc_type else "Unknown",
                    exception_message=str(exc_value),
                    exception_stacktrace="".join(
                        traceback.format_exception(exc_type, exc_value, traceback_obj)
                    ),
                )
            )
        self.end()

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if exc_value is not None:
            from pyagentspec.tracing.events import ExceptionRaised

            await self.add_event_async(
                ExceptionRaised(
                    exception_type=exc_type.__name__ if exc_type else "Unknown",
                    exception_message=str(exc_value),
                    exception_stacktrace=str(traceback),
                )
            )
        await self.end_async()

    def start(self) -> None:
        """
        Start the span.

        This includes calling the ``on_start`` method of the active SpanProcessors.
        """
        try:
            self._parent_span = get_current_span()
            self.start_time = time.time_ns()
            for span_processor in self._span_processors:
                span_processor.on_start(self)
                # We remember which span processors were started, so that we call on_end on them only
                # when we exit, e.g., because of an exception happening
                self._started_span_processors.append(span_processor)
            _append_span_to_active_stack(self)
            self._span_was_appended_to_active_stack = True
        except Exception as e:
            # If anything happens during the recording of the start span,
            # we still have to do the work needed to exit the context
            # including the span_processors.on_end call and removing the span from the active stack
            self.__exit__(*sys.exc_info())
            raise e

    async def start_async(self) -> None:
        """
        Start the span. Asynchronous method.

        This includes calling the ``on_start_async`` method of the active SpanProcessors.
        """
        try:
            self._parent_span = get_current_span()
            self.start_time = time.time_ns()
            for span_processor in self._span_processors:
                await span_processor.on_start_async(self)
                # We remember which span processors were started, so that we call on_end on them only
                # when we exit, e.g., because of an exception happening
                self._started_span_processors.append(span_processor)
            _append_span_to_active_stack(self)
            self._span_was_appended_to_active_stack = True
        except Exception as e:
            # If anything happens during the recording of the start span,
            # we still have to do the work needed to exit the context
            # including the span_processors.on_end call and removing the span from the active stack
            await self.__aexit__(*sys.exc_info())
            raise e

    def end(self) -> None:
        """
        End the span.

        This includes calling the ``on_end`` method of the active SpanProcessors.
        """
        try:
            exceptions_list: List[Exception] = []
            self.end_time = time.time_ns()
            # We call on_end only on the span_processors that were successfully started
            for span_processor in self._started_span_processors:
                # We catch the exceptions that are raised to ensure we call on_end on all
                # the span processors on which on_start was called
                try:
                    span_processor.on_end(self)
                except Exception as e:
                    exceptions_list.append(e)
            # If we caught exceptions in span processors, we raise one of them here (the first we caught)
            if len(exceptions_list) > 0:
                raise exceptions_list[0]
        finally:
            # Whatever happens, we have to pop the span if it is on the active spans stack
            if self._span_was_appended_to_active_stack:
                _pop_span_from_active_stack()

    async def end_async(self) -> None:
        """
        End the span. Asynchronous method.

        This includes calling the ``on_end_async`` method of the active SpanProcessors.
        """
        try:
            exceptions_list: List[Exception] = []
            self.end_time = time.time_ns()
            # We call on_end only on the span_processors that were successfully started
            for span_processor in self._started_span_processors:
                # We catch the exceptions that are raised to ensure we call on_end on all
                # the span processors on which on_start was called
                try:
                    await span_processor.on_end_async(self)
                except Exception as e:
                    exceptions_list.append(e)
            # If we caught exceptions in span processors, we raise one of them here (the first we caught)
            if len(exceptions_list) > 0:
                raise exceptions_list[0]
        finally:
            # Whatever happens, we have to pop the span if it is on the active spans stack
            if self._span_was_appended_to_active_stack:
                _pop_span_from_active_stack()

    def add_event(self, event: Event) -> None:
        """Add an event to the span and trigger ``on_event`` on the active ``SpanProcessors``."""
        self.events.append(event)
        for span_processor in self._started_span_processors:
            span_processor.on_event(event, self)

    async def add_event_async(self, event: Event) -> None:
        """Add an event to the span and trigger ``on_event_async`` on the active ``SpanProcessors``."""
        self.events.append(event)
        for span_processor in self._started_span_processors:
            await span_processor.on_event_async(event, self)
