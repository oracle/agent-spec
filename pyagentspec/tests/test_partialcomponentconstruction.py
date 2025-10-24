# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Type

import pytest

from pyagentspec import Agent, Swarm
from pyagentspec.component import Component
from pyagentspec.flows.edges import DataFlowEdge
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import BranchingNode, EndNode, LlmNode, StartNode, ToolNode
from pyagentspec.llms.openaiconfig import OpenAiConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.property import StringProperty
from pyagentspec.tools.tool import Tool
from pyagentspec.validation_helpers import PyAgentSpecErrorDetails


def test_flow_partially_constructed_infers_inputs() -> None:
    start_node = StartNode(
        name="node", inputs=[StringProperty(title="a"), StringProperty(title="b")]
    )
    partial_flow_config_as_dict = {
        "start_node": start_node,
        "control_flow_connections": [],
        "nodes": [start_node],
    }
    partial_flow = Flow.build_from_partial_config(partial_flow_config_as_dict)
    assert partial_flow.inputs == [StringProperty(title="a"), StringProperty(title="b")]
    assert partial_flow.outputs == []


def test_errors_can_be_listed_for_partially_constructed_flow() -> None:
    start_node = StartNode(
        name="node", inputs=[StringProperty(title="a"), StringProperty(title="b")]
    )
    partial_flow_config_as_dict = {
        "start_node": start_node,
        "control_flow_connections": [],
        "nodes": [start_node],
    }
    validation_errors = Flow.get_validation_errors(partial_flow_config_as_dict)
    assert (
        PyAgentSpecErrorDetails(type="missing", loc=("name",), msg="Field required")
        in validation_errors
    )


def test_flow_partially_constructed_infers_outputs() -> None:
    start_node = StartNode(name="start", inputs=[StringProperty(title="input1")])
    end_node = EndNode(name="end_node", outputs=[StringProperty(title="output1")])
    control_flow = [ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)]
    partial_flow_config_as_dict = {
        "start_node": start_node,
        "nodes": [start_node, end_node],
        "control_flow_connections": control_flow,
    }
    partial_flow = Flow.build_from_partial_config(partial_flow_config_as_dict)
    assert partial_flow.outputs == [StringProperty(title="output1")]


def test_no_validation_errors_for_valid_partial_flow() -> None:
    start_node = StartNode(
        name="start", inputs=[StringProperty(title="a"), StringProperty(title="b")]
    )
    end_node = EndNode(name="end", outputs=[StringProperty(title="output1")])
    control_flow = [ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)]
    partial_flow_config_as_dict = {
        "name": "flow_1",
        "start_node": start_node,
        "nodes": [start_node, end_node],
        "control_flow_connections": control_flow,
    }
    validation_errors = Flow.get_validation_errors(partial_flow_config_as_dict)
    assert not validation_errors


def test_llm_node_partially_constructed() -> None:
    start_node = StartNode(name="start", inputs=[StringProperty(title="input")])
    llm_node = LlmNode(
        name="llm",
        prompt_template="{{input}}",
        inputs=[StringProperty(title="input")],
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )
    control_flow = [ControlFlowEdge(name="start_to_llm", from_node=start_node, to_node=llm_node)]
    partial_config = {
        "name": "flow_2",
        "start_node": start_node,
        "nodes": [start_node, llm_node],
        "control_flow_connections": control_flow,
    }
    partially_constructed_flow = Flow.build_from_partial_config(partial_config)
    assert partially_constructed_flow.inputs == [StringProperty(title="input")]


with_all_concrete_component_types = pytest.mark.parametrize(
    "component_cls",
    [
        component_cls
        for component_cls in Component._get_all_subclasses()
        if not component_cls._is_abstract
    ],
)


@with_all_concrete_component_types
def test_all_component_types_can_be_constructed_out_of_nothing(
    component_cls: Type[Component],
) -> None:
    component = component_cls.build_from_partial_config({})
    assert isinstance(component, component_cls)


@with_all_concrete_component_types
@pytest.mark.filterwarnings("ignore:.*beta:UserWarning")
def test_all_component_types_can_list_validation_errors_out_of_nothing(
    component_cls: Type[Component],
) -> None:
    validation_errors = component_cls.get_validation_errors({})
    missing_name = PyAgentSpecErrorDetails(type="missing", loc=("name",), msg="Field required")
    assert missing_name in validation_errors


