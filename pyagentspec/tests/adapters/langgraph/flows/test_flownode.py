# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, FlowNode, InputMessageNode, StartNode
from pyagentspec.property import StringProperty


@pytest.fixture()
def flow_node_flow() -> Flow:
    custom_property = StringProperty(title="custom_prop")
    start_node = StartNode(name="start", inputs=[custom_property])
    end_node = EndNode(name="end", outputs=[custom_property])

    subflow = Flow(
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
        subflow=subflow,
    )
    start_node = StartNode(name="start", inputs=[custom_property])
    end_node = EndNode(name="end", outputs=[custom_property])

    return Flow(
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


def test_flownode_can_be_imported_and_executed(flow_node_flow: Flow) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(flow_node_flow)
    result = agent.invoke({"inputs": {"custom_prop": "custom"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "custom_prop" in outputs
    assert outputs["custom_prop"] == "custom"


def _flow_with_nested_input_node(*, propagate_pending_input: bool = True) -> Flow:
    custom_property = StringProperty(title="custom_input")
    input_message_node = InputMessageNode(
        name="input_message",
        outputs=[custom_property],
    )
    subflow_start_node = StartNode(name="subflow_start")
    subflow_end_node = EndNode(name="subflow_end", outputs=[custom_property])
    subflow = Flow(
        name="subflow",
        start_node=subflow_start_node,
        nodes=[subflow_start_node, input_message_node, subflow_end_node],
        control_flow_connections=[
            ControlFlowEdge(
                name="subflow_start_to_input",
                from_node=subflow_start_node,
                to_node=input_message_node,
            ),
            ControlFlowEdge(
                name="input_to_subflow_end",
                from_node=input_message_node,
                to_node=subflow_end_node,
            ),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_to_subflow_end",
                source_node=input_message_node,
                source_output=custom_property.title,
                destination_node=subflow_end_node,
                destination_input=custom_property.title,
            ),
        ],
        outputs=[custom_property],
    )

    flow_node = FlowNode(
        name="flow_node",
        subflow=subflow,
        propagate_pending_input=propagate_pending_input,
    )
    start_node = StartNode(name="start")
    end_node = EndNode(name="end", outputs=[custom_property])
    return Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, flow_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_flow_node", from_node=start_node, to_node=flow_node),
            ControlFlowEdge(name="flow_node_to_end", from_node=flow_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="flow_node_to_end",
                source_node=flow_node,
                source_output=custom_property.title,
                destination_node=end_node,
                destination_input=custom_property.title,
            ),
        ],
        outputs=[custom_property],
    )


def test_flownode_propagates_nested_input_required_state() -> None:
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    flow = _flow_with_nested_input_node()
    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(flow)

    config = RunnableConfig({"configurable": {"thread_id": "nested-flow-node-input"}})
    result = agent.invoke({}, config=config)
    assert "__interrupt__" in result
    assert result["__interrupt__"][0].value == ""

    result = agent.invoke(Command(resume="nested value"), config=config)

    assert "outputs" in result
    assert result["outputs"]["custom_input"] == "nested value"
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == "nested value"


def test_flownode_disabled_pending_input_propagation_raises() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    flow = _flow_with_nested_input_node(propagate_pending_input=False)
    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(flow)

    config = RunnableConfig({"configurable": {"thread_id": "nested-flow-node-input-disabled"}})
    with pytest.raises(RuntimeError, match="propagate_pending_input is disabled"):
        agent.invoke({}, config=config)


@pytest.mark.anyio
async def test_flownode_can_be_executed_async(flow_node_flow: Flow) -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_component(flow_node_flow)
    result = await agent.ainvoke({"inputs": {"custom_prop": "custom"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "custom_prop" in outputs
    assert outputs["custom_prop"] == "custom"
