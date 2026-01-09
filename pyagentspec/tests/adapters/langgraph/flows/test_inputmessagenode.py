# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import sys

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, InputMessageNode, StartNode
from pyagentspec.property import StringProperty


@pytest.fixture()
def input_message_flow() -> Flow:
    custom_input_property = StringProperty(title="custom_input")
    input_message_node = InputMessageNode(
        name="input_message",
        outputs=[custom_input_property],
    )
    start_node = StartNode(name="start")
    end_node = EndNode(name="end", outputs=[custom_input_property])

    return Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, input_message_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=input_message_node),
            ControlFlowEdge(name="node_to_end", from_node=input_message_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=input_message_node,
                source_output=custom_input_property.title,
                destination_node=end_node,
                destination_input=custom_input_property.title,
            ),
        ],
        outputs=[custom_input_property],
    )


def test_inputmessagenode_can_be_imported_and_executed(input_message_flow: Flow) -> None:
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(input_message_flow)

    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke({}, config=config)
    assert "__interrupt__" in result

    result = agent.invoke(Command(resume="3"), config=config)

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "custom_input" in outputs
    assert outputs["custom_input"] == "3"

    messages = result["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "3"


@pytest.mark.anyio
async def test_inputmessagenode_can_be_executed_async(input_message_flow: Flow) -> None:
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(input_message_flow)

    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    if sys.version_info < (3, 11):
        with pytest.raises(RuntimeError, match="Called get_config outside of a runnable context"):
            await agent.ainvoke({}, config=config)
        return
    result = await agent.ainvoke({}, config=config)
    assert "__interrupt__" in result

    result = await agent.ainvoke(Command(resume="3"), config=config)

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert "custom_input" in outputs
    assert outputs["custom_input"] == "3"

    messages = result["messages"]
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "3"
