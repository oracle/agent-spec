# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.agentnode import AgentNode
from pyagentspec.flows.nodes.branchingnode import BranchingNode
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.flownode import FlowNode
from pyagentspec.flows.nodes.llmnode import LlmNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import StringProperty


@pytest.fixture
def vllmconfig() -> VllmConfig:
    return VllmConfig(name="llm_name", model_id="llm_id", url="http://some.where")


def test_llm_node_has_single_next_branch(vllmconfig: VllmConfig) -> None:
    node = LlmNode(
        id="llm_node_id",
        name="llm_node_name",
        llm_config=vllmconfig,
        prompt_template="llm_node_prompt_template",
    )
    assert isinstance(node.branches, list)
    assert len(node.branches) == 1
    assert set(node.branches) == {"next"}


def test_specifying_incorrect_next_branches_for_llm_node_raises(vllmconfig: VllmConfig) -> None:
    expected_error_message = (
        r"\['(hello|world)', '(hello|world)'\] does not match expected branches \['next'\]"
    )
    with pytest.raises(ValueError, match=expected_error_message):
        LlmNode(
            id="llm_node_id",
            name="llm_node_name",
            llm_config=vllmconfig,
            prompt_template="llm_node_prompt_template",
            branches=["hello", "world"],
        )


def test_branching_node_correctly_infers_its_next_branches() -> None:
    node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_2": "some_branch_2",
            "some_value_3": "some_branch_3",
        },
    )
    assert isinstance(node.branches, list)
    assert len(node.branches) == 4
    assert set(node.branches) == {"default", "some_branch_1", "some_branch_2", "some_branch_3"}


def test_branching_node_correctly_infers_its_next_branches_with_repetition() -> None:
    node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_2": "some_branch_1",
            "some_value_3": "default",
        },
    )
    assert isinstance(node.branches, list)
    assert len(node.branches) == 2
    assert set(node.branches) == {"default", "some_branch_1"}


def test_branching_node_raises_when_incorrectly_specifying_next_branches() -> None:
    expected_error_message = (
        r"branches \['(a|b)', '(b|a)'\] does not match expected branches "
        r"\['(some_branch_1|default)', '(some_branch_1|default)'\]"
    )
    with pytest.raises(ValueError, match=expected_error_message):
        BranchingNode(
            name="branching_node_name",
            mapping={
                "some_value_1": "some_branch_1",
                "some_value_2": "some_branch_1",
                "some_value_3": "default",
            },
            branches=["a", "b"],
        )


def test_branching_node_can_be_instantiated_with_correct_branches() -> None:
    node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_2": "some_branch_1",
            "some_value_3": "default",
        },
        branches=["default", "some_branch_1"],
    )
    assert isinstance(node.branches, list)
    assert len(node.branches) == 2
    assert set(node.branches) == {"default", "some_branch_1"}


def test_branching_node_has_correct_input_outputs() -> None:
    node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_3": "default",
        },
    )
    assert node.inputs == [
        StringProperty(title="branching_mapping_key", description="Next branch name in the flow")
    ]
    assert node.outputs == []


def test_branching_node_works_when_input_is_renamed_by_proper_amount_of_inputs() -> None:
    node = BranchingNode(
        name="branching_node_name",
        mapping={
            "some_value_1": "some_branch_1",
            "some_value_3": "default",
        },
        inputs=[StringProperty(title="some_unknown_input")],
    )
    assert node.inputs == [StringProperty(title="some_unknown_input")]
    assert node.outputs == []


def test_agent_node_can_be_assigned_arbitrary_branches(vllmconfig: VllmConfig) -> None:
    agent = Agent(name="agent_name", llm_config=vllmconfig, system_prompt="Be helpful to the user")
    node = AgentNode(name="node_name", branches=["option_a", "option_b", "option_c"], agent=agent)
    assert isinstance(node.branches, list)
    assert len(node.branches) == 3
    assert set(node.branches) == {"option_a", "option_b", "option_c"}


def test_agent_node_has_branch_next_by_default(vllmconfig: VllmConfig) -> None:
    agent = Agent(name="agent_name", llm_config=vllmconfig, system_prompt="Be helpful to the user")
    node = AgentNode(name="node_name", agent=agent)
    assert isinstance(node.branches, list)
    assert len(node.branches) == 1
    assert set(node.branches) == {"next"}


