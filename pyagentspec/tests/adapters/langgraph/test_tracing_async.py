# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path

import pytest

from pyagentspec.tracing.events import (
    AgentExecutionEnd,
    AgentExecutionStart,
    FlowExecutionEnd,
    FlowExecutionStart,
    LlmGenerationRequest,
    LlmGenerationResponse,
    NodeExecutionEnd,
    NodeExecutionStart,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
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
from .test_tracing import DummySpanProcessor

CONFIGS = Path(__file__).parent / "configs"


def _assert_agent_llm_tool_async(proc: DummySpanProcessor) -> None:
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


def _assert_flow_async(
    proc: DummySpanProcessor,
    *,
    flow_tracing_has_llm: bool = True,
    expected_tool_response_outputs: dict[str, object] | None = None,
) -> None:
    # Sync startup/shutdown must not be used in async Trace
    assert proc.started_up is False
    assert proc.shut_down is False

    # Async spans (Flow + Node must be async, LLM when present)
    started_types = [type(s) for s in proc.starts_async]
    ended_types = [type(s) for s in proc.ends_async]
    assert any(issubclass(t, FlowExecutionSpan) for t in started_types)
    assert any(issubclass(t, FlowExecutionSpan) for t in ended_types)
    assert any(issubclass(t, NodeExecutionSpan) for t in started_types)
    assert any(issubclass(t, NodeExecutionSpan) for t in ended_types)
    assert any(issubclass(t, ToolExecutionSpan) for t in started_types)
    assert any(issubclass(t, ToolExecutionSpan) for t in ended_types)
    if flow_tracing_has_llm:
        assert any(issubclass(t, LlmGenerationSpan) for t in started_types)
        assert any(issubclass(t, LlmGenerationSpan) for t in ended_types)
    else:
        assert not any(issubclass(t, LlmGenerationSpan) for t in started_types)
        assert not any(issubclass(t, LlmGenerationSpan) for t in ended_types)

    # Async events
    etypes = [type(e) for (e, _s) in proc.events_async]
    assert any(issubclass(t, FlowExecutionStart) for t in etypes)
    assert any(issubclass(t, FlowExecutionEnd) for t in etypes)
    assert any(issubclass(t, NodeExecutionStart) for t in etypes)
    assert any(issubclass(t, NodeExecutionEnd) for t in etypes)
    assert any(issubclass(t, ToolExecutionRequest) for t in etypes)
    assert any(issubclass(t, ToolExecutionResponse) for t in etypes)
    if flow_tracing_has_llm:
        assert any(issubclass(t, LlmGenerationRequest) for t in etypes)
        assert any(issubclass(t, LlmGenerationResponse) for t in etypes)
    else:
        assert not any(issubclass(t, LlmGenerationRequest) for t in etypes)
        assert not any(issubclass(t, LlmGenerationResponse) for t in etypes)

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

    if expected_tool_response_outputs is not None:
        tool_response_events = [
            event
            for (event, _span) in proc.events_async
            if isinstance(event, ToolExecutionResponse)
        ]
        assert len(tool_response_events) == 1
        assert tool_response_events[0].outputs == expected_tool_response_outputs


@pytest.mark.anyio
async def test_langgraph_ainvoke_tracing_emits_agent_llm_and_tool_events(json_server: str) -> None:

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
    final_yaml = _replace_config_placeholders(yaml_content, json_server)

    weather_agent = AgentSpecLoader().load_yaml(final_yaml)

    proc = DummySpanProcessor()
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

    proc = DummySpanProcessor()
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

    async def ahaiku(haiku):
        return haiku.replace("a", "")

    flow = AgentSpecLoader(tool_registry={"remove_a": ahaiku}).load_json(final_json)

    proc = DummySpanProcessor()
    async with Trace(name="langgraph_tracing_async_test", span_processors=[proc]):
        response = await flow.ainvoke(input={"inputs": {}, "messages": []})
        assert "outputs" in response
        assert "haiku_without_a" in response["outputs"]
        assert "a" not in response["outputs"]["haiku_without_a"]

    _assert_flow_async(proc)


@pytest.mark.anyio
async def test_langgraph_astream_tracing_emits_flow_events(json_server: str) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    async def ahaiku(haiku):
        return haiku.replace("a", "")

    json_content = (CONFIGS / "haiku_without_a_flow.json").read_text()
    final_json = _replace_config_placeholders(json_content, json_server)

    flow = AgentSpecLoader(tool_registry={"remove_a": ahaiku}).load_json(final_json)

    proc = DummySpanProcessor()
    async with Trace(name="langgraph_tracing_async_test", span_processors=[proc]):
        async for chunk in flow.astream(input={"inputs": {}, "messages": []}, stream_mode="values"):
            if chunk:
                response = chunk
        assert "outputs" in response
        assert "haiku_without_a" in response["outputs"]
        assert "a" not in response["outputs"]["haiku_without_a"]

    _assert_flow_async(proc)


@pytest.mark.anyio
async def test_langgraph_ainvoke_tracing_emits_async_server_tool_events_for_flow() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
    from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
    from pyagentspec.flows.flow import Flow
    from pyagentspec.flows.nodes import ToolNode
    from pyagentspec.flows.nodes.endnode import EndNode
    from pyagentspec.flows.nodes.startnode import StartNode
    from pyagentspec.property import IntegerProperty, Property
    from pyagentspec.tools import ServerTool

    async def double_tool(x: int) -> int:
        return x * 2

    server_tool = ServerTool(
        name="double_tool",
        description="Doubles the input number",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
    )
    start_node = StartNode(name="start", inputs=server_tool.inputs)
    tool_node = ToolNode(name="tool", tool=server_tool)
    end_node = EndNode(name="end", outputs=server_tool.outputs)
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, tool_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_tool", from_node=start_node, to_node=tool_node),
            ControlFlowEdge(name="tool_to_end", from_node=tool_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output="x",
                destination_node=tool_node,
                destination_input="x",
            ),
            DataFlowEdge(
                name="output_edge",
                source_node=tool_node,
                source_output="result",
                destination_node=end_node,
                destination_input="result",
            ),
        ],
    )
    app = AgentSpecLoader(tool_registry={"double_tool": double_tool}).load_component(flow)

    proc = DummySpanProcessor()
    async with Trace(name="langgraph_tracing_async_server_tool_test", span_processors=[proc]):
        response = await app.ainvoke(input={"inputs": {"x": 5}})

    assert response["outputs"] == {"result": 10}
    _assert_flow_async(
        proc,
        flow_tracing_has_llm=False,
        expected_tool_response_outputs={"result": 10},
    )


