# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import CatchExceptionNode, EndNode, StartNode, ToolNode
from pyagentspec.property import NullProperty, Property, StringProperty, UnionProperty
from pyagentspec.tools import ServerTool


def _create_subflow_with_tool(
    *, tool: ServerTool, inp: Property, outp: StringProperty, end_branch: str | None = None
) -> Flow:
    sub_start = StartNode(name="sub_start", inputs=[inp])
    tool_node = ToolNode(name=f"{tool.name}_node", tool=tool)
    sub_end = (
        EndNode(name="sub_end", outputs=[outp], branch_name=end_branch)
        if end_branch
        else EndNode(name="sub_end", outputs=[outp])
    )
    return Flow(
        name=f"{tool.name}_subflow",
        start_node=sub_start,
        nodes=[sub_start, tool_node, sub_end],
        control_flow_connections=[
            ControlFlowEdge(name="s2t", from_node=sub_start, to_node=tool_node),
            ControlFlowEdge(name="t2e", from_node=tool_node, to_node=sub_end),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="in",
                source_node=sub_start,
                source_output=inp.title,
                destination_node=tool_node,
                destination_input=inp.title,
            ),
            DataFlowEdge(
                name="out",
                source_node=tool_node,
                source_output=outp.title,
                destination_node=sub_end,
                destination_input=outp.title,
            ),
        ],
        inputs=[inp],
        outputs=[outp],
    )


def _create_flow_with_catch_and_error_path(
    *,
    subflow: Flow,
    inp: Property,
    outp: StringProperty,
):
    catch = CatchExceptionNode(name="catch", subflow=subflow)

    start = StartNode(name="start", inputs=[inp])
    error_info = UnionProperty(
        title="error_info",
        any_of=[StringProperty(title="error_info"), NullProperty(title="error_info")],
        default=None,
    )
    end = EndNode(name="end", outputs=[outp])
    error_end = EndNode(name="error_end", outputs=[error_info], branch_name="ERROR")

    flow = Flow(
        name="outer",
        start_node=start,
        nodes=[start, catch, end, error_end],
        control_flow_connections=[
            ControlFlowEdge(name="s2c", from_node=start, to_node=catch),
            ControlFlowEdge(name="c2e", from_node=catch, to_node=end),
            ControlFlowEdge(
                name="caught_to_error",
                from_node=catch,
                from_branch=CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH,
                to_node=error_end,
            ),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="in",
                source_node=start,
                source_output=inp.title,
                destination_node=catch,
                destination_input=inp.title,
            ),
            DataFlowEdge(
                name="out",
                source_node=catch,
                source_output=outp.title,
                destination_node=end,
                destination_input=outp.title,
            ),
            DataFlowEdge(
                name="exception_to_error",
                source_node=catch,
                source_output="caught_exception_info",
                destination_node=error_end,
                destination_input=error_info.title,
            ),
        ],
        inputs=[inp],
        outputs=[outp, error_info],
    )
    return flow, error_info


def _create_flow_with_catch_and_custom_ok_branch(
    *,
    subflow: Flow,
    inp: Property,
    outp: StringProperty,
    custom_branch: str,
):
    catch = CatchExceptionNode(name="catch", subflow=subflow)

    start = StartNode(name="start", inputs=[inp])
    error_info = UnionProperty(
        title="error_info",
        any_of=[StringProperty(title="error_info"), NullProperty(title="error_info")],
        default=None,
    )
    ok_end = EndNode(name="ok_end", outputs=[outp, error_info])
    other_end = EndNode(name="other_end")

    flow = Flow(
        name="outer",
        start_node=start,
        nodes=[start, catch, ok_end, other_end],
        control_flow_connections=[
            ControlFlowEdge(name="s2c", from_node=start, to_node=catch),
            # Route custom subflow branch explicitly
            ControlFlowEdge(name="ok", from_node=catch, from_branch=custom_branch, to_node=ok_end),
            # Default path not used here, but defined to be explicit
            ControlFlowEdge(name="def", from_node=catch, to_node=other_end),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="in",
                source_node=start,
                source_output=inp.title,
                destination_node=catch,
                destination_input=inp.title,
            ),
            DataFlowEdge(
                name="y",
                source_node=catch,
                source_output=outp.title,
                destination_node=ok_end,
                destination_input=outp.title,
            ),
            DataFlowEdge(
                name="err",
                source_node=catch,
                source_output="caught_exception_info",
                destination_node=ok_end,
                destination_input=error_info.title,
            ),
        ],
        inputs=[inp],
        outputs=[outp, error_info],
    )
    return flow, error_info


