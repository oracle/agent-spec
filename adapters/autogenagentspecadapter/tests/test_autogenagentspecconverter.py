# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import asyncio
import os
from pathlib import Path

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import ToolCallSummaryMessage
from autogen_agentspec_adapter import AgentSpecExporter, AgentSpecLoader
from autogen_ext.models.ollama import OllamaChatCompletionClient

from pyagentspec.agent import Agent as AgentSpecAgent

from .conftest import IS_JSON_SERVER_RUNNING, JSON_SERVER_PORT

CONFIGS = Path(__file__).parent / "configs"


def test_autogen_agent_can_be_converted_to_agentspec() -> None:
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
    assert component.system_prompt == agent._system_messages[0].content
    assert len(component.tools) == 1
    assert component.tools[0].name == mock_tool.__name__


@pytest.mark.skipif(
    not IS_JSON_SERVER_RUNNING, reason="Skipping test because json server is not running"
)
def test_remote_tool_with_agent(json_server) -> None:
    async def test_func():
        yaml_content = (CONFIGS / "weather_agent_remote_tool.yaml").read_text()
        agent = AgentSpecLoader().load_yaml(
            yaml_content.replace(
                "[[remote_tools_server]]", f"http://localhost:{JSON_SERVER_PORT}"
            ).replace("[[LLAMA_API_URL]]", os.environ.get("LLAMA_API_URL"))
        )

        result = await agent.run(task="What is the weather like in Agadir?")
        message = result.messages[-1]
        assert isinstance(message, ToolCallSummaryMessage)
        assert "city" in message.tool_calls[0].arguments
        assert "Agadir" in message.tool_calls[0].arguments
        assert message.results[-1].content == str({"weather": "sunny"})

    asyncio.run(test_func())
