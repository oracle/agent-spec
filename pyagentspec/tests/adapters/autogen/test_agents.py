# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
from pathlib import Path

from pyagentspec.agent import Agent as AgentSpecAgent

from ..conftest import _replace_config_placeholders

CONFIGS = Path(__file__).parent / "configs"


def test_autogen_agent_can_be_converted_to_agentspec() -> None:

    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.ollama import OllamaChatCompletionClient

    from pyagentspec.adapters.autogen import AgentSpecExporter

    async def mock_tool() -> str:
        return "AutoGen is a programming framework for building multi-agent applications."

    # Create an agent that uses the llama 3.2 model.
    model_client = OllamaChatCompletionClient(
        model="llama3.2:latest",
        host="localhost:11434",
    )

    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[mock_tool],
        system_message="Use tools to solve tasks.",
    )

    exporter = AgentSpecExporter()
    component = exporter.to_component(agent)
    assert isinstance(component, AgentSpecAgent)
    assert component.name == agent.name
    assert agent._system_messages[0].content in component.system_prompt
    assert len(component.tools) == 1
    assert component.tools[0].name == mock_tool.__name__


def test_autogen_agent_with_2_tools_can_be_converted_to_agentspec() -> None:

    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.ollama import OllamaChatCompletionClient

    from pyagentspec.adapters.autogen import AgentSpecExporter

    async def get_weather(city: str) -> str:
        """Get the weather for a given city."""
        return f"The weather in {city} is 30 degrees and Sunny."

    async def get_capital(country: str) -> str:
        """Get the capital for a given country."""
        return f"The capital of {country} is Rabat."

    model_client = OllamaChatCompletionClient(
        model="llama3.2:latest",
        host="localhost:11434",
    )

    agent = AssistantAgent(
        name="autogen_assistant",
        model_client=model_client,
        tools=[get_weather, get_capital],
        system_message="Use tools to solve tasks.",
    )

    exporter = AgentSpecExporter()
    agentspec_component = exporter.to_component(agent)
    assert isinstance(agentspec_component, AgentSpecAgent)
    assert agentspec_component.name == agent.name
    assert agent._system_messages[0].content in agentspec_component.system_prompt
    assert len(agentspec_component.tools) == 2
    assert agentspec_component.tools[0].name == get_weather.__name__
    assert agentspec_component.tools[1].name == get_capital.__name__


def test_remote_tool_with_agent(json_server: str) -> None:
    from pyagentspec.adapters.autogen import AgentSpecLoader

    async def test_func():
        yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
        replaced_content = _replace_config_placeholders(yaml_content, json_server)
        agent = AgentSpecLoader().load_yaml(replaced_content)

        result = await agent.run(task="What is the weather like in Agadir?")
        message = result.messages[-1]
        assert "agadir" in message.content.lower()
        assert "sunny" in message.content.lower()

    asyncio.run(test_func())
