# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from langchain_core.messages import AIMessage
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, OutputMessageNode, StartNode
from pyagentspec.property import StringProperty

from langgraph_agentspec_adapter import AgentSpecLoader


def test_outputmessagenode_can_be_imported_and_executed() -> None:

    custom_input_property = StringProperty(title="custom_input")
    output_message_node = OutputMessageNode(
        name="output_message",
        message="Hey {{custom_input}}",
        inputs=[custom_input_property],
    )
    start_node = StartNode(name="start", inputs=[custom_input_property])
    end_node = EndNode(name="end")

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, output_message_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(
                name="start_to_node", from_node=start_node, to_node=output_message_node
            ),
            ControlFlowEdge(name="node_to_end", from_node=output_message_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=custom_input_property.title,
                destination_node=output_message_node,
                destination_input=custom_input_property.title,
            ),
        ],
        inputs=[custom_input_property],
    )

    agent = AgentSpecLoader().load_component(flow)
    result = agent.invoke({"inputs": {custom_input_property.title: "custom"}})

    assert "outputs" in result
    assert "messages" in result

    messages = result["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], AIMessage)
    assert messages[0].content == "Hey custom"
