# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path
from typing import List, Tuple

import pytest

from pyagentspec.tracing.events import (
    AgentExecutionEnd,
    AgentExecutionStart,
    Event,
    FlowExecutionEnd,
    FlowExecutionStart,
    LlmGenerationRequest,
    LlmGenerationResponse,
    NodeExecutionEnd,
    NodeExecutionStart,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from pyagentspec.tracing.spanprocessor import SpanProcessor
from pyagentspec.tracing.spans import (
    AgentExecutionSpan,
    FlowExecutionSpan,
    LlmGenerationSpan,
    NodeExecutionSpan,
    Span,
    ToolExecutionSpan,
)
from pyagentspec.tracing.trace import Trace

from ..conftest import _replace_config_placeholders

CONFIGS = Path(__file__).parent / "configs"


class DummyAsyncOnlySpanProcessor(SpanProcessor):
    """
    Processor used to assert that async APIs are invoked and sync ones are not.
    """

    def __init__(self) -> None:
        super().__init__()
        # Sync calls storage — should stay empty
        self.starts: List[Span] = []
        self.ends: List[Span] = []
        self.events: List[Tuple[Event, Span]] = []
        self.started_up = False
        self.shut_down = False
        # Async calls storage — should contain all activity
        self.starts_async: List[Span] = []
        self.ends_async: List[Span] = []
        self.events_async: List[Tuple[Event, Span]] = []
        self.started_up_async = False
        self.shut_down_async = False

    # Sync methods — should not be called
    def on_start(self, span: Span) -> None:
        self.starts.append(span)

    def on_end(self, span: Span) -> None:
        self.ends.append(span)

    def on_event(self, event: Event, span: Span) -> None:
        self.events.append((event, span))

    def startup(self) -> None:
        self.started_up = True

    def shutdown(self) -> None:
        self.shut_down = True

    # Async methods — should be called exclusively for async runs
    async def on_start_async(self, span: Span) -> None:
        self.starts_async.append(span)

    async def on_end_async(self, span: Span) -> None:
        self.ends_async.append(span)

    async def on_event_async(self, event: Event, span: Span) -> None:
        self.events_async.append((event, span))

    async def startup_async(self) -> None:
        self.started_up_async = True

    async def shutdown_async(self) -> None:
        self.shut_down_async = True


def _assert_agent_llm_tool_async(proc: DummyAsyncOnlySpanProcessor) -> None:
    # Sync startup/shutdown must not be used in async Trace
    assert proc.started_up is False
    assert proc.shut_down is False

    # Async spans
    started_types = [type(s) for s in proc.starts_async]
    ended_types = [type(s) for s in proc.ends_async]
    assert any(issubclass(t, AgentExecutionSpan) for t in started_types)
    assert any(issubclass(t, AgentExecutionSpan) for t in ended_types)
    assert any(issubclass(t, LlmGenerationSpan) for t in started_types)
    assert any(issubclass(t, LlmGenerationSpan) for t in ended_types)
    assert any(issubclass(t, ToolExecutionSpan) for t in started_types)
    assert any(issubclass(t, ToolExecutionSpan) for t in ended_types)

    # Async events
    etypes = [type(e) for (e, _s) in proc.events_async]
    assert any(issubclass(t, AgentExecutionStart) for t in etypes)
    assert any(issubclass(t, AgentExecutionEnd) for t in etypes)
    assert any(issubclass(t, LlmGenerationRequest) for t in etypes)
    assert any(issubclass(t, LlmGenerationResponse) for t in etypes)
    assert any(issubclass(t, ToolExecutionRequest) for t in etypes)
    assert any(issubclass(t, ToolExecutionResponse) for t in etypes)

    # Ensure key events are not emitted via sync API
    sync_etypes = [type(e) for (e, _s) in proc.events]
    assert not any(issubclass(t, AgentExecutionStart) for t in sync_etypes)
    assert not any(issubclass(t, AgentExecutionEnd) for t in sync_etypes)
    assert not any(issubclass(t, LlmGenerationRequest) for t in sync_etypes)
    assert not any(issubclass(t, LlmGenerationResponse) for t in sync_etypes)
    assert not any(issubclass(t, ToolExecutionRequest) for t in sync_etypes)
    assert not any(issubclass(t, ToolExecutionResponse) for t in sync_etypes)


def _assert_flow_async(proc: DummyAsyncOnlySpanProcessor) -> None:
    # Sync startup/shutdown must not be used in async Trace
    assert proc.started_up is False
    assert proc.shut_down is False

    # Async spans (Flow + Node + LLM/Tool must be async)
    started_types = [type(s) for s in proc.starts_async]
    ended_types = [type(s) for s in proc.ends_async]
    assert any(issubclass(t, FlowExecutionSpan) for t in started_types)
    assert any(issubclass(t, FlowExecutionSpan) for t in ended_types)
    assert any(issubclass(t, NodeExecutionSpan) for t in started_types)
    assert any(issubclass(t, NodeExecutionSpan) for t in ended_types)
    assert any(issubclass(t, LlmGenerationSpan) for t in started_types)
    assert any(issubclass(t, LlmGenerationSpan) for t in ended_types)
    assert any(issubclass(t, ToolExecutionSpan) for t in started_types)
    assert any(issubclass(t, ToolExecutionSpan) for t in ended_types)

    # Async events
    etypes = [type(e) for (e, _s) in proc.events_async]
    assert any(issubclass(t, FlowExecutionStart) for t in etypes)
    assert any(issubclass(t, FlowExecutionEnd) for t in etypes)
    assert any(issubclass(t, NodeExecutionStart) for t in etypes)
    assert any(issubclass(t, NodeExecutionEnd) for t in etypes)
    assert any(issubclass(t, LlmGenerationRequest) for t in etypes)
    assert any(issubclass(t, LlmGenerationResponse) for t in etypes)
    assert any(issubclass(t, ToolExecutionRequest) for t in etypes)
    assert any(issubclass(t, ToolExecutionResponse) for t in etypes)

    # Ensure flow-level key events are not emitted via sync API
    sync_etypes = [type(e) for (e, _s) in proc.events]
    assert not any(issubclass(t, FlowExecutionStart) for t in sync_etypes)
    assert not any(issubclass(t, FlowExecutionEnd) for t in sync_etypes)
    assert not any(issubclass(t, NodeExecutionStart) for t in sync_etypes)
    assert not any(issubclass(t, NodeExecutionEnd) for t in sync_etypes)
    assert not any(issubclass(t, LlmGenerationRequest) for t in sync_etypes)
    assert not any(issubclass(t, LlmGenerationResponse) for t in sync_etypes)
    assert not any(issubclass(t, ToolExecutionRequest) for t in sync_etypes)
    assert not any(issubclass(t, ToolExecutionResponse) for t in sync_etypes)


@pytest.mark.anyio
async def test_langgraph_ainvoke_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)

    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummyAsyncOnlySpanProcessor()
    async with Trace(name="langgraph_tracing_async_test", span_processors=[proc]):
        agent_input = {
            "inputs": {},
            "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
        }
        response = await weather_agent.ainvoke(input=agent_input)
        assert "sunny" in str(response).lower()

    _assert_agent_llm_tool_async(proc)


