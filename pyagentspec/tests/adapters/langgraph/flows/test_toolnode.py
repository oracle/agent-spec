# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import sys
from typing import Any, Dict, List

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.property import (
    ListProperty,
    NumberProperty,
    ObjectProperty,
    Property,
    StringProperty,
)
from pyagentspec.tools import ClientTool


@pytest.fixture()
def tool_flow() -> Flow:
    x_property = NumberProperty(title="input")
    x_square_property = NumberProperty(title="input_square")

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


def _build_flow_with_client_tool(
    *,
    input_prop: Property,
    output_props: List[Property],
):
    start = StartNode(name="start", inputs=[input_prop])
    tool = ClientTool(
        name="echo_tool",
        description="Client-side tool used for testing",
        inputs=[input_prop],
        outputs=output_props,
    )
    tool_node = ToolNode(name="tool", tool=tool)
    end = EndNode(name="end", outputs=output_props)

    data_edges = [
        DataFlowEdge(
            name="x_to_tool",
            source_node=start,
            source_output=input_prop.title,
            destination_node=tool_node,
            destination_input=input_prop.title,
        ),
        *[
            DataFlowEdge(
                name=f"{p.title}_to_end",
                source_node=tool_node,
                source_output=p.title,
                destination_node=end,
                destination_input=p.title,
            )
            for p in output_props
        ],
    ]

    flow = Flow(
        name="tool_output_flow",
        start_node=start,
        nodes=[start, tool_node, end],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_tool", from_node=start, to_node=tool_node),
            ControlFlowEdge(name="tool_to_end", from_node=tool_node, to_node=end),
        ],
        data_flow_connections=data_edges,
    )
    return flow


def _run_flow_and_resume(flow: Flow, resume_payload: Any) -> Dict[str, Any]:
    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "t"}})
    # First call interrupts at the client tool
    result = agent.invoke({"inputs": {flow.start_node.inputs[0].title: 123}}, config=config)
    assert "__interrupt__" in result
    # Resume with the payload which simulates the tool output
    resumed = agent.invoke(Command(resume=resume_payload), config=config)
    return resumed["outputs"]


def test_toolnode_single_output_wraps_multi_dict_under_declared_key() -> None:
    flow = _build_flow_with_client_tool(
        input_prop=NumberProperty(title="x"),
        output_props=[ObjectProperty(title="out_dict", properties={})],
    )
    expected_return_value = {"a": 1, "b": 2}
    outputs = _run_flow_and_resume(flow, expected_return_value)
    assert outputs == {"out_dict": expected_return_value}


def test_toolnode_single_output_wraps_single_dict_under_declared_key() -> None:
    flow = _build_flow_with_client_tool(
        input_prop=NumberProperty(title="x"),
        output_props=[ObjectProperty(title="out_dict", properties={})],
    )
    expected_return_value = {"a": 1}
    outputs = _run_flow_and_resume(flow, expected_return_value)
    assert outputs == {"out_dict": expected_return_value}


def test_toolnode_single_output_unwraps_single_dict_under_same_key() -> None:
    flow = _build_flow_with_client_tool(
        input_prop=NumberProperty(title="x"),
        output_props=[ObjectProperty(title="out_dict", properties={})],
    )
    expected_return_value = {"out_dict": 1}
    outputs = _run_flow_and_resume(flow, expected_return_value)
    assert outputs == expected_return_value


def test_toolnode_single_output_passes_through_when_key_matches() -> None:
    flow = _build_flow_with_client_tool(
        input_prop=NumberProperty(title="x"), output_props=[StringProperty(title="out_string")]
    )
    expected_return_value = "value"
    outputs = _run_flow_and_resume(flow, expected_return_value)
    assert outputs == {"out_string": expected_return_value}


def test_toolnode_multiple_outputs_filter_and_defaults_fill_missing() -> None:
    flow = _build_flow_with_client_tool(
        input_prop=NumberProperty(title="x"),
        output_props=[NumberProperty(title="a"), NumberProperty(title="b", default=0)],
    )
    outputs = _run_flow_and_resume(flow, {"a": 5})
    assert outputs == {"a": 5, "b": 0}


def test_toolnode_list_output_generic_maps_to_single_declared_output() -> None:
    x = NumberProperty(title="x")
    out = ListProperty(title="out", item_type=NumberProperty(title="item"))
    flow = _build_flow_with_client_tool(input_prop=x, output_props=[out])
    outputs = _run_flow_and_resume(flow, [1, 2, 3])
    assert outputs == {"out": [1, 2, 3]}


def test_toolnode_scalar_output_maps_to_single_declared_output() -> None:
    x = NumberProperty(title="x")
    out = NumberProperty(title="out_number")
    flow = _build_flow_with_client_tool(input_prop=x, output_props=[out])
    outputs = _run_flow_and_resume(flow, 42)
    assert outputs == {"out_number": 42}


def test_toolnode_tuple_output_maps_to_single_declared_string_output() -> None:
    # Tuple outputs are treated as scalars; with a string-declared output,
    # the value is stringified by _cast_values_and_add_defaults.
    x = NumberProperty(title="x")
    out = StringProperty(title="out")
    flow = _build_flow_with_client_tool(input_prop=x, output_props=[out])
    outputs = _run_flow_and_resume(flow, (1, 2))
    assert outputs == {"out": "[1, 2]"}


def test_toolnode_tuple_output_maps_positionally_to_multiple_outputs() -> None:
    x = NumberProperty(title="x")
    a = NumberProperty(title="a")
    b = StringProperty(title="b")
    flow = _build_flow_with_client_tool(input_prop=x, output_props=[a, b])
    outputs = _run_flow_and_resume(flow, (7, "ok"))
    assert outputs == {"a": 7, "b": "ok"}


def test_tool_node_multiple_complex_outputs() -> None:
    flow = _build_flow_with_client_tool(
        input_prop=NumberProperty(title="x"),
        output_props=[
            NumberProperty(title="num"),
            ObjectProperty(title="obj", properties={}),
            ListProperty(title="array", item_type=NumberProperty(title="elem")),
        ],
    )
    outputs = _run_flow_and_resume(flow, (7, {"key": "val"}, [1]))
    assert outputs == {"num": 7, "obj": {"key": "val"}, "array": [1]}
