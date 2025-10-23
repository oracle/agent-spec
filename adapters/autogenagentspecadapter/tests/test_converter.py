# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentspec_adapter import AgentSpecExporter, AgentSpecLoader
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.ollama import OllamaChatCompletionClient

from pyagentspec import Agent
from pyagentspec.llms import OllamaConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ServerTool


async def mock_tool() -> str:
    return "AutoGen is a framework for building multi-agent applications."


def test_autogen_agent_can_be_converted_to_agentspec() -> None:

    agent = AssistantAgent(
        name="autogen_assistant",
        model_client=OllamaChatCompletionClient(
            model="agi_model",
            host="url_to_my_agi_model",
            model_info=ModelInfo(
                vision=True,
                function_calling=True,
                json_output=True,
                family=ModelFamily.UNKNOWN,
                structured_output=True,
            ),
        ),
        tools=[mock_tool],
        system_message="Use tools to solve tasks.",
    )

    exporter = AgentSpecExporter()
    agentspec_yaml = exporter.to_yaml(agent)
    agentspec_dict = yaml.safe_load(agentspec_yaml)
    assert "component_type" in agentspec_dict
    assert agentspec_dict["component_type"] == "Agent"
    assert agentspec_dict["name"] == "autogen_assistant"
    assert agent._system_messages[0].content in agentspec_dict["system_prompt"]
    # Check LLM
    assert "llm_config" in agentspec_dict
    assert "component_type" in agentspec_dict["llm_config"]
    assert agentspec_dict["llm_config"]["component_type"] == "OllamaConfig"
    # Check Tools
    assert "tools" in agentspec_dict
    assert isinstance(agentspec_dict["tools"], list)
    assert len(agentspec_dict["tools"]) == 1
    assert "component_type" in agentspec_dict["tools"][0]
    assert agentspec_dict["tools"][0]["component_type"] == "ServerTool"
    assert agentspec_dict["tools"][0]["name"] == "mock_tool"


def test_agentspec_agent_can_be_converted_to_autogen() -> None:

    agent = Agent(
        name="autogen_assistant",
        llm_config=OllamaConfig(
            name="agi_model",
            model_id="agi_model",
            url="url_to_my_agi_model",
        ),
        tools=[
            ServerTool(name="mock_tool", inputs=[], outputs=[StringProperty(title="mock_tool")])
        ],
        system_prompt="Use tools to solve tasks.",
    )
    agentspec_yaml = AgentSpecSerializer().to_yaml(agent)

    autogen_assistant = AgentSpecLoader(tool_registry={"mock_tool": mock_tool}).load_yaml(
        agentspec_yaml
    )
    assert isinstance(autogen_assistant, AssistantAgent)
    assert autogen_assistant.name == "autogen_assistant"
    assert autogen_assistant._system_messages[0].content == "Use tools to solve tasks."
    assert len(autogen_assistant._tools) == 1
    assert isinstance(autogen_assistant._model_client, OllamaChatCompletionClient)
