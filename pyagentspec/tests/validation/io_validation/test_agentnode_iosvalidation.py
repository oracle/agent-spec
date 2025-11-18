# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.flows.nodes.agentnode import AgentNode
from pyagentspec.llms.llmconfig import LlmConfig
from pyagentspec.property import (
    FloatProperty,
    IntegerProperty,
    ListProperty,
    NullProperty,
    StringProperty,
)


@pytest.fixture
def agent(default_llm_config: LlmConfig) -> Agent:
    input_1 = StringProperty(title="input_1")
    input_2 = NullProperty(title="input_2")
    output_1 = ListProperty(title="output_1", item_type=IntegerProperty())
    output_2 = FloatProperty(title="output_2")
    agent = Agent(
        name="test_agent",
        llm_config=default_llm_config,
        system_prompt="Do what makes you happy! {{input_1}} {{input_2}}",
        inputs=[input_1, input_2],
        outputs=[output_1, output_2],
    )
    return agent


def test_agent_node_has_same_ios_as_agent_by_default(agent: Agent) -> None:
    input_1 = StringProperty(title="input_1")
    input_2 = NullProperty(title="input_2")
    output_1 = ListProperty(title="output_1", item_type=IntegerProperty())
    output_2 = FloatProperty(title="output_2")
    agent_node = AgentNode(name="test_agent_node", agent=agent)
    assert agent_node.inputs == [input_1, input_2]
    assert agent_node.outputs == [output_1, output_2]


def test_agent_node_raises_if_inputs_with_incorrect_names(agent: Agent) -> None:
    input_1 = StringProperty(title="BADLY_NAMED_input_1")
    input_2 = NullProperty(title="input_2")
    with pytest.raises(ValueError, match="BADLY_NAMED_input_1"):
        AgentNode(
            name="test_agent_node",
            agent=agent,
            inputs=[input_1, input_2],
        )


def test_agent_node_raises_if_outputs_with_incorrect_names(agent: Agent) -> None:
    output_1 = ListProperty(title="output_1", item_type=IntegerProperty())
    output_2 = FloatProperty(title="BADLY_NAMED_output_2")
    with pytest.raises(ValueError, match="BADLY_NAMED_output_2"):
        AgentNode(
            name="test_agent_node",
            agent=agent,
            outputs=[output_1, output_2],
        )


# TODO test_agent_node_raises_if_ios_with_incompatible_types
# TODO test_agent_node_accepts_ios_with_castable_types