@pytest.mark.anyio
async def test_langgraph_astream_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)

    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummyAsyncOnlySpanProcessor()
    async with Trace(name="langgraph_tracing_async_test", span_processors=[proc]):
        agent_input = {
            "inputs": {},
            "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
        }
        response = ""
        async for message_chunk, metadata in weather_agent.astream(
            input=agent_input, stream_mode="messages"
        ):
            if message_chunk.content:
                response += message_chunk.content
        assert "sunny" in str(response).lower()

    _assert_agent_llm_tool_async(proc)


@pytest.mark.anyio
async def test_langgraph_ainvoke_tracing_emits_flow_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    json_content = (CONFIGS / "haiku_without_a_flow.json").read_text()
    final_json = _replace_config_placeholders(json_content, json_server)

    flow = AgentSpecLoader(
        tool_registry={"remove_a": lambda haiku: haiku.replace("a", "")}
    ).load_json(final_json)

    proc = DummyAsyncOnlySpanProcessor()
    async with Trace(name="langgraph_tracing_async_test", span_processors=[proc]):
        response = await flow.ainvoke(input={"inputs": {}, "messages": []})
        assert "outputs" in response
        assert "haiku_without_a" in response["outputs"]
        assert "a" not in response["outputs"]["haiku_without_a"]

    _assert_flow_async(proc)


@pytest.mark.anyio
async def test_langgraph_astream_tracing_emits_flow_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    json_content = (CONFIGS / "haiku_without_a_flow.json").read_text()
    final_json = _replace_config_placeholders(json_content, json_server)

    flow = AgentSpecLoader(
        tool_registry={"remove_a": lambda haiku: haiku.replace("a", "")}
    ).load_json(final_json)

    proc = DummyAsyncOnlySpanProcessor()
    async with Trace(name="langgraph_tracing_async_test", span_processors=[proc]):
        async for chunk in flow.astream(input={"inputs": {}, "messages": []}, stream_mode="values"):
            if chunk:
                response = chunk
        assert "outputs" in response
        assert "haiku_without_a" in response["outputs"]
        assert "a" not in response["outputs"]["haiku_without_a"]

    _assert_flow_async(proc)