def _create_flow_with_catch_default_branch(
    *,
    subflow: Flow,
    inp: Property,
    outp: StringProperty,
):
    catch = CatchExceptionNode(name="catch", subflow=subflow)

    start = StartNode(name="start", inputs=[inp])
    error_info = UnionProperty(
        title="error_info",
        any_of=[StringProperty(title="error_info"), NullProperty(title="error_info")],
        default=None,
    )
    next_end = EndNode(name="next_end", outputs=[outp, error_info])

    flow = Flow(
        name="outer",
        start_node=start,
        nodes=[start, catch, next_end],
        control_flow_connections=[
            ControlFlowEdge(name="s2c", from_node=start, to_node=catch),
            ControlFlowEdge(name="nxt", from_node=catch, to_node=next_end),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="in",
                source_node=start,
                source_output=inp.title,
                destination_node=catch,
                destination_input=inp.title,
            ),
            DataFlowEdge(
                name="y",
                source_node=catch,
                source_output=outp.title,
                destination_node=next_end,
                destination_input=outp.title,
            ),
            DataFlowEdge(
                name="err",
                source_node=catch,
                source_output="caught_exception_info",
                destination_node=next_end,
                destination_input=error_info.title,
            ),
        ],
        inputs=[inp],
        outputs=[outp, error_info],
    )
    return flow, error_info


def test_catchexceptionnode_can_be_imported_and_executed_without_exception_and_with_exception() -> (
    None
):
    # Build a subflow that simply passes input to output
    # ServerTool that raises ValueError when x < 0, otherwise returns "ok"
    inp = Property(json_schema={"title": "x", "type": "integer"})
    outp = StringProperty(title="y", default="")

    def _flaky_func(x: int) -> str:
        if x < 0:
            raise ValueError("x must be non-negative")
        return "ok"

    flaky_tool = ServerTool(
        name="flaky_tool",
        description="Raises for negative inputs",
        inputs=[inp],
        outputs=[outp],
    )
    subflow = _create_subflow_with_tool(tool=flaky_tool, inp=inp, outp=outp)

    flow, error_info = _create_flow_with_catch_and_error_path(subflow=subflow, inp=inp, outp=outp)

    agent = AgentSpecLoader(tool_registry={"flaky_tool": _flaky_func}).load_component(flow)

    # Case 1: No exception
    result = agent.invoke({"inputs": {inp.title: 1}})
    outputs = result["outputs"]
    assert outputs[outp.title] == "ok"

    # Case 2: Exception is raised -> default output value and caught_exception_info populated
    result = agent.invoke({"inputs": {inp.title: -1}})
    outputs = result["outputs"]
    assert outputs[outp.title] == ""  # default from node property
    assert isinstance(result["node_execution_details"], dict)
    # Final branch should be the error end node branch
    assert result["node_execution_details"]["branch"] == "ERROR"
    assert "error_info" in outputs and isinstance(outputs["error_info"], str)


def test_catchexceptionnode_success_propagates_custom_branch_and_none_exception_info() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Build subflow that always succeeds and ends with branch "OK"
    inp = Property(json_schema={"title": "x", "type": "integer"})
    outp = StringProperty(title="y", default="")
    error_info = UnionProperty(
        title="error_info",
        any_of=[StringProperty(title="error_info"), NullProperty(title="error_info")],
        default=None,
    )

    def _ok_impl(x: int) -> str:
        return "ok"

    ok_tool = ServerTool(
        name="ok_tool",
        description="Always returns ok",
        inputs=[inp],
        outputs=[outp],
    )
    subflow = _create_subflow_with_tool(tool=ok_tool, inp=inp, outp=outp, end_branch="OK")
    flow, error_info = _create_flow_with_catch_and_custom_ok_branch(
        subflow=subflow, inp=inp, outp=outp, custom_branch="OK"
    )

    agent = AgentSpecLoader(tool_registry={"ok_tool": _ok_impl}).load_component(flow)

    result = agent.invoke({"inputs": {inp.title: 7}})
    # Final branch in outer flow comes from EndNode (default: next)
    assert result["node_execution_details"]["branch"] == CatchExceptionNode.DEFAULT_NEXT_BRANCH
    outputs = result["outputs"]
    assert outputs[outp.title] == "ok"
    # On success path, caught_exception_info should be None
    assert outputs[error_info.title] is None


def test_catchexceptionnode_success_default_branch_and_none_exception_info() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    # Subflow with default branch (no custom branch_name)
    inp = Property(json_schema={"title": "x", "type": "integer"})
    outp = StringProperty(title="y", default="")
    error_info = UnionProperty(
        title="error_info",
        any_of=[StringProperty(title="error_info"), NullProperty(title="error_info")],
        default=None,
    )

    def _ok_impl(x: int) -> str:
        return "ok"

    ok_tool = ServerTool(
        name="ok_tool_default",
        description="Always returns ok",
        inputs=[inp],
        outputs=[outp],
    )

    subflow = _create_subflow_with_tool(tool=ok_tool, inp=inp, outp=outp)
    flow, error_info = _create_flow_with_catch_default_branch(subflow=subflow, inp=inp, outp=outp)

    agent = AgentSpecLoader(tool_registry={"ok_tool_default": _ok_impl}).load_component(flow)
    result = agent.invoke({"inputs": {inp.title: 5}})
    # Default branch expected to be "next"
    assert result["node_execution_details"]["branch"] == CatchExceptionNode.DEFAULT_NEXT_BRANCH
    outputs = result["outputs"]
    assert outputs[outp.title] == "ok"
    assert outputs[error_info.title] is None
