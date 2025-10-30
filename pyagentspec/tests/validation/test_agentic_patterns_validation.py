# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
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
