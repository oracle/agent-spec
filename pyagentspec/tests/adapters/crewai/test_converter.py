# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import pytest
import yaml
from pydantic import BaseModel

from pyagentspec import Agent
from pyagentspec.llms import (
    LlmConfig,
    LlmGenerationConfig,
    OllamaConfig,
    OpenAiCompatibleConfig,
    OpenAiConfig,
)
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool

# mypy: ignore-errors


def mock_tool() -> str:
    return "CrewAI is a framework for building multi-agent applications."


def test_crewai_agent_can_be_converted_to_agentspec() -> None:

    from pyagentspec.adapters.crewai import AgentSpecExporter
    from pyagentspec.adapters.crewai._types import CrewAITool, crewai

    class MockToolSchema(BaseModel):
        pass

    crewai_mock_tool = CrewAITool(
        name="mock_tool",
        description="Mocked tool",
        args_schema=MockToolSchema,
        func=mock_tool,
    )

    agent = crewai.Agent(
        role="crew_ai_assistant",
        goal="Use tools to solve tasks.",
        backstory="You are a helpful assistant",
        llm=crewai.LLM(
            model="ollama/agi_model",
            base_url="url_to_my_agi_model",
            max_tokens=200,
        ),
        tools=[crewai_mock_tool],
    )

    exporter = AgentSpecExporter()
    agentspec_yaml = exporter.to_yaml(agent)
    agentspec_dict = yaml.safe_load(agentspec_yaml)
    assert "component_type" in agentspec_dict
    assert agentspec_dict["component_type"] == "Agent"
    assert agentspec_dict["name"] == "crew_ai_assistant"
    assert agentspec_dict["system_prompt"] == "Use tools to solve tasks."
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


@pytest.mark.parametrize(
    "llm_config",
    [
        OllamaConfig(
            name="agi_model",
            model_id="agi_model",
            url="url_to_my_agi_model",
            default_generation_parameters=LlmGenerationConfig(max_tokens=200),
        ),
        OpenAiCompatibleConfig(
            name="agi_model",
            model_id="agi_model",
            url="url_to_my_agi_model",
            default_generation_parameters=LlmGenerationConfig(temperature=200),
        ),
        OpenAiConfig(
            name="agi_model",
            model_id="agi_model",
            default_generation_parameters=LlmGenerationConfig(top_p=0.3),
        ),
    ],
)
def test_agentspec_agent_can_be_converted_to_crewai(llm_config: LlmConfig) -> None:
    from pyagentspec.adapters.crewai import AgentSpecLoader
    from pyagentspec.adapters.crewai._types import crewai

    agent = Agent(
        name="crew_ai_assistant",
        description="You are a helpful assistant",
        llm_config=llm_config,
        tools=[
            ServerTool(
                name="mock_tool_server", inputs=[], outputs=[StringProperty(title="output")]
            ),
            ClientTool(
                name="mock_tool_client",
                inputs=[StringProperty(title="input_2")],
                outputs=[StringProperty(title="output_2")],
            ),
            RemoteTool(
                name="mock_tool_remote",
                url="my.remote.server",
                http_method="GET",
                data={"in": "{{input_3}}"},
                inputs=[StringProperty(title="input_3")],
                outputs=[StringProperty(title="output_3")],
            ),
        ],
        system_prompt="Use tools to solve tasks.",
    )
    agentspec_yaml = AgentSpecSerializer().to_yaml(agent)

    crewai_assistant = AgentSpecLoader(tool_registry={"mock_tool_server": mock_tool}).load_yaml(
        agentspec_yaml
    )
    assert isinstance(crewai_assistant, crewai.Agent)
    assert crewai_assistant.role == "crew_ai_assistant"
    assert crewai_assistant.goal == "Use tools to solve tasks."
    assert crewai_assistant.backstory == "You are a helpful assistant"
    assert len(crewai_assistant.tools) == 3
    assert isinstance(crewai_assistant.llm, crewai.LLM)
