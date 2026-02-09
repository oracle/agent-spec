# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import cast

from pyagentspec.agent import Agent
from pyagentspec.llms.openaicompatibleconfig import OpenAiCompatibleConfig


def test_agent_framework_converts_to_agent_spec_with_server_tool() -> None:

    from agent_framework import ChatAgent, tool
    from agent_framework.openai import OpenAIChatClient

    from pyagentspec.adapters.agent_framework import AgentSpecExporter

    @tool(name="add_tool", description="Sum")
    def add_tool(a: int, b: int) -> int:
        return a + b

    agent = ChatAgent(
        chat_client=OpenAIChatClient(
            api_key="ollama",
            base_url="url.to.agi.model",
            model_id="agi_ollama_model",
        ),
        name="MathAgent",
        instructions="You are a helpful math agent",
        tools=add_tool,
        temperature=0.2,
        top_p=0.5,
        max_tokens=10000,
    )
    exporter = AgentSpecExporter()
    agent_component = cast(Agent, exporter.to_component(agent))
    # Agent config
    assert agent_component.name == agent.name
    assert agent_component.description == agent.description
    assert isinstance(agent_component.llm_config, OpenAiCompatibleConfig)
    assert isinstance(agent.chat_client, OpenAIChatClient)
    assert agent_component.system_prompt == agent.default_options["instructions"]

    # Llm Config
    assert agent_component.llm_config.url == agent.chat_client.service_url()
    assert agent_component.llm_config.model_id == agent.chat_client.model_id
    default_generation_parameters = agent_component.llm_config.default_generation_parameters
    assert default_generation_parameters is not None
    assert default_generation_parameters.temperature == agent.additional_properties["temperature"]
    assert default_generation_parameters.top_p == agent.additional_properties["top_p"]
    assert default_generation_parameters.max_tokens == agent.additional_properties["max_tokens"]

    # Tools
    assert len(agent_component.tools) == 1
    assert len(agent_component.tools) == len(agent.default_options["tools"])  # type: ignore
    add_tool_agentspec = agent_component.tools[0]
    assert add_tool_agentspec.name == agent.default_options["tools"][0].name  # type: ignore
    assert add_tool_agentspec.inputs and len(add_tool_agentspec.inputs) == 2
    assert add_tool_agentspec.outputs and len(add_tool_agentspec.outputs) == 1
    input_json_schemas = [i.json_schema for i in add_tool_agentspec.inputs]
    output_json_schema = add_tool_agentspec.outputs[0].json_schema
    assert "a" in (schema["title"] for schema in input_json_schemas)
    assert "b" in (schema["title"] for schema in input_json_schemas)
    assert all(schema["type"] == "integer" for schema in input_json_schemas)
    assert output_json_schema["title"] == "result" and output_json_schema["type"] == "integer"
