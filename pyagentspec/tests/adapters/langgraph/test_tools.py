# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any
from unittest.mock import patch

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import ToolNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.property import IntegerProperty, Property
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool


class DummyResponse:
    def __init__(self, obj):
        self._obj = obj

    @property
    def status_code(self):
        return 200

    def json(self):
        return self._obj


def test_remote_tool_having_nested_inputs_with_langgraph() -> None:
    """
    End-to-end: convert an AgentSpec RemoteTool to a LangGraph StructuredTool and run it.
    Patch httpx.request to capture the outgoing HTTP call and verify the rendered JSON payload.
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        city = kwargs["json"]["location"]["city"]
        return DummyResponse({"weather": f"sunny in {city}"})

    # Build a RemoteTool with nested data containing multiple template placeholders.
    remote_tool = RemoteTool(
        name="forecast_weather",
        description="Returns a forecast of the weather for the chosen city",
        url="https://weatherforecast.example/api/forecast/{{city}}",
        http_method="POST",
        data={
            "location": {
                "city": "{{city}}",
                "coordinates": {"lat": "{{lat}}", "lon": "{{lon}}"},
            },
            "meta": ["requested_by:{{user}}", {"note": "hello{{suffix}}"}],
            "raw": "binary-{{bin_suffix}}",
        },
        headers={"X-Caller": "{{user}}"},
    )

    # Convert to a LangGraph StructuredTool using the LangGraph adapter converter.
    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Expected object passed as the `json` kwarg to httpx.request after rendering.
    expected_json = {
        "location": {"city": "Agadir", "coordinates": {"lat": "30.4", "lon": "-9.6"}},
        "meta": ["requested_by:alice", {"note": "helloworld"}],
        "raw": "binary-blob",
    }

    # Patch httpx.request (used inside the converted langgraph tool) to capture the call.
    with patch("httpx.request", side_effect=mock_request) as patched_request:
        # Call the underlying function of the StructuredTool directly with keyword args.
        # The LangGraph converter wraps the function as a StructuredTool with .func attribute.
        result = lang_tool.func(
            city="Agadir", lat="30.4", lon="-9.6", user="alice", suffix="world", bin_suffix="blob"
        )
        # Ensure httpx.request was invoked and inspect the kwargs it was called with.
        patched_request.assert_called_once()
        called_args, called_kwargs = patched_request.call_args
        # The converter uses `json=remote_tool_data` when calling httpx.request for dict data
        assert (
            "json" in called_kwargs
        ), f"Expected 'json' kwarg in request call since json is a dict, got {called_kwargs}"
        assert called_kwargs["json"] == expected_json
        assert result == {"weather": "sunny in Agadir"}


def test_remote_tool_post_json_array_with_langgraph() -> None:
    """
    Test RemoteTool with JSON array body (data as list).
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        json_data = kwargs["json"]
        city = json_data[1]["location"]
        return DummyResponse({"processed_city": city})

    # Build a RemoteTool with data as a list containing placeholders.
    remote_tool = RemoteTool(
        name="process_array",
        description="Processes a JSON array body",
        url="https://example.com/api/process",
        http_method="POST",
        data=[
            "forecast",
            {"location": "{{city}}", "temp": "{{temp}}"},
        ],
        headers={"X-Caller": "{{user}}"},
    )

    # Convert to a LangGraph StructuredTool using the LangGraph adapter converter.
    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Expected rendered data (list).
    expected_data = [
        "forecast",
        {"location": "Agadir", "temp": "25"},
    ]

    # Patch httpx.request.
    with patch("httpx.request", side_effect=mock_request) as patched_request:
        # Call the underlying function of the StructuredTool directly with keyword args.
        result = lang_tool.func(
            city="Agadir",
            temp="25",
            user="alice",
        )
        patched_request.assert_called_once()
        called_args, called_kwargs = patched_request.call_args
        assert "json" in called_kwargs
        assert called_kwargs["json"] == expected_data
        assert result == {"processed_city": "Agadir"}


