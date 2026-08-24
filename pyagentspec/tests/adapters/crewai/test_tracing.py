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
    LlmGenerationRequest,
    LlmGenerationResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from pyagentspec.tracing.spanprocessor import SpanProcessor
from pyagentspec.tracing.spans import AgentExecutionSpan, LlmGenerationSpan, Span, ToolExecutionSpan
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


def check_dummyspanprocessor_events_and_spans(span_processor: DummySpanProcessor) -> None:
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


def test_crewai_crew_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.crewai import AgentSpecLoader
    from pyagentspec.adapters.crewai._types import crewai

    # Prepare YAML config with placeholders replaced
    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)
    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    # Build a simple task/crew run
    task = crewai.Task(
        description="Use your tool to answer this simple request from the user: {user_input}",
        expected_output="A helpful, concise reply to the user.",
        agent=weather_agent,
    )
    crew = crewai.Crew(agents=[weather_agent], tasks=[task], verbose=False)

    proc = DummySpanProcessor()
    with Trace(name="crewai_tracing_test", span_processors=[proc]):
        with weather_agent.agentspec_event_listener():
            response = crew.kickoff(inputs={"user_input": "What's the weather in Agadir?"})
            assert "sunny" in str(response).lower()

    check_dummyspanprocessor_events_and_spans(proc)


def test_crewai_agent_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.crewai import AgentSpecLoader

    # Prepare YAML config with placeholders replaced
    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)
    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummySpanProcessor()
    with Trace(name="crewai_tracing_test", span_processors=[proc]):
        with weather_agent.agentspec_event_listener():
            response = weather_agent.kickoff(messages="What's the weather in Agadir?")
            assert "sunny" in str(response).lower()

    check_dummyspanprocessor_events_and_spans(proc)
