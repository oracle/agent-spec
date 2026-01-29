# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, OutputMessageNode, StartNode
from pyagentspec.property import StringProperty


@pytest.fixture()
def output_message_flow() -> Flow:
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
    # attach helper for tests to read property title without re-building
    flow.__dict__["_custom_input_title"] = custom_input_property.title
    return flow


def test_outputmessagenode_can_be_imported_and_executed(output_message_flow: Flow) -> None:
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(output_message_flow)
    result = agent.invoke(
        {"inputs": {output_message_flow.__dict__["_custom_input_title"]: "custom"}}
    )

    assert "outputs" in result
    assert "messages" in result

    messages = result["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], AIMessage)
    assert messages[0].content == "Hey custom"


@pytest.mark.anyio
async def test_outputmessagenode_can_be_executed_async(output_message_flow: Flow) -> None:
    from langchain_core.messages import AIMessage

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(output_message_flow)
    result = await agent.ainvoke(
        {"inputs": {output_message_flow.__dict__["_custom_input_title"]: "custom"}}
    )

    assert "messages" in result
    messages = result["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], AIMessage)
    assert messages[0].content == "Hey custom"
