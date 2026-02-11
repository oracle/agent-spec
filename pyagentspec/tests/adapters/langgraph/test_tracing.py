# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
from pathlib import Path
from typing import List, Tuple

from pyagentspec.tracing.events import (
    AgentExecutionEnd,
    AgentExecutionStart,
    Event,
    FlowExecutionEnd,
    FlowExecutionStart,
    LlmGenerationChunkReceived,
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


class DummySpanProcessor(SpanProcessor):
    """
    Minimal processor mirroring the behavior used in tests/tracing/test_tracing.py
    to capture span lifecycle and events for assertions.
    """

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


def check_dummyspanprocessor_agent_events_and_spans(span_processor: DummySpanProcessor) -> None:
    # Assertions on spans started/ended
    # We expect at least one of each span type during a normal run
    started_types = [type(s) for s in span_processor.starts]
    ended_types = [type(s) for s in span_processor.ends]

    assert any(
        issubclass(t, AgentExecutionSpan) for t in started_types
    ), "AgentExecutionSpan did not start"
    assert any(
        issubclass(t, AgentExecutionSpan) for t in ended_types
    ), "AgentExecutionSpan did not end"
    assert any(
        issubclass(t, LlmGenerationSpan) for t in started_types
    ), "LlmGenerationSpan did not start"
    assert any(
        issubclass(t, LlmGenerationSpan) for t in ended_types
    ), "LlmGenerationSpan did not end"

    assert any(
        issubclass(t, ToolExecutionSpan) for t in started_types
    ), "ToolExecutionSpan did not start"
    assert any(
        issubclass(t, ToolExecutionSpan) for t in ended_types
    ), "ToolExecutionSpan did not end"

    # Assertions on key events observed
    event_types = [type(e) for (e, _s) in span_processor.events]
    assert any(
        issubclass(t, AgentExecutionStart) for t in event_types
    ), "AgentExecutionStart not emitted"
    assert any(
        issubclass(t, AgentExecutionEnd) for t in event_types
    ), "AgentExecutionEnd not emitted"
    assert any(
        issubclass(t, LlmGenerationRequest) for t in event_types
    ), "LlmGenerationRequest not emitted"
    assert any(
        issubclass(t, LlmGenerationResponse) for t in event_types
    ), "LlmGenerationResponse not emitted"
    assert any(
        issubclass(t, ToolExecutionRequest) for t in event_types
    ), "ToolExecutionRequest not emitted"
    assert any(
        issubclass(t, ToolExecutionResponse) for t in event_types
    ), "ToolExecutionResponse not emitted"


def check_dummyspanprocessor_flow_events_and_spans(span_processor: DummySpanProcessor) -> None:
    # Assertions on spans started/ended
    # We expect at least one of each span type during a normal run
    started_types = [type(s) for s in span_processor.starts]
    ended_types = [type(s) for s in span_processor.ends]

    assert any(
        issubclass(t, FlowExecutionSpan) for t in started_types
    ), "FlowExecutionSpan did not start"
    assert any(
        issubclass(t, FlowExecutionSpan) for t in ended_types
    ), "FlowExecutionSpan did not end"
    assert any(
        issubclass(t, NodeExecutionSpan) for t in started_types
    ), "NodeExecutionSpan did not start"
    assert any(
        issubclass(t, NodeExecutionSpan) for t in ended_types
    ), "NodeExecutionSpan did not end"
    assert any(
        issubclass(t, LlmGenerationSpan) for t in started_types
    ), "LlmGenerationSpan did not start"
    assert any(
        issubclass(t, LlmGenerationSpan) for t in ended_types
    ), "LlmGenerationSpan did not end"

    assert any(
        issubclass(t, ToolExecutionSpan) for t in started_types
    ), "ToolExecutionSpan did not start"
    assert any(
        issubclass(t, ToolExecutionSpan) for t in ended_types
    ), "ToolExecutionSpan did not end"

    # Assertions on key events observed
    event_types = [type(e) for (e, _s) in span_processor.events]
    # Agent execution events are not emitted yet
    assert any(
        issubclass(t, FlowExecutionStart) for t in event_types
    ), "FlowExecutionStart not emitted"
    assert any(issubclass(t, FlowExecutionEnd) for t in event_types), "FlowExecutionEnd not emitted"
    assert any(
        issubclass(t, NodeExecutionStart) for t in event_types
    ), "NodeExecutionStart not emitted"
    assert any(issubclass(t, NodeExecutionEnd) for t in event_types), "NodeExecutionEnd not emitted"
    assert any(
        issubclass(t, LlmGenerationRequest) for t in event_types
    ), "LlmGenerationRequest not emitted"
    assert any(
        issubclass(t, LlmGenerationResponse) for t in event_types
    ), "LlmGenerationResponse not emitted"
    assert any(
        issubclass(t, ToolExecutionRequest) for t in event_types
    ), "ToolExecutionRequest not emitted"
    assert any(
        issubclass(t, ToolExecutionResponse) for t in event_types
    ), "ToolExecutionResponse not emitted"


def test_langgraph_invoke_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Prepare YAML config with placeholders replaced
    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)

    # Convert to LangGraph agent
    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummySpanProcessor()
    with Trace(name="langgraph_tracing_test", span_processors=[proc]):
        agent_input = {
            "inputs": {},
            "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
        }
        response = weather_agent.invoke(input=agent_input)
        assert "sunny" in str(response).lower()

    check_dummyspanprocessor_agent_events_and_spans(proc)


