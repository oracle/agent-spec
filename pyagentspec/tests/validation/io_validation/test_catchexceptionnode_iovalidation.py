# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.flowbuilder import FlowBuilder
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import LlmNode
from pyagentspec.flows.nodes.catchexceptionnode import CatchExceptionNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.property import Property, StringProperty


@pytest.fixture
def flow() -> Flow:
    in_property = Property(json_schema={"title": "in_prop", "type": "string"})
    out_property = Property(json_schema={"title": "out_prop", "type": "string", "default": ""})
    start_node = StartNode(name="start_node", inputs=[in_property])
    end_node = EndNode(name="end_node", outputs=[out_property])
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="edge",
                source_node=start_node,
                source_output="in_prop",
                destination_node=end_node,
                destination_input="out_prop",
            ),
        ],
    )
    return flow


def test_catchexceptionnode_has_inputs_and_outputs_matching_subflow(flow: Flow) -> None:
    node = CatchExceptionNode(name="catch_node", subflow=flow)
    assert node.inputs == [StringProperty(title="in_prop")]
    # Outputs include subflow outputs + caught_exception_info
    assert any(p.title == "out_prop" for p in node.outputs or [])
    assert any(p.title == "caught_exception_info" for p in node.outputs or [])


def test_catchexceptionnode_branches_include_subflow_and_exception(flow: Flow) -> None:
    node = CatchExceptionNode(name="catch_node", subflow=flow)
    assert set(node.branches) == {
        Node.DEFAULT_NEXT_BRANCH,
        CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH,
    }


def test_catchexceptionnode_raises_when_subflow_outputs_lack_defaults(default_llm_config) -> None:
    n1 = LlmNode(
        name="n1", llm_config=default_llm_config, prompt_template="hi"
    )  # node with no default output
    subflow = FlowBuilder.build_linear_flow([n1])
    with pytest.raises(ValueError, match="must define a default value"):
        _ = CatchExceptionNode(name="catch_node", subflow=subflow)


def test_catchexceptionnode_raises_when_provided_outputs_names_do_not_match_subflow(
    flow: Flow,
) -> None:
    bad_outputs = [StringProperty(title="different", default="")]
    with pytest.raises(ValueError, match="same names as subflow outputs"):
        CatchExceptionNode(name="catch_node", subflow=flow, outputs=bad_outputs)


def test_catchexceptionnode_raises_when_provided_outputs_missing_defaults(flow: Flow) -> None:
    missing_default_outputs = [
        StringProperty(title="out_prop"),
        StringProperty(title=CatchExceptionNode.DEFAULT_EXCEPTION_INFO_VALUE),
    ]
    with pytest.raises(ValueError, match="must define a default value"):
        CatchExceptionNode(name="catch_node", subflow=flow, outputs=missing_default_outputs)


def test_catchexceptionnode_raises_when_subflow_branch_conflicts_with_exception_branch() -> None:
    in_property = StringProperty(title="in_prop")
    out_property = StringProperty(title="out_prop", default="")
    start_node = StartNode(name="start_node", inputs=[in_property])
    end_node = EndNode(
        name="end_node",
        outputs=[out_property],
        branch_name=CatchExceptionNode.CAUGHT_EXCEPTION_BRANCH,
    )
    subflow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="edge",
                source_node=start_node,
                source_output="in_prop",
                destination_node=end_node,
                destination_input="out_prop",
            ),
        ],
    )
    with pytest.raises(ValueError, match="conflicts with the exception branch name"):
        CatchExceptionNode(name="catch_node", subflow=subflow)


def test_catchexceptionnode_raises_when_subflow_output_conflicts_with_exception_info() -> None:
    in_property = StringProperty(title="in_prop")
    out_property = StringProperty(
        title=CatchExceptionNode.DEFAULT_EXCEPTION_INFO_VALUE,
        default="",
    )
    start_node = StartNode(name="start_node", inputs=[in_property])
    end_node = EndNode(name="end_node", outputs=[out_property])
    subflow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="edge",
                source_node=start_node,
                source_output="in_prop",
                destination_node=end_node,
                destination_input=CatchExceptionNode.DEFAULT_EXCEPTION_INFO_VALUE,
            ),
        ],
    )
    with pytest.raises(
        ValueError, match="conflicts with the reserved exception information output name"
    ):
        CatchExceptionNode(name="catch_node", subflow=subflow)
