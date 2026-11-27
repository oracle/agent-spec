# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
"""Tools converted to LangGraph receive their object arguments as plain JSON values.

LangChain validates tool calls with the pydantic models generated from the Agent Spec input
schemas and would otherwise hand the nested model instances to the tool callable.
"""

from typing import Any, Dict, List

import pytest

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.property import Property, StringProperty
from pyagentspec.tools import ClientTool, ServerTool

LOCATION_SCHEMA: Dict[str, Any] = {
    "title": "location",
    "type": "object",
    "properties": {
        "city": {"type": "string"},
        "coordinates": {
            "type": "object",
            "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}},
            "required": ["lat", "lon"],
        },
        "units": {"type": "string", "default": "metric"},
    },
    "required": ["city", "coordinates"],
}

LOCATION_CALL = {"location": {"city": "Zurich", "coordinates": {"lat": 47.37, "lon": 8.54}}}
EXPECTED_LOCATION = {
    "city": "Zurich",
    "coordinates": {"lat": 47.37, "lon": 8.54},
    "units": "metric",
}


def _forecast_tool() -> ServerTool:
    return ServerTool(
        name="forecast",
        description="Forecasts the weather at a location",
        inputs=[Property(json_schema=LOCATION_SCHEMA)],
        outputs=[StringProperty(title="forecast")],
    )


def test_sync_server_tool_receives_plain_dictionaries() -> None:
    received: List[Any] = []

    def forecast(location: Dict[str, Any]) -> str:
        received.append(location)
        return f"sunny in {location['city']}"

    langgraph_tool = AgentSpecLoader(tool_registry={"forecast": forecast}).load_component(
        _forecast_tool()
    )
    assert langgraph_tool.invoke(LOCATION_CALL) == "sunny in Zurich"
    assert received == [EXPECTED_LOCATION]
    assert type(received[0]) is dict
    assert type(received[0]["coordinates"]) is dict


@pytest.mark.anyio
async def test_async_server_tool_receives_plain_dictionaries() -> None:
    received: List[Any] = []

    async def forecast(location: Dict[str, Any]) -> str:
        received.append(location)
        return f"sunny in {location['city']}"

    langgraph_tool = AgentSpecLoader(tool_registry={"forecast": forecast}).load_component(
        _forecast_tool()
    )
    assert await langgraph_tool.ainvoke(LOCATION_CALL) == "sunny in Zurich"
    assert received == [EXPECTED_LOCATION]
    assert type(received[0]) is dict


def test_client_tool_interrupt_payload_contains_plain_dictionaries() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    location = Property(json_schema=LOCATION_SCHEMA)
    forecast_output = StringProperty(title="forecast")
    client_tool = ClientTool(
        name="forecast",
        description="Forecasts the weather at a location, on the client",
        inputs=[location],
        outputs=[forecast_output],
    )
    start = StartNode(name="start", inputs=[location])
    tool_node = ToolNode(name="forecast_node", tool=client_tool)
    end = EndNode(name="end", outputs=[forecast_output])
    flow = Flow(
        name="forecast_flow",
        start_node=start,
        nodes=[start, tool_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_tool", from_node=start, to_node=tool_node),
            ControlFlowEdge(name="tool_to_end", from_node=tool_node, to_node=end),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="location",
                source_node=start,
                source_output="location",
                destination_node=tool_node,
                destination_input="location",
            ),
            DataFlowEdge(
                name="forecast",
                source_node=tool_node,
                source_output="forecast",
                destination_node=end,
                destination_input="forecast",
            ),
        ],
    )
    graph = AgentSpecLoader(checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "forecast"}})
    result = graph.invoke({"inputs": LOCATION_CALL}, config=config)

    tool_request = result["__interrupt__"][0].value
    assert tool_request["name"] == "forecast"
    assert tool_request["inputs"]["kwargs"] == {"location": EXPECTED_LOCATION}
    assert type(tool_request["inputs"]["kwargs"]["location"]) is dict
