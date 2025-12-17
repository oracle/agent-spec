# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import re
import time
from typing import List, Tuple

import pytest

from pyagentspec.tracing.events import Event, ExceptionRaised
from pyagentspec.tracing.spanprocessor import SpanProcessor
from pyagentspec.tracing.spans import RootSpan
from pyagentspec.tracing.spans.span import (
    Span,
    get_active_span_stack,
    get_current_span,
)
from pyagentspec.tracing.trace import Trace, get_trace

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


class DummySpanProcessor(SpanProcessor):

    def __init__(self, mask_sensitive_information: bool = True) -> None:
        super().__init__(mask_sensitive_information=mask_sensitive_information)
        self.started_up = False
        self.shut_down = False
        self.started_up_async = False
        self.shut_down_async = False
        self.starts: List[Span] = []
        self.ends: List[Span] = []
        self.events: List[Tuple[Event, Span]] = []
        self.starts_async: List[Span] = []
        self.ends_async: List[Span] = []
        self.events_async: List[Tuple[Event, Span]] = []

    def on_start(self, span: Span) -> None:
        self.starts.append(span)

    async def on_start_async(self, span: Span) -> None:
        self.starts_async.append(span)

    def on_end(self, span: Span) -> None:
        self.ends.append(span)

    async def on_end_async(self, span: Span) -> None:
        self.ends_async.append(span)

    def on_event(self, event: Event, span: Span) -> None:
        self.events.append((event, span))

    async def on_event_async(self, event: Event, span: Span) -> None:
        self.events_async.append((event, span))

    def startup(self) -> None:
        self.started_up = True

    def shutdown(self) -> None:
        self.shut_down = True

    async def startup_async(self) -> None:
        self.started_up_async = True

    async def shutdown_async(self) -> None:
        self.shut_down_async = True


@pytest.fixture
def dummy_span_processor() -> SpanProcessor:
    return DummySpanProcessor()


def test_event_default_name_and_fields() -> None:
    before_timestamp = time.time_ns()
    e = Event()
    after_timestamp = time.time_ns()
    # Default name is class name
    assert e.name == "Event"
    # id should look like a uuid
    assert isinstance(e.id, str) and UUID_RE.match(e.id)
    # timestamp should be an integer in ns
    assert before_timestamp <= e.timestamp <= after_timestamp and e.timestamp > 0


def test_span_instantiation_defaults() -> None:
    s = Span()
    # Default name is class name
    assert s.name == "Span"
    # id should look like a uuid
    assert isinstance(s.id, str) and UUID_RE.match(s.id)
    # start/end times are None until the span is started/ended
    assert s.start_time is None and s.end_time is None
    # No events by default
    assert s.events == []
    # Not entered as a context, shouldn't be active
    assert get_current_span() is None


def test_exception_event_creation_defaults() -> None:
    ex = ExceptionRaised(exception_type="ValueError", exception_message="bad input")
    # Name defaults to class name
    assert ex.name == "ExceptionRaised"
    assert ex.exception_type == "ValueError"
    # SensitiveField should accept plain str and retain value
    assert str(ex.exception_message) == "bad input"
    # Stacktrace has default
    assert isinstance(ex.exception_stacktrace, str)


def test_span_start_end_and_active_stack() -> None:
    stack_len_before = len(get_active_span_stack())
    s = Span(name="current_span")
    before_span_start = time.time_ns()
    s.start()
    after_span_start_before_end = time.time_ns()
    # Span s is the current one while active
    assert get_current_span() is s
    assert (
        s.start_time is not None
        and before_span_start <= s.start_time <= after_span_start_before_end
    )
    assert s.end_time is None
    # Active stack grew by 1
    assert len(get_active_span_stack()) == stack_len_before + 1
    s.end()
    after_span_end = time.time_ns()
    # After exit, span is closed and stack restored
    assert (
        s.start_time is not None
        and before_span_start <= s.start_time <= after_span_start_before_end
    )
    assert s.end_time is not None and after_span_start_before_end <= s.end_time <= after_span_end
    assert get_current_span() is None
    assert len(get_active_span_stack()) == stack_len_before


