# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

import yaml
from crewai import LLM as CrewAILlm
from crewai import Agent as CrewAIAgent
from crewai.tools.base_tool import Tool as CrewAIServerTool
from crewai_agentspec_adapter import AgentSpecExporter, AgentSpecLoader
from pydantic import BaseModel

from pyagentspec import Agent
from pyagentspec.llms import LlmGenerationConfig, OllamaConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ServerTool


def mock_tool() -> str:
    return "CrewAI is a framework for building multi-agent applications."


def test_crewai_agent_can_be_converted_to_agentspec() -> None:

    class MockToolSchema(BaseModel):
        pass

    crewai_mock_tool = CrewAIServerTool(
        name="mock_tool",
        description="Mocked tool",
        args_schema=MockToolSchema,
        func=mock_tool,
    )

    agent = CrewAIAgent(
        role="crew_ai_assistant",
        goal="Use tools to solve tasks.",
        backstory="You are a helpful assistant",
        llm=CrewAILlm(
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


def test_agentspec_agent_can_be_converted_to_crewai() -> None:

    agent = Agent(
        name="crew_ai_assistant",
        description="You are a helpful assistant",
        llm_config=OllamaConfig(
            name="agi_model",
            model_id="agi_model",
            url="url_to_my_agi_model",
            default_generation_parameters=LlmGenerationConfig(max_tokens=200),
        ),
        tools=[
            ServerTool(name="mock_tool", inputs=[], outputs=[StringProperty(title="mock_tool")])
        ],
        system_prompt="Use tools to solve tasks.",
    )
    agentspec_yaml = AgentSpecSerializer().to_yaml(agent)

    crewai_assistant = AgentSpecLoader(tool_registry={"mock_tool": mock_tool}).load_yaml(
        agentspec_yaml
    )
    assert isinstance(crewai_assistant, CrewAIAgent)
    assert crewai_assistant.role == "crew_ai_assistant"
    assert crewai_assistant.goal == "Use tools to solve tasks."
    assert crewai_assistant.backstory == "You are a helpful assistant"
    assert len(crewai_assistant.tools) == 1
    assert isinstance(crewai_assistant.llm, CrewAILlm)
