# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest
import yaml

from pyagentspec import Agent
from pyagentspec.llms import OpenAiConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ServerTool


def test_openai_agent_can_be_converted_to_agentspec() -> None:

    from pyagentspec.adapters.openaiagents import AgentSpecExporter
    from pyagentspec.adapters.openaiagents._types import OAAgent, function_tool

    @function_tool
    def get_weather(city: str) -> str:
        """Return weather for a city."""
        return f"Sunny in {city}"

    oa_agent = OAAgent(
        name="assistant",
        instructions="You are a helpful assistant.",
        model="gpt-4.1",
        tools=[get_weather],
    )

    exporter = AgentSpecExporter()
    agentspec_yaml = exporter.to_yaml(oa_agent)
    agentspec_dict = yaml.safe_load(agentspec_yaml)

    # Top-level
    assert "component_type" in agentspec_dict
    assert agentspec_dict["component_type"] == "Agent"
    assert agentspec_dict["name"] == "assistant"
    assert agentspec_dict["system_prompt"] == "You are a helpful assistant."

    # LLM
    assert "llm_config" in agentspec_dict
    assert "component_type" in agentspec_dict["llm_config"]
    assert agentspec_dict["llm_config"]["component_type"] == "OpenAiConfig"
    assert agentspec_dict["llm_config"]["model_id"] == "gpt-4.1"

    # Tools
    assert "tools" in agentspec_dict
    assert isinstance(agentspec_dict["tools"], list)
    assert len(agentspec_dict["tools"]) == 1
    tool0 = agentspec_dict["tools"][0]
    assert tool0["component_type"] == "ServerTool"
    assert tool0["name"] == "get_weather"


async def _mock_tool(city: str) -> str:
    return f"Sunny in {city}"


def test_agentspec_agent_can_be_converted_to_openai() -> None:

    from pyagentspec.adapters.openaiagents import AgentSpecLoader
    from pyagentspec.adapters.openaiagents._types import OAAgent

    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiConfig(name="gpt-4.1", model_id="gpt-4.1"),
        tools=[
            ServerTool(
                name="get_weather",
                inputs=[StringProperty(title="city")],
                outputs=[StringProperty(title="result")],
            )
        ],
        system_prompt="You are a helpful assistant.",
    )

    agentspec_yaml = AgentSpecSerializer().to_yaml(agentspec_agent)

    loader = AgentSpecLoader(tool_registry={"get_weather": _mock_tool})
    oa_agent = loader.load_yaml(agentspec_yaml)

    assert isinstance(oa_agent, OAAgent)
    assert oa_agent.name == "assistant"
    assert oa_agent.instructions == "You are a helpful assistant."
    assert isinstance(oa_agent.tools, list)
    assert len(oa_agent.tools) == 1


def test_missing_server_tool_raises() -> None:

    from pyagentspec.adapters.openaiagents import AgentSpecLoader

    agentspec_agent = Agent(
        name="assistant",
        llm_config=OpenAiConfig(name="gpt-4.1", model_id="gpt-4.1"),
        tools=[
            ServerTool(
                name="get_weather",
                inputs=[StringProperty(title="city")],
                outputs=[StringProperty(title="result")],
            )
        ],
        system_prompt="You are a helpful assistant.",
    )
    agentspec_yaml = AgentSpecSerializer().to_yaml(agentspec_agent)

    loader = AgentSpecLoader(tool_registry={})
    with pytest.raises(ValueError) as excinfo:
        loader.load_yaml(agentspec_yaml)
    assert "ServerTool" in str(excinfo.value)