@with_all_concrete_component_types
@pytest.mark.filterwarnings("ignore:.*beta:UserWarning")
def test_validation_errors_dont_contain_missing_name_when_name_is_provided(
    component_cls: Type[Component],
) -> None:
    validation_errors = component_cls.get_validation_errors({"name": "the_component_name"})
    missing_name = PyAgentSpecErrorDetails(type="missing", loc=("name",), msg="Field required")
    assert missing_name not in validation_errors


def test_flow_can_return_multiple_validation_errors() -> None:
    start_node = StartNode(name="start", inputs=[StringProperty(title="input")])
    end_node = EndNode(name="end", outputs=[StringProperty(title="output")])
    partial_config = {
        "name": "flow_1",
        "start_node": StartNode(name="WRONG_START"),
        "nodes": [start_node, end_node],
        "control_flow_connections": [
            ControlFlowEdge(name="edge", from_node=start_node, to_node=EndNode(name="WRONG_END"))
        ],
        "data_flow_connections": [
            DataFlowEdge(
                name="edge",
                source_node=StartNode(name="WRONG_START", inputs=[StringProperty(title="input")]),
                source_output="input",
                destination_node=end_node,
                destination_input="output",
            )
        ],
    }
    flow = Flow.build_from_partial_config(partial_config)
    assert isinstance(flow, Flow)
    validation_errors = Flow.get_validation_errors(partial_config)
    wrong_start_node = PyAgentSpecErrorDetails(
        type="value_error",
        msg=(
            "Value error, The ``start_node`` node is not matching the start "
            "node from the list of nodes in the flow ``nodes`` (start node was"
            " 'WRONG_START', found 'start' in ``nodes``."
        ),
    )
    assert wrong_start_node in validation_errors
    wrong_control_edge = PyAgentSpecErrorDetails(
        type="value_error",
        msg=(
            "Value error, A control flow edge was defined, but the flow does"
            " not contain the destination node 'WRONG_END'"
        ),
    )
    assert wrong_control_edge in validation_errors
    wrong_data_edge = PyAgentSpecErrorDetails(
        type="value_error",
        msg=(
            "Value error, A data flow edge was defined, but the flow does not contain the source "
            "node 'WRONG_START'"
        ),
    )
    assert wrong_data_edge in validation_errors


def test_branching_step_can_infer_branches_from_partial_config() -> None:
    partial_config = {"mapping": {"x": "B", "y": "B", "z": "A"}}
    branching_node = BranchingNode.build_from_partial_config(partial_config)
    assert branching_node.branches == ["A", "B", BranchingNode.DEFAULT_BRANCH]


def test_llm_node_can_be_constructed_with_missing_inputs() -> None:
    partial_config = {
        "name": "My Llm node",
        "inputs": [StringProperty(title="a"), StringProperty(title="b")],
        "prompt_template": "{{a}} + {{b}} = {{c}} * {{d}}",
    }
    llm_node = LlmNode.build_from_partial_config(partial_config)
    assert llm_node.inputs == [StringProperty(title="a"), StringProperty(title="b")]


def test_nested_component_can_be_constructed() -> None:
    partial_config = {
        "name": "ToolNode",
        "tool": {
            "name": "My Server Tool",
            "component_type": "ServerTool",
        },
    }
    tool_node = ToolNode.build_from_partial_config(partial_config)
    assert isinstance(tool_node.tool, Tool)


def test_nested_component_returns_validation_errors() -> None:
    partial_config = {
        "tool": {
            "component_type": "ServerTool",
        }
    }
    validation_errors = ToolNode.get_validation_errors(partial_config)
    # The partial config is missing the name for the ToolNode and for the ServerTool it contains
    assert (
        PyAgentSpecErrorDetails(
            type="missing",
            msg="Field required",
            loc=(
                "tool",
                "name",
            ),
        )
        in validation_errors
    )
    assert (
        PyAgentSpecErrorDetails(type="missing", msg="Field required", loc=("name",))
        in validation_errors
    )


def test_complex_nested_component_returns_validation_errors() -> None:
    partial_config = {
        "name": "My agent",
        "llm_config": OpenAiConfig(name="default", model_id="test_model"),
        # Tool with missing name, it should raise a validation error
        "tools": [{"component_type": "ServerTool"}, {"component_type": "ClientTool"}],
        "system_prompt": "Be nice",
    }
    validation_errors = Agent.get_validation_errors(partial_config)
    _ = Agent.build_from_partial_config(partial_config)
    assert len(validation_errors) >= 2
    assert (
        PyAgentSpecErrorDetails(type="missing", msg="Field required", loc=("tools", 0, "name"))
        in validation_errors
    )
    assert (
        PyAgentSpecErrorDetails(type="missing", msg="Field required", loc=("tools", 1, "name"))
        in validation_errors
    )
