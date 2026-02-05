# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# mypy: ignore-errors

import yaml

from pyagentspec import Agent
from pyagentspec.llms import OllamaConfig
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools import ServerTool


def mock_tool() -> str:
    """Mocked tool"""
    return "LangGraph is a framework for building agentic applications."


def test_langgraph_agent_can_be_converted_to_agentspec() -> None:
    from langchain.agents import create_agent
    from langchain_ollama import ChatOllama

    from pyagentspec.adapters.langgraph import AgentSpecExporter

    model = ChatOllama(
        model="agi_model",
        base_url=f"http://url_to_my_agi_model/v1",
    )
    agent = create_agent(
        name="langgraph_assistant",
        model=model,
        system_prompt="Use tools to solve tasks.",
        tools=[mock_tool],
    )

    exporter = AgentSpecExporter()
    agentspec_yaml = exporter.to_yaml(agent)
    agentspec_dict = yaml.safe_load(agentspec_yaml)
    assert "component_type" in agentspec_dict
    assert agentspec_dict["component_type"] == "Agent"
    assert agentspec_dict["name"] == "langgraph_assistant"
    # We cannot retrieve the system prompt properly yet
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


def test_agentspec_agent_can_be_converted_to_langgraph() -> None:

    from langgraph.graph.state import CompiledStateGraph

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = Agent(
        name="langgraph_assistant",
        description="You are a helpful assistant",
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

    langgraph_assistant = AgentSpecLoader(tool_registry={"mock_tool": mock_tool}).load_yaml(
        agentspec_yaml
    )
    assert isinstance(langgraph_assistant, CompiledStateGraph)
    assert langgraph_assistant.get_name() == "langgraph_assistant"
