# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

from uuid import uuid4

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph_agentspec_adapter import AgentSpecLoader

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, MapNode, StartNode, ToolNode
from pyagentspec.property import FloatProperty, ListProperty, Property, UnionProperty
from pyagentspec.tools import ServerTool

from .conftest import (
    IS_JSON_SERVER_RUNNING,
    JSON_SERVER_PORT,
    get_weather,
)


def test_weather_agent_with_server_tool(weather_agent_server_tool_yaml: str) -> None:
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_server_tool_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]},
        config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    tool_call_message = result["messages"][-2]
    assert isinstance(tool_call_message, ToolMessage)


def test_weather_agent_with_server_tool_ollama(weather_ollama_agent_yaml: str) -> None:
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_ollama_agent_yaml
    )
    assert isinstance(agent, CompiledStateGraph)


def test_weather_agent_with_server_tool_with_output_descriptors(
    weather_agent_with_outputs_yaml: str,
) -> None:
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_with_outputs_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]},
        config,
    )
    last_message = result["structured_response"]
    assert isinstance(last_message.temperature_rating, int)
    assert isinstance(last_message.weather, str)


def test_client_tool_with_agent(weather_agent_client_tool_yaml: str) -> None:
    agent = AgentSpecLoader().load_yaml(weather_agent_client_tool_yaml)
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]}
    agent.invoke(
        messages,
        config,
    )
    result = agent.invoke(
        input=Command(resume={"weather": "sunny"}),
        config=config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    assert all(x in last_message.content.lower() for x in ("agadir", "sunny"))


def test_client_tool_with_two_inputs(ancestry_agent_with_client_tool_yaml: str) -> None:
    agent = AgentSpecLoader().load_yaml(ancestry_agent_with_client_tool_yaml)
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "Who's the son of Tim and Dorothy"}]}
    agent.invoke(
        messages,
        config,
    )
    result = agent.invoke(
        input=Command(resume={"son": "himothy"}),
        config=config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    assert "himothy" in last_message.content.lower()


@pytest.mark.skipif(
    not IS_JSON_SERVER_RUNNING, reason="Skipping test because json server is not running"
)
def test_remote_tool_with_agent(json_server, weather_agent_remote_tool_yaml: str) -> None:
    yaml_content = weather_agent_remote_tool_yaml
    agent = AgentSpecLoader().load_yaml(
        yaml_content.replace("[[remote_tools_server]]", f"http://localhost:{JSON_SERVER_PORT}")
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]}
    result = agent.invoke(
        messages,
        config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    assert all(x in last_message.content.lower() for x in ("agadir", "sunny"))


def test_mapnode() -> None:
    def create_mapnode_flow() -> Flow:

        # Define subflow for squaring a number
        x_property = Property(json_schema={"title": "input", "type": "number"})
        x_square_property = Property(json_schema={"title": "input_square", "type": "number"})

        square_tool = ServerTool(
            name="square_tool",
            description="Computes the square of a number",
            inputs=[x_property],
            outputs=[x_square_property],
        )

        # Build inner flow for MapNode
        inner_start_node = StartNode(name="subflow_start", inputs=[x_property])
        inner_end_node = EndNode(name="subflow_end", outputs=[x_square_property])
        square_tool_node = ToolNode(name="square_tool_node", tool=square_tool)

        square_number_flow = Flow(
            name="Square number flow",
            start_node=inner_start_node,
            nodes=[inner_start_node, square_tool_node, inner_end_node],
            control_flow_connections=[
                ControlFlowEdge(
                    name="start_to_tool", from_node=inner_start_node, to_node=square_tool_node
                ),
                ControlFlowEdge(
                    name="tool_to_end", from_node=square_tool_node, to_node=inner_end_node
                ),
            ],
            data_flow_connections=[
                DataFlowEdge(
                    name="input_edge",
                    source_node=inner_start_node,
                    source_output="input",
                    destination_node=square_tool_node,
                    destination_input="input",
                ),
                DataFlowEdge(
                    name="input_square_edge",
                    source_node=square_tool_node,
                    source_output="input_square",
                    destination_node=inner_end_node,
                    destination_input="input_square",
                ),
            ],
        )

        # 1. Define the 'iterated_input' property as UnionProperty for MapNode input
        single_x_property = Property(json_schema={"title": "input", "type": "number"})
        list_x_property = Property(
            json_schema={"title": "input", "type": "array", "items": {"type": "number"}}
        )

        iterated_x_property = UnionProperty(
            any_of=[single_x_property, list_x_property], title="iterated_input"
        )

        # 2. Output property for MapNode
        collected_x_square_property = Property(
            json_schema={
                "title": "collected_input_square",
                "type": "array",
                "items": {"type": "number"},
            }
        )

        # Create MapNode
        square_numbers_map_node = MapNode(
            name="square_number_map_node",
            subflow=square_number_flow,
            inputs=[iterated_x_property],
            outputs=[collected_x_square_property],
        )

        list_x_property = Property(
            json_schema={"title": "input_list", "type": "array", "items": {"type": "number"}}
        )
        collected_x_square_property = ListProperty(
            title="collected_input_square",
            item_type=FloatProperty(),
        )

        # Outer start/end nodes
        outer_start_node = StartNode(name="outer_start", inputs=[list_x_property])
        outer_end_node = EndNode(name="outer_end", outputs=[collected_x_square_property])

        # Assemble the full flow
        final_assistant_flow = Flow(
            name="flow to square all elements of a list",
            start_node=outer_start_node,
            nodes=[
                outer_start_node,
                square_numbers_map_node,
                outer_end_node,
            ],
            control_flow_connections=[
                ControlFlowEdge(
                    name="start_to_square_numbers",
                    from_node=outer_start_node,
                    to_node=square_numbers_map_node,
                ),
                ControlFlowEdge(
                    name="map_to_end",
                    from_node=square_numbers_map_node,
                    to_node=outer_end_node,
                ),
            ],
            data_flow_connections=[
                DataFlowEdge(
                    name="list_of_input_edge",
                    source_node=outer_start_node,
                    source_output="input_list",
                    destination_node=square_numbers_map_node,
                    destination_input="iterated_input",
                ),
                DataFlowEdge(
                    name="input_square_list_edge",
                    source_node=square_numbers_map_node,
                    source_output="collected_input_square",
                    destination_node=outer_end_node,
                    destination_input="collected_input_square",
                ),
            ],
        )
        return final_assistant_flow

    def square_tool(input: int) -> int:
        return int(input) * int(input)

    mapnode_flow = create_mapnode_flow()
    config = RunnableConfig({"configurable": {"thread_id": str(uuid4())}})
    agent = AgentSpecLoader(
        tool_registry={"square_tool": square_tool}, config=config
    ).load_component(mapnode_flow)
    result = agent.invoke({"inputs": {"input_list": [1, 2, 3, 4]}}, config)
    outputs = result["outputs"]
    assert "collected_input_square" in outputs
    assert outputs["collected_input_square"] == 30
