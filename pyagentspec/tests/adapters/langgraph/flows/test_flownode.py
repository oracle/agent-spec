# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, FlowNode, StartNode
from pyagentspec.property import StringProperty


def test_flownode_can_be_imported_and_executed() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    custom_property = StringProperty(title="custom_prop")
    start_node = StartNode(name="start", inputs=[custom_property])
    end_node = EndNode(name="end", outputs=[custom_property])

    flow = Flow(
        name="subflow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=custom_property.title,
                destination_node=end_node,
                destination_input=custom_property.title,
            ),
        ],
        inputs=[custom_property],
        outputs=[custom_property],
    )

    flow_node = FlowNode(
        name="flow_node",
        subflow=flow,
    )
    start_node = StartNode(name="start", inputs=[custom_property])
    end_node = EndNode(name="end", outputs=[custom_property])

    flow = Flow(
        name="subflow",
        start_node=start_node,
        nodes=[start_node, flow_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=flow_node),
            ControlFlowEdge(name="node_to_end", from_node=flow_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=custom_property.title,
                destination_node=flow_node,
                destination_input=custom_property.title,
            ),
            DataFlowEdge(
                name="input_edge",
                source_node=flow_node,
                source_output=custom_property.title,
                destination_node=end_node,
                destination_input=custom_property.title,
            ),
        ],
        inputs=[custom_property],
        outputs=[custom_property],
    )

    agent = AgentSpecLoader().load_component(flow)
    result = agent.invoke({"inputs": {custom_property.title: "custom"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert custom_property.title in outputs
    assert outputs[custom_property.title] == "custom"