def test_span_start_end_and_active_stack_with_context_manager() -> None:
    stack_len_before = len(get_active_span_stack())
    with Span(name="current_span") as s:
        # Span s is the current one while active
        assert get_current_span() is s
        assert s.start_time is not None and s.end_time is None
        # Active stack grew by 1
        assert len(get_active_span_stack()) == stack_len_before + 1
    # After exit, span is closed and stack restored
    assert s.end_time is not None and s.end_time >= s.start_time  # type: ignore[arg-type]
    assert get_current_span() is None
    assert len(get_active_span_stack()) == stack_len_before


def test_span_parent_span_and_get_current() -> None:
    with Span() as parent:
        with Span() as child:
            # child recorded its parent span
            assert child._parent_span is parent
            assert get_current_span() is child
        # After child exits, current is parent
        assert get_current_span() is parent
    assert get_current_span() is None


def test_spanprocessor_hooks_called_by_span(dummy_span_processor: DummySpanProcessor) -> None:
    root_span = RootSpan()
    with Trace(name="T1", span_processors=[dummy_span_processor], root_span=root_span) as t:
        # Trace set in context
        assert root_span in get_active_span_stack()
        assert root_span is get_current_span()
        assert dummy_span_processor.starts == [root_span]
        assert get_trace() is t
        with Span() as s:
            assert s in get_active_span_stack()
            # on_start called for processor
            assert dummy_span_processor.starts == [root_span, s]
            ev = Event(name="custom_event")
            s.add_event(ev)
            # Event recorded both in span and processor
            assert s.events == [ev]
            assert dummy_span_processor.events == [(ev, s)]
        # on_end called
        assert dummy_span_processor.ends == [s]
        # Trace lifecycle hooks were invoked
        assert dummy_span_processor.started_up is True
        assert root_span in get_active_span_stack()
        assert root_span is get_current_span()
    assert dummy_span_processor.ends == [s, root_span]
    assert dummy_span_processor.shut_down is True
    # After exiting Trace, no active trace
    assert get_trace() is None


def test_trace_startup_shutdown_and_nesting(dummy_span_processor: DummySpanProcessor) -> None:
    with Trace(span_processors=[dummy_span_processor]):
        assert dummy_span_processor.started_up is True
        assert dummy_span_processor.started_up_async is False
        assert get_trace() is not None
        # Nested Trace not allowed
        with pytest.raises(RuntimeError, match="A Trace already exists"):
            with Trace():
                pass
    assert dummy_span_processor.shut_down is True
    assert dummy_span_processor.shut_down_async is False


def test_span_emits_exception_event_on_error() -> None:
    with Trace():
        with pytest.raises(RuntimeError):
            with Span() as s:
                raise RuntimeError("boom")
    # after exception, span ended and contains ExceptionRaised in events
    assert any(isinstance(ev, ExceptionRaised) for ev in s.events)


def test_add_event_async_calls_async_handlers(dummy_span_processor: DummySpanProcessor) -> None:

    async def run():
        async_ev = Event(name="async_ev")
        with Trace(span_processors=[dummy_span_processor]):
            with Span() as s:
                await s.add_event_async(async_ev)
        return async_ev

    ev = asyncio.run(run())
    assert len(dummy_span_processor.events_async) == 1
    assert dummy_span_processor.events_async[0][0] is ev


# =========================
# Asynchronous variants
# =========================


def test_span_start_end_and_active_stack_async_manual(
    dummy_span_processor: DummySpanProcessor,
) -> None:
    root_span = RootSpan()

    async def run():
        stack_len_before = len(get_active_span_stack())
        async with Trace(span_processors=[dummy_span_processor], root_span=root_span) as t:
            stack_len_in_trace = len(get_active_span_stack())
            assert stack_len_in_trace == stack_len_before + 1
            s = Span(name="current_span")
            before_span_start = time.time_ns()
            await s.start_async()
            after_span_start_before_end = time.time_ns()
            # Span s is the current one while active
            assert get_current_span() is s
            assert (
                s.start_time is not None
                and before_span_start <= s.start_time <= after_span_start_before_end
            )
            assert s.end_time is None
            # Active stack grew by 1
            assert len(get_active_span_stack()) == stack_len_in_trace + 1
            await s.end_async()
            after_span_end = time.time_ns()
            # After exit, span is closed and stack restored
            assert (
                s.start_time is not None
                and before_span_start <= s.start_time <= after_span_start_before_end
            )
            assert (
                s.end_time is not None
                and after_span_start_before_end <= s.end_time <= after_span_end
            )
            assert get_current_span() is t._root_span
        assert get_current_span() is None
        return stack_len_before, s

    stack_len_before, s = asyncio.run(run())
    # After loop, stack back to original size
    assert len(get_active_span_stack()) == stack_len_before
    # Async processor methods were invoked
    assert dummy_span_processor.starts_async == [root_span, s]
    assert dummy_span_processor.ends_async == [s, root_span]


