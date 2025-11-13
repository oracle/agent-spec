# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import BranchingNode, EndNode, StartNode
from pyagentspec.property import StringProperty

from langgraph_agentspec_adapter import AgentSpecLoader


def test_branchingnode_can_be_imported_and_executed() -> None:

    custom_input_property = StringProperty(title="custom_input")
    custom_output_property_a = StringProperty(title="output_a", default="no_value")
    custom_output_property_b = StringProperty(title="output_b", default="no_value")
    branching_node = BranchingNode(
        name="branching",
        mapping={
            "a": "branch_a",
            "b": "branch_b",
        },
        inputs=[custom_input_property],
    )
    start_node = StartNode(name="start", inputs=[custom_input_property])
    end_node_a = EndNode(name="end_a", outputs=[custom_output_property_a])
    end_node_b = EndNode(name="end_b", outputs=[custom_output_property_b])
    end_node_default = EndNode(name="end_default")

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, branching_node, end_node_a, end_node_b, end_node_default],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=branching_node),
            ControlFlowEdge(
                name="node_to_end_a",
                from_node=branching_node,
                to_node=end_node_a,
                from_branch="branch_a",
            ),
            ControlFlowEdge(
                name="node_to_end_b",
                from_node=branching_node,
                to_node=end_node_b,
                from_branch="branch_b",
            ),
            ControlFlowEdge(
                name="node_to_end_def",
                from_node=branching_node,
                to_node=end_node_default,
                from_branch="default",
            ),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=custom_input_property.title,
                destination_node=branching_node,
                destination_input=custom_input_property.title,
            ),
            DataFlowEdge(
                name="output_edge",
                source_node=start_node,
                source_output=custom_input_property.title,
                destination_node=end_node_b,
                destination_input=custom_output_property_b.title,
            ),
            DataFlowEdge(
                name="output_edge",
                source_node=start_node,
                source_output=custom_input_property.title,
                destination_node=end_node_a,
                destination_input=custom_output_property_a.title,
            ),
        ],
        outputs=[custom_output_property_a, custom_output_property_b],
    )

    agent = AgentSpecLoader().load_component(flow)

    result = agent.invoke({"inputs": {custom_input_property.title: "a"}})
    assert "outputs" in result
    assert "messages" in result
    outputs = result["outputs"]
    assert custom_output_property_a.title in outputs
    assert custom_output_property_b.title in outputs
    assert outputs[custom_output_property_a.title] == "a"
    assert outputs[custom_output_property_b.title] == "no_value"

    result = agent.invoke({"inputs": {custom_input_property.title: "b"}})
    assert "outputs" in result
    assert "messages" in result
    outputs = result["outputs"]
    assert custom_output_property_a.title in outputs
    assert custom_output_property_b.title in outputs
    assert outputs[custom_output_property_a.title] == "no_value"
    assert outputs[custom_output_property_b.title] == "b"

    result = agent.invoke({"inputs": {custom_input_property.title: "no_match"}})
    assert "outputs" in result
    assert "messages" in result
    outputs = result["outputs"]
    assert custom_output_property_a.title in outputs
    assert custom_output_property_b.title in outputs
    assert outputs[custom_output_property_a.title] == "no_value"
    assert outputs[custom_output_property_b.title] == "no_value"
