# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.node import Node
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.llms import LlmConfig
from pyagentspec.llms.openaiconfig import OpenAiConfig
from pyagentspec.managerworkers import ManagerWorkers
from pyagentspec.property import IntegerProperty, StringProperty
from pyagentspec.swarm import Swarm
from pyagentspec.tools import ServerTool, Tool


@pytest.fixture
def dummy_llm_config() -> LlmConfig:
    return OpenAiConfig(name="openai", model_id="gpt-test")


@pytest.fixture
def dummy_agent(dummy_llm_config: LlmConfig) -> Agent:
    return Agent(name="agent", llm_config=dummy_llm_config, system_prompt="Hello")


@pytest.fixture
def dummy_tool() -> Tool:
    return ServerTool(
        name="servertool",
        inputs=[IntegerProperty(title="x")],
        outputs=[IntegerProperty(title="y")],
    )


@pytest.fixture
def dummy_flow(dummy_llm_config: LlmConfig) -> Flow:
    prompt_prop = StringProperty(title="prompt")
    llm_out_prop = StringProperty(title="generated_text")
    start_node = StartNode(name="start", inputs=[prompt_prop])
    llm_node = LlmNode(
        name="llm",
        llm_config=dummy_llm_config,
        prompt_template="{{prompt}}",
        inputs=[prompt_prop],
        outputs=[llm_out_prop],
    )
    end_node = EndNode(name="end", outputs=[llm_out_prop])
    control_flow_edges = [
        ControlFlowEdge(name="s_to_llm", from_node=start_node, to_node=llm_node),
        ControlFlowEdge(name="llm_to_e", from_node=llm_node, to_node=end_node),
    ]
    data_flow_edges = [
        DataFlowEdge(
            name="prompt_edge",
            source_node=start_node,
            source_output="prompt",
            destination_node=llm_node,
            destination_input="prompt",
        ),
        DataFlowEdge(
            name="out_edge",
            source_node=llm_node,
            source_output="generated_text",
            destination_node=end_node,
            destination_input="generated_text",
        ),
    ]
    return Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, llm_node, end_node],
        control_flow_connections=control_flow_edges,
        data_flow_connections=data_flow_edges,
    )


@pytest.fixture
def dummy_node(dummy_llm_config: LlmConfig) -> Node:
    return LlmNode(
        name="llm_node",
        llm_config=dummy_llm_config,
        prompt_template="{{prompt}}",
        inputs=[StringProperty(title="prompt")],
        outputs=[StringProperty(title="generated_text")],
    )


@pytest.fixture
def dummy_managerworkers(dummy_llm_config: LlmConfig) -> ManagerWorkers:
    mgr = Agent(name="manager", llm_config=dummy_llm_config, system_prompt="You are a manager")
    w1 = Agent(name="worker", llm_config=dummy_llm_config, system_prompt="You are a worker")
    return ManagerWorkers(name="mw", group_manager=mgr, workers=[w1])


@pytest.fixture
def dummy_swarm(dummy_llm_config: LlmConfig) -> Swarm:
    a1 = Agent(name="a1", llm_config=dummy_llm_config, system_prompt="You are a1")
    a2 = Agent(name="a2", llm_config=dummy_llm_config, system_prompt="You are a2")
    return Swarm(name="sw", first_agent=a1, relationships=[(a1, a2)])