def test_flow_node_has_next_branch_by_default(vllmconfig: VllmConfig) -> None:
    llm_node = LlmNode(name="node_name", llm_config=vllmconfig, prompt_template="How much is 6x7?")
    start_node = StartNode(name="start_node")
    end_node = EndNode(name="end_node")
    flow = Flow(
        name="flow_name",
        start_node=start_node,
        nodes=[start_node, llm_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start::llm", from_node=start_node, to_node=llm_node),
            ControlFlowEdge(name="llm::end", from_node=llm_node, to_node=end_node),
        ],
    )
    flow_node = FlowNode(name="flow_node_name", subflow=flow)
    assert isinstance(flow_node.branches, list)
    assert len(flow_node.branches) == 1
    assert set(flow_node.branches) == {"next"}


def test_looping_flow_raises_if_no_end_node(vllmconfig: VllmConfig) -> None:
    start_node = StartNode(name="start_node")
    branching = BranchingNode(name="node_name", mapping={"1": "default", "2": "default"})
    llm_node = LlmNode(
        id="llm_node_id",
        name="llm_node_name",
        llm_config=vllmconfig,
        prompt_template="llm_node_prompt_template",
    )
    with pytest.raises(
        ValueError, match="A Flow should be composed of at least one EndNode but didn't find any"
    ):
        Flow(
            name="flow_name",
            start_node=start_node,
            nodes=[start_node, branching, llm_node],
            control_flow_connections=[
                ControlFlowEdge(name="start::branching", from_node=start_node, to_node=branching),
                ControlFlowEdge(
                    name="!", from_node=branching, from_branch="default", to_node=llm_node
                ),
            ],
        )


def test_flow_node_branches_is_next_by_default() -> None:
    start_node = StartNode(name="start_node")
    branching = BranchingNode(name="node_name", mapping={"1": "a", "2": "b", "3": "c"})
    start_to_branch = ControlFlowEdge(name="start::branch", from_node=start_node, to_node=branching)
    end_x, end_y, end_z = EndNode(name="x"), EndNode(name="y"), EndNode(name="z")
    branch_to_x = ControlFlowEdge(name="!", from_node=branching, from_branch="a", to_node=end_x)
    branch_to_y = ControlFlowEdge(name="!", from_node=branching, from_branch="b", to_node=end_y)
    branch_to_z = ControlFlowEdge(name="!", from_node=branching, from_branch="c", to_node=end_z)
    default = ControlFlowEdge(
        name="!", from_node=branching, from_branch="default", to_node=branching
    )
    flow = Flow(
        name="flow_name",
        start_node=start_node,
        nodes=[start_node, branching, end_x, end_y, end_z],
        control_flow_connections=[start_to_branch, branch_to_x, branch_to_y, branch_to_z, default],
    )
    flow_node = FlowNode(name="flow_node_name", subflow=flow)
    assert isinstance(flow_node.branches, list)
    assert len(flow_node.branches) == 1
    assert flow_node.branches == ["next"]


def test_flow_node_branches_are_branch_name_of_end_nodes() -> None:
    start_node = StartNode(name="start_node")
    branching = BranchingNode(name="node_name", mapping={"1": "a", "2": "b", "3": "c"})
    start_to_branch = ControlFlowEdge(name="start::branch", from_node=start_node, to_node=branching)
    end_x, end_y, end_z = (
        EndNode(name="x", branch_name="end_x"),
        EndNode(name="y", branch_name="end_y"),
        EndNode(name="z", branch_name="end_z"),
    )
    branch_to_x = ControlFlowEdge(name="!", from_node=branching, from_branch="a", to_node=end_x)
    branch_to_y = ControlFlowEdge(name="!", from_node=branching, from_branch="b", to_node=end_y)
    branch_to_z = ControlFlowEdge(name="!", from_node=branching, from_branch="c", to_node=end_z)
    default = ControlFlowEdge(
        name="!", from_node=branching, from_branch="default", to_node=branching
    )
    flow = Flow(
        name="flow_name",
        start_node=start_node,
        nodes=[start_node, branching, end_x, end_y, end_z],
        control_flow_connections=[start_to_branch, branch_to_x, branch_to_y, branch_to_z, default],
    )
    flow_node = FlowNode(name="flow_node_name", subflow=flow)
    assert isinstance(flow_node.branches, list)
    assert len(flow_node.branches) == 3
    assert set(flow_node.branches) == {"end_x", "end_y", "end_z"}


def test_agent_node_raises_when_duplicate_branches_are_specified(vllmconfig: VllmConfig) -> None:
    agent = Agent(name="agent_name", llm_config=vllmconfig, system_prompt="Be helpful to the user")
    with pytest.raises(ValueError, match="The branches of a node should have no duplicate"):
        AgentNode(name="node_name", agent=agent, branches=["next", "next"])
