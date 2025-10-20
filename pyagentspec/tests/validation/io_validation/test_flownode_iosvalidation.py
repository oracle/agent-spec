# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.flownode import FlowNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.property import Property


@pytest.fixture
def flow() -> Flow:
    property_1 = Property(json_schema={"title": "property_1", "type": "string"})
    property_2 = Property(json_schema={"title": "property_2", "type": "string"})
    property_3 = Property(json_schema={"title": "property_3", "type": "string"})
    start_node = StartNode(name="start_node", inputs=[property_1, property_2])
    end_node = EndNode(name="end_node", outputs=[property_2, property_3])
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="start_to_end",
                source_node=start_node,
                source_output="property_1",
                destination_node=end_node,
                destination_input="property_2",
            ),
            DataFlowEdge(
                name="start_to_end",
                source_node=start_node,
                source_output="property_2",
                destination_node=end_node,
                destination_input="property_3",
            ),
        ],
    )
    return flow


def test_flow_node_has_ios_matching_start_and_end_steps(flow: Flow) -> None:
    property_1 = Property(json_schema={"title": "property_1", "type": "string"})
    property_2 = Property(json_schema={"title": "property_2", "type": "string"})
    property_3 = Property(json_schema={"title": "property_3", "type": "string"})
    flow_node = FlowNode(name="flow_node", subflow=flow)
    assert flow_node.inputs == [property_1, property_2]
    assert flow_node.outputs == [property_2, property_3]


def test_flow_node_raises_if_inputs_have_incorrect_names(flow: Flow) -> None:
    property_1 = Property(json_schema={"title": "NOT_property_1", "type": "string"})
    property_2 = Property(json_schema={"title": "property_2", "type": "string"})
    with pytest.raises(ValueError, match="NOT_property_1"):
        FlowNode(name="flow_node", subflow=flow, inputs=[property_1, property_2])


def test_flow_node_raises_if_outputs_have_incorrect_names(flow: Flow) -> None:
    property_2 = Property(json_schema={"title": "property_2", "type": "string"})
    property_1 = Property(json_schema={"title": "NOT_property_3", "type": "string"})
    with pytest.raises(ValueError, match="NOT_property_3"):
        FlowNode(name="flow_node", subflow=flow, outputs=[property_1, property_2])