def test_span_start_end_and_active_stack_with_async_context_manager(
    dummy_span_processor: DummySpanProcessor,
) -> None:
    root_span = RootSpan()

    async def run():
        stack_len_before = len(get_active_span_stack())
        async with Trace(span_processors=[dummy_span_processor], root_span=root_span):
            assert root_span in get_active_span_stack()
            assert root_span is get_current_span()
            stack_len_in_trace = len(get_active_span_stack())
            assert stack_len_in_trace == stack_len_before + 1
            async with Span(name="current_span") as s:
                # Span s is the current one while active
                assert get_current_span() is s
                assert s.start_time is not None and s.end_time is None
                # Active stack grew by 1
                assert len(get_active_span_stack()) == stack_len_in_trace + 1
            # After exit, span is closed and stack restored
            assert s.end_time is not None and s.end_time >= s.start_time
            assert root_span in get_active_span_stack()
            assert root_span is get_current_span()
        assert get_current_span() is None
        return stack_len_before, s

    stack_len_before, s = asyncio.run(run())
    assert len(get_active_span_stack()) == stack_len_before
    assert dummy_span_processor.starts_async == [root_span, s]
    assert dummy_span_processor.ends_async == [s, root_span]


def test_span_parent_span_and_get_current_async() -> None:
    async def run():
        with Trace() as t:
            async with Span() as parent:
                async with Span() as child:
                    # child recorded its parent span
                    assert child._parent_span is parent
                    assert get_current_span() is child
                # After child exits, current is parent
                assert get_current_span() is parent
            assert get_current_span() is t._root_span
        assert get_current_span() is None
        return True

    assert asyncio.run(run()) is True


def test_spanprocessor_hooks_called_by_span_async(
    dummy_span_processor: DummySpanProcessor,
) -> None:
    async def run():
        with Trace(name="T1-async", span_processors=[dummy_span_processor]) as t:
            # Trace set in context
            assert get_trace() is t
            async with Span() as s:
                assert s in get_active_span_stack()
                # on_start_async called for processor
                assert dummy_span_processor.starts_async == [s]
                ev = Event(name="custom_event_async")
                await s.add_event_async(ev)
                # Event recorded both in span and processor (async)
                assert s.events == [ev]
                assert dummy_span_processor.events_async == [(ev, s)]
            # on_end_async called
            assert dummy_span_processor.ends_async == [s]  # type: ignore[name-defined]
            # Trace lifecycle hooks were invoked
            assert dummy_span_processor.started_up is True
        assert dummy_span_processor.shut_down is True
        # After exiting Trace, no active trace
        assert get_trace() is None
        return True

    assert asyncio.run(run()) is True


def test_span_emits_exception_event_on_error_async() -> None:
    async def run():
        with Trace():
            with pytest.raises(RuntimeError):
                async with Span() as s:
                    raise RuntimeError("boom-async")
        # after exception, span ended and contains ExceptionRaised in events
        assert any(isinstance(ev, ExceptionRaised) for ev in s.events)
        return True

    assert asyncio.run(run()) is True


def test_trace_startup_shutdown_and_nesting_async(dummy_span_processor: DummySpanProcessor) -> None:

    async def run():
        async with Trace(span_processors=[dummy_span_processor]):
            assert dummy_span_processor.started_up is False
            assert dummy_span_processor.started_up_async is True
            assert get_trace() is not None
            # Nested Trace not allowed
            with pytest.raises(RuntimeError, match="A Trace already exists"):
                with Trace():
                    pass
        assert dummy_span_processor.shut_down is False
        assert dummy_span_processor.shut_down_async is True
        return True

    assert asyncio.run(run()) is True
