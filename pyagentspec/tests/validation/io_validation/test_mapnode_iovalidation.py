# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.mapnode import MapNode, ReductionMethod
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.flows.nodes.toolnode import ToolNode
from pyagentspec.property import (
    FloatProperty,
    Property,
)
from pyagentspec.tools.servertool import ServerTool


@pytest.fixture
def server_tool() -> ServerTool:
    number_property = FloatProperty(title="number")
    server_tool = ServerTool(
        name="double_number",
        description="Returns the number doubled",
        inputs=[number_property],
        outputs=[number_property],
    )
    return server_tool


@pytest.fixture
def double_number_flow(server_tool: ServerTool) -> Flow:
    number_property = FloatProperty(title="number")
    start_node = StartNode(name="start_node", inputs=[number_property])
    tool_node = ToolNode(name="node", tool=server_tool)
    end_node = EndNode(name="end_node", outputs=[number_property])
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, tool_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=tool_node),
            ControlFlowEdge(name="edge", from_node=tool_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="edge",
                source_node=start_node,
                source_output="number",
                destination_node=tool_node,
                destination_input="number",
            ),
            DataFlowEdge(
                name="edge",
                source_node=tool_node,
                source_output="number",
                destination_node=end_node,
                destination_input="number",
            ),
        ],
    )
    return flow


def test_map_node_infers_inputs_as_lists_of_inner_flow_inputs(double_number_flow: Flow) -> None:
    map_node = MapNode(name="node", subflow=double_number_flow)
    assert map_node.inputs == [
        Property(
            json_schema={
                "title": "iterated_number",
                "anyOf": [
                    {"type": "number", "title": "number"},
                    {"type": "array", "items": {"type": "number", "title": "number"}},
                ],
            }
        )
    ]
    assert map_node.outputs == [
        Property(
            json_schema={
                "title": "collected_number",
                "type": "array",
                "items": {"title": "number", "type": "number"},
            },
        )
    ]


def test_map_node_infers_output_aligns_with_reduction_method(double_number_flow: Flow) -> None:
    map_node = MapNode(
        name="node", subflow=double_number_flow, reducers={"number": ReductionMethod.MIN}
    )
    assert map_node.outputs == [
        Property(
            json_schema={
                "title": "collected_number",
                "type": "number",
            },
        )
    ]
