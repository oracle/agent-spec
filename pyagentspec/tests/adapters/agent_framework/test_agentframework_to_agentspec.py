# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import cast

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType, OpenAiCompatibleConfig


def test_agent_framework_converts_to_agent_spec_with_server_tool() -> None:

    from agent_framework import Agent, tool
    from agent_framework.openai import OpenAIChatCompletionClient

    from pyagentspec.adapters.agent_framework import AgentSpecExporter

    @tool(name="add_tool", description="Sum")
    def add_tool(a: int, b: int) -> int:
        return a + b

    agent = Agent(
        client=OpenAIChatCompletionClient(
            api_key="ollama",
            base_url="url.to.agi.model",
            model="agi_ollama_model",
        ),
        name="MathAgent",
        instructions="You are a helpful math agent",
        tools=add_tool,
        additional_properties=dict(
            temperature=0.2,
            top_p=0.5,
            max_tokens=10000,
        ),
    )
    exporter = AgentSpecExporter()
    agent_component = cast(AgentSpecAgent, exporter.to_component(agent))
    # Agent config
    assert agent_component.name == agent.name
    assert agent_component.description == agent.description
    assert isinstance(agent_component.llm_config, OpenAiCompatibleConfig)
    assert agent_component.llm_config.api_type == OpenAIAPIType.CHAT_COMPLETIONS
    assert isinstance(agent.client, OpenAIChatCompletionClient)
    assert agent_component.system_prompt == agent.default_options["instructions"]

    # Llm Config
    assert agent_component.llm_config.url == agent.client.service_url()
    assert agent_component.llm_config.model_id == agent.client.model
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


def test_agent_framework_responses_client_converts_to_agent_spec() -> None:
    from agent_framework import Agent
    from agent_framework.openai import OpenAIChatClient

    from pyagentspec.adapters.agent_framework import AgentSpecExporter

    agent = Agent(
        client=OpenAIChatClient(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="gpt-test",
        ),
        name="ResponsesAgent",
        instructions="Be helpful.",
    )

    agent_component = cast(AgentSpecAgent, AgentSpecExporter().to_component(agent))

    assert isinstance(agent_component.llm_config, OpenAiCompatibleConfig)
    assert agent_component.llm_config.api_type == OpenAIAPIType.RESPONSES
    assert agent_component.llm_config.model_id == agent.client.model
