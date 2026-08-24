# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.property import Property
from pyagentspec.tools import ServerTool


@pytest.mark.usefixtures("mute_crewai_console_prints")
def test_toolnode_can_be_imported_and_executed() -> None:
    from crewai import Flow as CrewAIFlow

    from pyagentspec.adapters.crewai import AgentSpecLoader

    x_property = Property(json_schema={"title": "input", "type": "number"})
    x_square_property = Property(json_schema={"title": "input_square", "type": "number"})

    square_tool = ServerTool(
        name="square_tool",
        description="Computes the square of a number",
        inputs=[x_property],
        outputs=[x_square_property],
    )

    start_node = StartNode(name="subflow_start", inputs=[x_property])
    end_node = EndNode(name="subflow_end", outputs=[x_square_property])
    square_tool_node = ToolNode(name="square_tool_node", tool=square_tool)

    flow = Flow(
        name="Square number flow",
        start_node=start_node,
        nodes=[start_node, square_tool_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_tool", from_node=start_node, to_node=square_tool_node),
            ControlFlowEdge(name="tool_to_end", from_node=square_tool_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output="input",
                destination_node=square_tool_node,
                destination_input="input",
            ),
            DataFlowEdge(
                name="input_square_edge",
                source_node=square_tool_node,
                source_output="input_square",
                destination_node=end_node,
                destination_input="input_square",
            ),
        ],
    )

    def square_tool_callable(input: float) -> float:
        return input * input

    tool_registry = {"square_tool": square_tool_callable}
    flow_instance = AgentSpecLoader(tool_registry).load_component(flow)

    assert isinstance(flow_instance, CrewAIFlow)

    result = flow_instance.kickoff({"input": 4})

    assert isinstance(result, dict)
    assert "input_square" in result
    assert result["input_square"] == 16.0
