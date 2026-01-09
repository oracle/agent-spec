# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import sys

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.property import Property
from pyagentspec.tools import ClientTool


@pytest.fixture()
def tool_flow() -> Flow:
    x_property = Property(json_schema={"title": "input", "type": "number"})
    x_square_property = Property(json_schema={"title": "input_square", "type": "number"})

    square_tool = ClientTool(
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

    return flow


def test_toolnode_can_be_imported_and_executed(tool_flow: Flow) -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(tool_flow)

    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke({"inputs": {"input": 4}}, config=config)
    assert "__interrupt__" in result

    result = agent.invoke(Command(resume=16), config=config)

    outputs = result["outputs"]
    assert "input_square" in outputs
    assert outputs["input_square"] == 16


@pytest.mark.anyio
async def test_toolnode_can_be_executed_async_with_interrupt_resume(tool_flow: Flow) -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(tool_flow)

    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    if sys.version_info < (3, 11):
        with pytest.raises(RuntimeError, match="Called get_config outside of a runnable context"):
            await agent.ainvoke({"inputs": {"input": 4}}, config=config)
        return
    result = await agent.ainvoke({"inputs": {"input": 4}}, config=config)
    assert "__interrupt__" in result

    result = await agent.ainvoke(Command(resume=16), config=config)

    outputs = result["outputs"]
    assert "input_square" in outputs
    assert outputs["input_square"] == 16
