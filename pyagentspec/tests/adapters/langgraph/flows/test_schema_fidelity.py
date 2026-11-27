# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""Flows executed with the LangGraph adapter honour the JSON schemas declared on their nodes.

Covers oracle/agent-spec#220, #231, #233, #239 and #241, plus ToolNodes without outputs.
"""

from typing import Any, Callable, Dict, List

import pytest

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.property import IntegerProperty, Property, StringProperty
from pyagentspec.tools import ServerTool

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "title": "payload",
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "profile": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["score", "active", "tags"],
        },
    },
    "required": ["name", "profile"],
    "additionalProperties": False,
}

# Same shape as PAYLOAD_SCHEMA, but nothing is required
PERMISSIVE_PAYLOAD_SCHEMA: Dict[str, Any] = {
    "title": "payload",
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "profile": {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "additionalProperties": False,
}

STATE_SCHEMA: Dict[str, Any] = {
    "title": "state",
    "type": "object",
    "properties": {
        "counter": {"type": "integer"},
        "trace": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["counter", "trace"],
    "additionalProperties": True,
}

REQUEST_SCHEMA: Dict[str, Any] = {
    "title": "request",
    "type": "object",
    "properties": {
        "customer_id": {"type": "string"},
        "profile": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        },
        "tags": {"type": "array", "items": {"type": "string"}},
        "priority": {"type": "string", "default": "normal"},
        "notifications": {"type": "boolean", "default": True},
    },
    "required": ["customer_id", "profile", "tags"],
    "additionalProperties": False,
}


def _chain_of_tool_nodes_flow(
    flow_input: Property,
    flow_output: Property,
    tools: List[ServerTool],
) -> Flow:
    """Start -> ToolNode(tools[0]) -> ... -> ToolNode(tools[-1]) -> End, passing one value along."""
    start = StartNode(name="start", inputs=[flow_input])
    end = EndNode(name="end", outputs=[flow_output])
    tool_nodes = [ToolNode(name=f"{tool.name}_node", tool=tool) for tool in tools]
    nodes = [start, *tool_nodes, end]

    control_flow_connections = [
        ControlFlowEdge(name=f"{source.name}_to_{target.name}", from_node=source, to_node=target)
        for source, target in zip(nodes[:-1], nodes[1:])
    ]
    data_flow_connections = [
        DataFlowEdge(
            name=f"{source.name}_value_to_{target.name}",
            source_node=source,
            source_output=(source.outputs or [])[0].title if source.outputs else flow_input.title,
            destination_node=target,
            destination_input=(
                (target.inputs or [])[0].title if target.inputs else flow_output.title
            ),
        )
        for source, target in zip(nodes[:-1], nodes[1:])
    ]
    return Flow(
        name="schema_fidelity_flow",
        start_node=start,
        nodes=nodes,
        control_flow_connections=control_flow_connections,
        data_flow_connections=data_flow_connections,
    )


def _start_to_end_flow(flow_input: Property, flow_output: Property) -> Flow:
    start = StartNode(name="start", inputs=[flow_input])
    end = EndNode(name="end", outputs=[flow_output])
    return Flow(
        name="start_to_end_flow",
        start_node=start,
        nodes=[start, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start, to_node=end)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="value",
                source_node=start,
                source_output=flow_input.title,
                destination_node=end,
                destination_input=flow_output.title,
            )
        ],
    )


def _run(flow: Flow, inputs: Dict[str, Any], tool_registry: Dict[str, Callable[..., Any]]) -> Any:
    graph = AgentSpecLoader(tool_registry=tool_registry).load_component(flow)
    return graph.invoke({"inputs": inputs})["outputs"]


@pytest.mark.parametrize("tool_return_value", [None, "done", 3, [1, 2]])
def test_toolnode_without_outputs_accepts_any_tool_return_value(tool_return_value: Any) -> None:
    # A ToolNode with no declared output used to fail with "Unsupported multi-output mapping"
    notify = ServerTool(
        name="notify",
        description="Sends a notification and returns nothing useful",
        inputs=[StringProperty(title="message")],
        outputs=[],
    )
    start = StartNode(name="start", inputs=[StringProperty(title="message")])
    notify_node = ToolNode(name="notify_node", tool=notify)
    end = EndNode(name="end", outputs=[])
    flow = Flow(
        name="notify_flow",
        start_node=start,
        nodes=[start, notify_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_notify", from_node=start, to_node=notify_node),
            ControlFlowEdge(name="notify_to_end", from_node=notify_node, to_node=end),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="message",
                source_node=start,
                source_output="message",
                destination_node=notify_node,
                destination_input="message",
            )
        ],
    )
    received: List[str] = []

    def notify_tool(message: str) -> Any:
        received.append(message)
        return tool_return_value

    assert _run(flow, {"message": "hello"}, {"notify": notify_tool}) == {}
    assert received == ["hello"]


def test_server_tool_receives_object_inputs_as_plain_dictionaries() -> None:
    # Tools are written against JSON values, as in the other runtimes
    request = Property(json_schema=REQUEST_SCHEMA)
    echo = ServerTool(name="echo", description="Echoes", inputs=[request], outputs=[request])
    flow = _chain_of_tool_nodes_flow(request, request, [echo])
    received: List[Any] = []

    def echo_tool(request: Any) -> Any:
        received.append(request)
        return request

    _run(
        flow,
        {"request": {"customer_id": "C-1", "profile": {"name": "Ada", "age": 36}, "tags": []}},
        {"echo": echo_tool},
    )
    assert type(received[0]) is dict
    assert type(received[0]["profile"]) is dict


def test_additional_object_fields_are_preserved_across_tool_nodes() -> None:
    # oracle/agent-spec#239
    state = Property(json_schema=STATE_SCHEMA)
    tools = [
        ServerTool(name=f"step{i}", description=f"Step {i}", inputs=[state], outputs=[state])
        for i in (1, 2, 3)
    ]
    flow = _chain_of_tool_nodes_flow(state, state, tools)

    def make_step(step_name: str, increment: int, label: str) -> Callable[..., Any]:
        def step(state: Dict[str, Any]) -> Dict[str, Any]:
            new_state = dict(state)
            new_state["counter"] = state["counter"] + increment
            new_state["trace"] = [*state["trace"], step_name]
            new_state[step_name] = label
            return new_state

        return step

    outputs = _run(
        flow,
        {"state": {"counter": 0, "trace": []}},
        {
            "step1": make_step("step1", 1, "initialized"),
            "step2": make_step("step2", 10, "enriched"),
            "step3": make_step("step3", 100, "finalized"),
        },
    )
    assert outputs == {
        "state": {
            "counter": 111,
            "trace": ["step1", "step2", "step3"],
            "step1": "initialized",
            "step2": "enriched",
            "step3": "finalized",
        }
    }


def test_declared_defaults_are_applied_to_omitted_nested_fields() -> None:
    # oracle/agent-spec#241
    request = Property(json_schema=REQUEST_SCHEMA)
    normalize = ServerTool(
        name="normalize", description="Normalizes", inputs=[request], outputs=[request]
    )
    flow = _chain_of_tool_nodes_flow(request, request, [normalize])
    received: List[Any] = []

    def normalize_tool(request: Dict[str, Any]) -> Dict[str, Any]:
        received.append(request)
        return request

    expected = {
        "customer_id": "C-1042",
        "profile": {"name": "Ada", "age": 36},
        "tags": ["priority", "verified"],
        "priority": "normal",
        "notifications": True,
    }
    outputs = _run(
        flow,
        {
            "request": {
                "customer_id": "C-1042",
                "profile": {"name": "Ada", "age": 36},
                "tags": ["priority", "verified"],
            }
        },
        {"normalize": normalize_tool},
    )
    assert received == [expected]
    assert outputs == {"request": expected}


def test_bare_object_items_keep_their_keys() -> None:
    # oracle/agent-spec#220
    components = Property(
        json_schema={"title": "components", "type": "array", "items": {"type": "object"}}
    )
    render = ServerTool(
        name="render", description="Renders", inputs=[components], outputs=[components]
    )
    flow = _chain_of_tool_nodes_flow(components, components, [render])
    value = [{"id": "root", "component": "Card", "children": [{"id": "title"}]}]
    outputs = _run(flow, {"components": value}, {"render": lambda components: components})
    assert outputs == {"components": value}


def test_start_node_rejects_input_not_conforming_to_nested_schema() -> None:
    # oracle/agent-spec#231
    payload = Property(json_schema=PAYLOAD_SCHEMA)
    flow = _start_to_end_flow(payload, payload)
    with pytest.raises(
        ValueError, match=r"(?s)`payload` of node `start`.*'active' is a required"
    ) as e:
        _run(
            flow,
            {"payload": {"name": "Ada", "profile": {"score": 0.98, "tags": ["verified"]}}},
            {},
        )
    assert "$.profile" in str(e.value)


def test_start_node_reports_all_schema_violations() -> None:
    payload = Property(json_schema=PAYLOAD_SCHEMA)
    flow = _start_to_end_flow(payload, payload)
    with pytest.raises(ValueError) as e:
        _run(
            flow,
            {"payload": {"name": 123, "profile": {"score": "high", "tags": []}, "extra": 1}},
            {},
        )
    message = str(e.value)
    assert "Additional properties are not allowed ('extra' was unexpected)" in message
    assert "$.name: 123 is not of type 'string'" in message
    assert "$.profile: 'active' is a required property" in message
    assert "$.profile.score: 'high' is not of type 'number'" in message


def test_end_node_rejects_value_not_conforming_to_its_schema() -> None:
    # oracle/agent-spec#233: a permissive StartNode lets the value in, the strict EndNode
    # must still reject it
    flow = _start_to_end_flow(
        Property(json_schema=PERMISSIVE_PAYLOAD_SCHEMA), Property(json_schema=PAYLOAD_SCHEMA)
    )
    with pytest.raises(ValueError, match=r"(?s)`payload` of node `end`.*'active' is a required"):
        _run(
            flow,
            {"payload": {"name": "Ada", "profile": {"score": 0.98, "tags": ["verified"]}}},
            {},
        )


def test_end_node_accepts_conforming_value() -> None:
    flow = _start_to_end_flow(
        Property(json_schema=PERMISSIVE_PAYLOAD_SCHEMA), Property(json_schema=PAYLOAD_SCHEMA)
    )
    value = {"name": "Ada", "profile": {"score": 0.98, "active": True, "tags": ["verified"]}}
    assert _run(flow, {"payload": value}, {}) == {"payload": value}


def test_integer_input_given_non_numeric_string_raises_schema_error() -> None:
    number = IntegerProperty(title="n")
    flow = _start_to_end_flow(number, number)
    with pytest.raises(
        ValueError, match=r"(?s)`n` of node `start`.*'abc' is not of type 'integer'"
    ):
        _run(flow, {"n": "abc"}, {})
    with pytest.raises(ValueError, match=r"\[1, 2\] is not of type 'integer'"):
        _run(flow, {"n": [1, 2]}, {})
    # Numeric strings are still accepted and cast
    assert _run(flow, {"n": " 7 "}, {}) == {"n": 7}


def test_untyped_property_accepts_any_value() -> None:
    anything = Property(json_schema={"title": "anything"})
    flow = _start_to_end_flow(anything, anything)
    value = {"nested": [1, "two", None, {"three": 3.0}]}
    assert _run(flow, {"anything": value}, {}) == {"anything": value}