def test_remote_tool_post_raw_body_with_langgraph() -> None:
    """
    Test RemoteTool with raw string body (non-JSON, uses data=).
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        raw_data = kwargs["content"]
        # Extract city from raw body for dependency.
        city = raw_data.split("city: ")[1].split(" ")[0]
        return DummyResponse({"echoed_body": raw_data, "city": city})

    # Build a RemoteTool with data as a string containing placeholders.
    remote_tool = RemoteTool(
        name="send_raw",
        description="Sends a raw string body",
        url="https://example.com/api/raw",
        http_method="POST",
        data="request body for city: {{city}} with note: {{note}}",
        headers={"X-Caller": "{{user}}"},
    )

    # Convert to a LangGraph StructuredTool using the LangGraph adapter converter.
    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Expected rendered data (str).
    expected_data = "request body for city: Agadir with note: urgent"

    # Patch httpx.request.
    with patch("httpx.request", side_effect=mock_request) as patched_request:
        # Call the underlying function of the StructuredTool directly with keyword args.
        result = lang_tool.func(
            city="Agadir",
            note="urgent",
            user="alice",
        )
        patched_request.assert_called_once()
        called_args, called_kwargs = patched_request.call_args
        assert "content" in called_kwargs
        assert called_kwargs["content"] == expected_data
        assert result["city"] == "Agadir"


@pytest.mark.parametrize(
    "data, headers, is_json_payload",
    [
        (
            {"value": "{{ v1 }}", "listofvalues": ["a", "{{ v2 }}", "c"]},
            {"header1": "{{ h1 }}"},
            True,
        ),
        (
            {"value": "{{ v1 }}", "listofvalues": ["a", "{{ v2 }}", "c"]},
            {"header1": "{{ h1 }}", "Content-Type": "application/x-www-form-urlencoded"},
            False,
        ),
        ("value: {{ v1 }}, listofvalues: [a, {{ v2 }}, c]", {"header1": "{{ h1 }}"}, False),
        (["value: {{ v1 }}", "listofvalues: [a, {{ v2 }}, c]"], {"header1": "{{ h1 }}"}, True),
    ],
)
def test_remote_tool_actual_endpoint_with_langgraph(
    json_server: str, data, headers, is_json_payload
) -> None:
    """
    Real-server test using the in-repo FastAPI app (json_server fixture).
    Validates templating, JSON vs form vs raw payload handling, headers, query params, and path rendering.
    """
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Remote tool hitting the local test server echo endpoint
    remote_tool = RemoteTool(
        name="echo_tool",
        description="Echo tool for testing",
        url=f"{json_server}/api/echo/" + "{{u1}}",
        http_method="POST",
        data=data,
        query_params={"param": "{{ p1 }}"},
        headers=headers,
    )

    lang_tool = AgentSpecLoader().load_component(remote_tool)

    # Inputs used to render templates in url, headers, params and body
    inputs = {
        "v1": "test1",
        "v2": "test2",
        "p1": "test3",
        "h1": "test4",
        "u1": "u_seg",
    }

    result = lang_tool.func(**inputs)
    expected_msg = "JSON received" if is_json_payload else "JSON not received"

    # Core assertions from the echo server
    assert result["test"] == "test"
    assert result["__parsed_path"] == "/api/echo/u_seg"
    assert result["param"] == "test3"
    assert result["header1"] == "test4"
    assert result["json_body_received"] == expected_msg

    # Body-derived assertions (work for JSON, form-encoded, and parsed text formats)
    assert result["value"] == "test1"
    assert result["listofvalues"] == ["a", "test2", "c"]


def _make_simple_flow_with_tool(tool_node, start_inputs=None, end_outputs=None):
    """Builds Start -> Tool -> End flow with x->x and result->result edges."""

    start_node = StartNode(name="start", inputs=start_inputs or tool_node.inputs)
    end_node = EndNode(name="end", outputs=end_outputs or tool_node.outputs)

    return Flow(
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


def _invoke_until_interrupt(app, payload, config):
    """Invoke and assert first response is an interrupt; return interrupt value."""
    result = app.invoke(payload, config=config)
    assert "__interrupt__" in result and len(result["__interrupt__"]) > 0
    return result["__interrupt__"][0].value


def _approve_command():
    from langgraph.types import Command

    return Command(resume={"decisions": [{"type": "approve"}]})


def _reject_command(reason="no"):
    from langgraph.types import Command

    return Command(resume={"decisions": [{"type": "reject", "reason": reason}]})


def test_server_tool_confirmation_flow_approve_executes() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def double_tool_func(x: int) -> int:
        return x * 2

    server_tool = ServerTool(
        name="double_tool",
        description="Doubles the input number",
        inputs=[IntegerProperty(title="x", description="The number to double")],
        outputs=[Property(title="result", description="The doubled number", json_schema={})],
        # the property is a AnyProperty as the output may not be of type string.
        requires_confirmation=True,
    )
    agentspec_flow = _make_simple_flow_with_tool(
        ToolNode(name="double_tool_node", tool=server_tool)
    )

    langgraph_agent = AgentSpecLoader(
        tool_registry={"double_tool": double_tool_func},
        checkpointer=MemorySaver(),
    ).load_component(agentspec_flow)

    config = RunnableConfig({"configurable": {"thread_id": "t1"}})

    interrupt_payload = _invoke_until_interrupt(
        langgraph_agent, {"inputs": {"x": 5}}, config=config
    )
    assert interrupt_payload["action_requests"][0]["name"] == "double_tool"
    assert interrupt_payload["action_requests"][0]["arguments"] == {"x": 5}

    result = langgraph_agent.invoke(_approve_command(), config=config)
    assert result["outputs"] == {"result": 10}


def test_flow_with_server_tool_confirmation_reject_skips_executes_denial_message() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    called = {"n": 0}

    def double_tool_func(x: int) -> int:
        called["n"] += 1
        return x * 2

    server_tool = ServerTool(
        name="double_tool",
        description="Doubles the input number",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    agentspec_flow = _make_simple_flow_with_tool(
        ToolNode(name="double_tool_node", tool=server_tool)
    )

    langgraph_agent = AgentSpecLoader(
        tool_registry={"double_tool": double_tool_func},
        checkpointer=MemorySaver(),
    ).load_component(agentspec_flow)

    config = RunnableConfig({"configurable": {"thread_id": "t2"}})

    _ = _invoke_until_interrupt(langgraph_agent, {"inputs": {"x": 5}}, config=config)
    result = langgraph_agent.invoke(_reject_command("nope"), config=config)

    assert called["n"] == 0  # Tool should not be executed

    assert "outputs" in result
    assert "denied execution" in str(result["outputs"])


def test_flow_with_client_tool_confirmation_approve_then_interrupts_for_client_execution() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    client_tool = ClientTool(
        name="client_double",
        description="Client doubles the number",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="client_tool_node", tool=client_tool))

    app = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "ct1"}})

    # 1. confirmation interrupt
    confirm_interrupt = _invoke_until_interrupt(app, {"inputs": {"x": 7}}, config=config)
    assert confirm_interrupt["action_requests"][0]["name"] == "client_double"
    assert confirm_interrupt["action_requests"][0]["arguments"] == {"x": 7}

    # 2. approve -> should now interrupt with client_tool_request
    next_result = app.invoke(_approve_command(), config=config)
    assert "__interrupt__" in next_result and len(next_result["__interrupt__"]) > 0
    client_tool_request = next_result["__interrupt__"][0].value
    assert client_tool_request["type"] == "client_tool_request"
    assert client_tool_request["name"] == "client_double"
    assert client_tool_request["inputs"]["kwargs"] == {"x": 7}


def test_flow_with_client_tool_confirmation_reject_returns_denial_and_no_client_request() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    client_tool = ClientTool(
        name="client_double",
        description="Client doubles the number",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="client_tool_node", tool=client_tool))

    app = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "ct2"}})

    _ = _invoke_until_interrupt(app, {"inputs": {"x": 7}}, config=config)

    result = app.invoke(_reject_command("no"), config=config)
    assert "__interrupt__" not in result  # should not proceed to client request
    assert "outputs" in result
    assert "denied execution" in str(result["outputs"])


def test_flow_with_remote_tool_confirmation_approve_executes_http_request() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def mock_request(*args, **kwargs):
        body = kwargs.get("json") or kwargs.get("data") or kwargs.get("content")
        return DummyResponse({"ok": True, "body": body})

    remote_tool = RemoteTool(
        name="remote_echo",
        description="Echo",
        url="https://example.com/echo",
        http_method="POST",
        data={"x": "{{x}}"},
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="remote_node", tool=remote_tool))

    app = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "rt1"}})

    _ = _invoke_until_interrupt(app, {"inputs": {"x": 3}}, config=config)

    with patch("httpx.request", side_effect=mock_request) as patched:
        result = app.invoke(_approve_command(), config=config)
        patched.assert_called_once()
        assert "outputs" in result
        assert result["outputs"] == {"result": {"ok": True, "body": {"x": "3"}}}


def test_flow_with_remote_tool_confirmation_reject_does_not_call_http() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    remote_tool = RemoteTool(
        name="remote_echo",
        description="Echo",
        url="https://example.com/echo",
        http_method="POST",
        data={"x": "{{x}}"},
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="remote_node", tool=remote_tool))

    app = AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "rt2"}})

    _ = _invoke_until_interrupt(app, {"inputs": {"x": 3}}, config=config)

    with patch("httpx.request") as patched:
        result = app.invoke(_reject_command("no"), config=config)
        patched.assert_not_called()
        assert "outputs" in result
        assert "denied execution" in str(result["outputs"])


def _get_fake_model() -> Any:
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from langchain_openai import ChatOpenAI

    class FakeModel(FakeMessagesListChatModel, ChatOpenAI):
        pass

    return FakeModel(
        responses=[
            AIMessage(
                content="Calling tool",
                tool_calls=[{"name": "double_tool", "args": {"x": 5}, "id": "call_1"}],
            ),
            AIMessage(content="Done"),
        ]
    )


def test_server_tool_confirmation_in_agent_approve_executes_tool() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    def double_tool_func(x: int) -> int:
        return x * 2

    agent_spec = Agent(
        name="agent",
        system_prompt="You are a helpful agent.",
        llm_config=OpenAiCompatibleConfig(name="llm", model_id="fake", url="null"),
        # ^ will be patched
        tools=[
            ServerTool(
                name="double_tool",
                description="Doubles input",
                inputs=[IntegerProperty(title="x")],
                outputs=[Property(title="result", json_schema={})],
                requires_confirmation=True,
            )
        ],
    )
    loader = AgentSpecLoader(
        tool_registry={"double_tool": double_tool_func},
        checkpointer=MemorySaver(),
    )
    with patch.object(
        AgentSpecToLangGraphConverter, "_llm_convert_to_langgraph", return_value=_get_fake_model()
    ):
        app = loader.load_component(agent_spec)

    config = RunnableConfig({"configurable": {"thread_id": "ag1"}})

    interrupt_payload = _invoke_until_interrupt(app, {"inputs": {"x": 5}}, config=config)
    assert interrupt_payload["action_requests"][0]["name"] == "double_tool"
    assert interrupt_payload["action_requests"][0]["arguments"] == {"x": 5}

    result = app.invoke(_approve_command(), config=config)

    assert "messages" in result and len(result["messages"]) > 1
    tool_result_message = result["messages"][-2]
    assert "10" in tool_result_message.content


def test_server_tool_confirmation_in_agent_reject_denies_and_does_not_execute() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader
    from pyagentspec.adapters.langgraph._langgraphconverter import AgentSpecToLangGraphConverter

    called = {"n": 0}

    def double_tool_func(x: int) -> int:
        called["n"] += 1
        return x * 2

    agent_spec = Agent(
        name="agent",
        system_prompt="You are a helpful agent.",
        llm_config=OpenAiCompatibleConfig(
            name="llm", model_id="fake", url="null"
        ),  # will be patched
        tools=[
            ServerTool(
                name="double_tool",
                description="Doubles input",
                inputs=[IntegerProperty(title="x")],
                outputs=[Property(title="result", json_schema={})],
                requires_confirmation=True,
            )
        ],
    )

    loader = AgentSpecLoader(
        tool_registry={"double_tool": double_tool_func},
        checkpointer=MemorySaver(),
    )

    with patch.object(
        AgentSpecToLangGraphConverter, "_llm_convert_to_langgraph", return_value=_get_fake_model()
    ):
        app = loader.load_component(agent_spec)

    config = RunnableConfig({"configurable": {"thread_id": "ag2"}})

    _ = _invoke_until_interrupt(app, {"inputs": {"x": 5}}, config=config)
    result = app.invoke(_reject_command("no"), config=config)

    assert called["n"] == 0
    assert "messages" in result and len(result["messages"]) > 1
    tool_result_message = result["messages"][-2]
    assert "denied execution" in tool_result_message.content


def test_requires_confirmation_without_checkpointer_raises_for_server_tool_in_flow() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def double_tool_func(x: int) -> int:
        return x * 2

    server_tool = ServerTool(
        name="double_tool",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="n", tool=server_tool))

    with pytest.raises(ValueError, match="Checkpointer is required"):
        AgentSpecLoader(
            tool_registry={"double_tool": double_tool_func}, checkpointer=None
        ).load_component(flow)


def test_requires_confirmation_without_checkpointer_raises_for_client_tool() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    client_tool = ClientTool(
        name="client_tool",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="n", tool=client_tool))

    with pytest.raises(ValueError, match="Checkpointer is required"):
        AgentSpecLoader(tool_registry={}, checkpointer=None).load_component(flow)


def test_server_tool_missing_from_registry_raises() -> None:
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    server_tool = ServerTool(
        name="missing_tool",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=False,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="n", tool=server_tool))

    with pytest.raises(ValueError, match="does not appear in the tool registry"):
        AgentSpecLoader(tool_registry={}, checkpointer=MemorySaver()).load_component(flow)


def test_invalid_confirmation_resume_payload_raises() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    def double_tool_func(x: int) -> int:
        return x * 2

    server_tool = ServerTool(
        name="double_tool",
        inputs=[IntegerProperty(title="x")],
        outputs=[Property(title="result", json_schema={})],
        requires_confirmation=True,
    )
    flow = _make_simple_flow_with_tool(ToolNode(name="n", tool=server_tool))

    app = AgentSpecLoader(
        tool_registry={"double_tool": double_tool_func},
        checkpointer=MemorySaver(),
    ).load_component(flow)

    config = RunnableConfig({"configurable": {"thread_id": "neg1"}})
    _ = _invoke_until_interrupt(app, {"inputs": {"x": 5}}, config=config)

    bad = Command(resume={"not_decisions": []})
    with pytest.raises(
        ValueError,
        match=(
            "Tool confirmation result for tool double_tool is not valid, "
            "should be a dict with a 'decisions' key"
        ),
    ):
        app.invoke(bad, config=config)
