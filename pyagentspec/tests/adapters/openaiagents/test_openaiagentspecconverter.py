# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.


import pytest
import yaml

from pyagentspec.adapters.openaiagents import AgentSpecExporter


def test_export_rejects_non_string_instructions() -> None:
    from agents.agent import Agent as OAAgent

    def dyn_instructions(ctx, agent):
        return "dynamic"

    oa_agent = OAAgent(name="assistant", instructions=dyn_instructions, model="gpt-4.1", tools=[])
    exporter = AgentSpecExporter()
    with pytest.raises(NotImplementedError):
        exporter.to_yaml(oa_agent)


def test_export_function_tool_to_server_tool() -> None:
    from agents.agent import Agent as OAAgent
    from agents.tool import function_tool

    @function_tool
    def echo(text: str) -> str:
        """Echo text."""
        return text

    oa_agent = OAAgent(
        name="assistant",
        instructions="You are a helpful assistant.",
        model="gpt-4.1",
        tools=[echo],
    )
    exporter = AgentSpecExporter()
    data = yaml.safe_load(exporter.to_yaml(oa_agent))

    assert data["component_type"] == "Agent"
    assert data["llm_config"]["component_type"] == "OpenAiConfig"
    assert len(data["tools"]) == 1
    assert data["tools"][0]["component_type"] == "ServerTool"
    assert data["tools"][0]["name"] == "echo"


def test_export_hosted_tool_to_remote_tool_stub() -> None:
    from agents.agent import Agent as OAAgent
    from agents.tool import WebSearchTool as OAWebSearchTool

    hosted = OAWebSearchTool()
    oa_agent = OAAgent(
        name="assistant",
        instructions="Use tools to help.",
        model="gpt-4.1",
        tools=[hosted],
    )
    exporter = AgentSpecExporter()
    data = yaml.safe_load(exporter.to_yaml(oa_agent))

    assert data["component_type"] == "Agent"
    assert len(data["tools"]) == 1
    tool0 = data["tools"][0]
    assert tool0["component_type"] == "RemoteTool"
    assert tool0["name"] == "web_search"
    assert tool0["url"] == "openai://hosted/web_search"
    assert tool0["http_method"] == "POST"