@pytest.mark.anyio
async def test_langgraph_ainvoke_tracing_falls_back_to_sync_tool_events_for_agent(
    weather_agent_server_tool_yaml: str,
) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # This verifies the async-tracing fallback in the LangGraph callback handler:
    # tool events should use sync processor hooks when async tool-event hooks are not implemented,
    # while the surrounding agent/LLM tracing continues to use async hooks.
    class SyncToolEventFallbackSpanProcessor(DummySpanProcessor):
        async def on_event_async(self, event: object, span: Span) -> None:
            if isinstance(span, ToolExecutionSpan):
                raise NotImplementedError
            await super().on_event_async(event, span)

    async def get_weather(city: str) -> str:
        return f"The weather in {city} is sunny."

    weather_agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_server_tool_yaml
    )

    proc = SyncToolEventFallbackSpanProcessor()
    async with Trace(
        name="langgraph_tracing_async_server_tool_sync_fallback_test", span_processors=[proc]
    ):
        response = await weather_agent.ainvoke(
            input={
                "inputs": {},
                "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
            }
        )
        assert "sunny" in str(response).lower()

    assert proc.started_up is False
    assert proc.shut_down is False
    assert proc.started_up_async is True
    assert proc.shut_down_async is True

    sync_event_types = [type(e) for (e, _s) in proc.events]
    assert any(issubclass(t, ToolExecutionRequest) for t in sync_event_types)
    assert any(issubclass(t, ToolExecutionResponse) for t in sync_event_types)

    async_event_types = [type(e) for (e, _s) in proc.events_async]
    assert any(issubclass(t, AgentExecutionStart) for t in async_event_types)
    assert any(issubclass(t, LlmGenerationRequest) for t in async_event_types)
    assert not any(issubclass(t, ToolExecutionRequest) for t in async_event_types)
    assert not any(issubclass(t, ToolExecutionResponse) for t in async_event_types)


@pytest.mark.anyio
async def test_langgraph_ainvoke_tracing_emits_agent_llm_and_async_server_tool_events(
    weather_agent_server_tool_yaml: str,
) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    async def get_weather(city: str) -> str:
        return f"The weather in {city} is sunny."

    weather_agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_server_tool_yaml
    )

    proc = DummySpanProcessor()
    async with Trace(name="langgraph_tracing_async_server_tool_agent_test", span_processors=[proc]):
        response = await weather_agent.ainvoke(
            input={
                "inputs": {},
                "messages": [{"role": "user", "content": "What's the weather in Agadir?"}],
            }
        )
        assert "sunny" in str(response).lower()

    _assert_agent_llm_tool_async(proc)