def test_langgraph_stream_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Prepare YAML config with placeholders replaced
    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)

    # Convert to LangGraph agent
    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummySpanProcessor()
    with Trace(name="langgraph_tracing_test", span_processors=[proc]):
        agent_input = {
            "inputs": {},
            "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
        }
        response = ""
        for message_chunk, metadata in weather_agent.stream(
            input=agent_input, stream_mode="messages"
        ):
            if message_chunk.content:
                response += message_chunk.content
        assert "sunny" in str(response).lower()

    check_dummyspanprocessor_agent_events_and_spans(proc)


def test_langgraph_invoke_tracing_emits_flow_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Prepare JSON config with placeholders replaced
    json_content = (CONFIGS / "haiku_without_a_flow.json").read_text()
    final_json = _replace_config_placeholders(json_content, json_server)

    # Convert to LangGraph agent
    flow = AgentSpecLoader(
        tool_registry={"remove_a": lambda haiku: haiku.replace("a", "")}
    ).load_json(final_json)

    proc = DummySpanProcessor()
    with Trace(name="langgraph_tracing_test", span_processors=[proc]):
        response = flow.invoke(input={"inputs": {}, "messages": []})
        assert "outputs" in response
        assert "haiku_without_a" in response["outputs"]
        assert "a" not in response["outputs"]["haiku_without_a"]

    check_dummyspanprocessor_flow_events_and_spans(proc)


def test_langgraph_stream_tracing_emits_flow_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Prepare JSON config with placeholders replaced
    json_content = (CONFIGS / "haiku_without_a_flow.json").read_text()
    final_json = _replace_config_placeholders(json_content, json_server)

    # Convert to LangGraph agent
    flow = AgentSpecLoader(
        tool_registry={"remove_a": lambda haiku: haiku.replace("a", "")}
    ).load_json(final_json)

    proc = DummySpanProcessor()
    with Trace(name="langgraph_tracing_test", span_processors=[proc]):
        for chunk in flow.stream(input={"inputs": {}, "messages": []}, stream_mode="values"):
            if chunk:
                response = chunk
        assert "outputs" in response
        assert "haiku_without_a" in response["outputs"]
        assert "a" not in response["outputs"]["haiku_without_a"]

    check_dummyspanprocessor_flow_events_and_spans(proc)


def test_langgraph_agent_emits_tool_calls_and_results_with_consistent_ids(json_server: str):

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Prepare YAML config with placeholders replaced
    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)

    # Convert to LangGraph agent
    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummySpanProcessor()
    with Trace(name="langgraph_tracing_tool_call_test", span_processors=[proc]):
        agent_input = {
            "inputs": {},
            "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
        }
        response = ""
        for message_chunk, metadata in weather_agent.stream(
            input=agent_input, stream_mode="messages"
        ):
            if message_chunk.content:
                response += message_chunk.content

    llm_response_chunk_events = [
        e for (e, _) in proc.events if isinstance(e, LlmGenerationChunkReceived)
    ]
    tool_call_chunks = [e for e in llm_response_chunk_events if len(e.tool_calls) == 1]
    streamed_tool_call_ids = {e.tool_calls[0].call_id for e in tool_call_chunks}

    # LangChain/LangGraph can stream provisional tool_call_ids that get abandoned before execution.
    # Only the tool_call_id that actually runs will trigger on_tool_start and create a ToolExecutionSpan,
    # so we assert that every executed span originated from the streamed IDs rather than enforcing
    # one-to-one equality between streamed and executed tool calls.
    tool_spans = [s for (_, s) in proc.events if isinstance(s, ToolExecutionSpan)]
    executed_tool_call_ids = {
        s.description.replace("tcid__", "") for s in tool_spans if s.description
    }

    # Every executed tool call must have been announced in the LLM chunks.
    assert executed_tool_call_ids.issubset(streamed_tool_call_ids)

    # Ensure at least one tool execution occurred so the test still exercises tool tracing.
    assert executed_tool_call_ids

    # TODO: Add robust event id matching asserts
