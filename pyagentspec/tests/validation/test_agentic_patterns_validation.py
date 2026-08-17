# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.llms import OpenAiConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.property import FloatProperty, StringProperty
from pyagentspec.swarm import Swarm


def test_managerworkers_without_workers_raises_errors() -> None:
    manager_agent = Agent(
        name="manager_agent",
        system_prompt="You are a group manager.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )

    with pytest.raises(ValueError, match=("Cannot define a `ManagerWorkers` with no worker")):
        ManagerWorkers(
            name="managerworkers",
            group_manager=manager_agent,
            workers=[],
        )


def test_managerworkers_with_manager_as_a_worker_raises_errors() -> None:
    manager_agent = Agent(
        name="manager_agent",
        system_prompt="You are a group manager.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )

    with pytest.raises(ValueError, match=("Group manager cannot be a worker")):
        ManagerWorkers(
            name="managerworkers",
            group_manager=manager_agent,
            workers=[manager_agent],
        )


def test_managerworkers_with_different_agentic_components_can_be_validated() -> None:
    agent = Agent(
        name="manager_agent",
        system_prompt="You are a group manager.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )

    start_node = StartNode(name="start_node")
    end_node = EndNode(name="end_node")
    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="edge", from_node=start_node, to_node=end_node)
        ],
    )

    _ = ManagerWorkers(
        name="managerworkers",
        group_manager=agent,
        workers=[flow],
    )

    with pytest.raises(ValueError, match=("Group manager cannot be a worker")):
        ManagerWorkers(
            name="managerworkers",
            group_manager=agent,
            workers=[flow, agent],
        )


def test_managerworkers_with_ios_matching_the_group_manager_can_be_validated() -> None:
    manager_agent = Agent(
        name="manager_agent",
        system_prompt="Answer about {{topic}}.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
        outputs=[StringProperty(title="answer")],
    )
    worker_agent = Agent(
        name="worker_agent",
        system_prompt="You help.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )

    # The I/Os of a ManagerWorkers must be the I/Os of its group manager (same name
    # and type); redeclaring them explicitly is valid.
    _ = ManagerWorkers(
        name="managerworkers",
        group_manager=manager_agent,
        workers=[worker_agent],
        inputs=[StringProperty(title="topic")],
        outputs=[StringProperty(title="answer")],
    )


def test_managerworkers_with_ios_not_matching_the_group_manager_raises_errors() -> None:
    manager_agent = Agent(
        name="manager_agent",
        system_prompt="Answer about {{topic}}.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
        outputs=[StringProperty(title="answer")],
    )
    worker_agent = Agent(
        name="worker_agent",
        system_prompt="You help.",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )

    # Same title as a group manager input, but a different type.
    with pytest.raises(ValueError, match="must match the inputs of its group manager"):
        ManagerWorkers(
            name="managerworkers",
            group_manager=manager_agent,
            workers=[worker_agent],
            inputs=[FloatProperty(title="topic")],
        )

    # Same title as a group manager output, but a different type.
    with pytest.raises(ValueError, match="must match the outputs of its group manager"):
        ManagerWorkers(
            name="managerworkers",
            group_manager=manager_agent,
            workers=[worker_agent],
            outputs=[FloatProperty(title="answer")],
        )

    # A title the group manager does not declare is rejected by the base
    # ComponentWithIO validation.
    with pytest.raises(ValueError, match="expected only properties with the titles"):
        ManagerWorkers(
            name="managerworkers",
            group_manager=manager_agent,
            workers=[worker_agent],
            outputs=[StringProperty(title="answer"), StringProperty(title="extra")],
        )


def test_swarm_with_empty_relationships_raises_errors() -> None:
    first_agent = Agent(
        name="first_agent",
        system_prompt="Be Good!!",
        llm_config=OpenAiConfig(name="default", model_id="test_model"),
    )

    with pytest.raises(ValueError, match=("Cannot define a `Swarm` with no relationships")):
        Swarm(
            name="swarm",
            first_agent=first_agent,
            relationships=[],
        )
