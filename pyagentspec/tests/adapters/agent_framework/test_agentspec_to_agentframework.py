# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import anyio
import pytest

from pyagentspec.agent import Agent as AgentSpecAgent
from pyagentspec.llms import LlmConfig
from pyagentspec.llms.openaicompatibleconfig import OpenAIAPIType, OpenAiCompatibleConfig
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.serialization import AgentSpecDeserializer

from .conftest import get_weather


@pytest.mark.parametrize(
    ("api_type", "expected_client_name"),
    [
        (OpenAIAPIType.CHAT_COMPLETIONS, "OpenAIChatCompletionClient"),
        (OpenAIAPIType.RESPONSES, "OpenAIChatClient"),
    ],
)
def test_agentspec_api_type_selects_agent_framework_client(
    api_type: OpenAIAPIType, expected_client_name: str
) -> None:
    from agent_framework.openai import OpenAIChatClient, OpenAIChatCompletionClient

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    client = AgentSpecLoader().load_component(
        OpenAiCompatibleConfig(
            name="test-model",
            model_id="test-model",
            url="http://test.example/v1",
            api_type=api_type,
        )
    )

    expected_client = {
        "OpenAIChatClient": OpenAIChatClient,
        "OpenAIChatCompletionClient": OpenAIChatCompletionClient,
    }[expected_client_name]
    assert isinstance(client, expected_client)


@pytest.mark.parametrize(
    ("api_type", "expected_client_name"),
    [
        ("chat_completions", "OpenAIChatCompletionClient"),
        ("responses", "OpenAIChatClient"),
    ],
)
def test_bare_llmconfig_api_type_selects_agent_framework_client(
    api_type: str, expected_client_name: str
) -> None:
    from agent_framework.openai import OpenAIChatClient, OpenAIChatCompletionClient

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    client = AgentSpecLoader().load_component(
        LlmConfig(
            name="test-model",
            model_id="test-model",
            api_provider="openai",
            api_type=api_type,
            url="http://test.example/v1",
        )
    )

    expected_client = {
        "OpenAIChatClient": OpenAIChatClient,
        "OpenAIChatCompletionClient": OpenAIChatCompletionClient,
    }[expected_client_name]
    assert isinstance(client, expected_client)


def test_agentspec_converts_to_agent_framework_with_server_tool(
    weather_agent_server_tool: str,
) -> None:

    from agent_framework import Agent, FunctionTool
    from agent_framework.openai import OpenAIChatCompletionClient

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent_component = AgentSpecDeserializer().from_yaml(weather_agent_server_tool)
    assert isinstance(agent_component, AgentSpecAgent)
    loader = AgentSpecLoader(tool_registry={"get_weather": get_weather})
    agent = loader.load_yaml(weather_agent_server_tool)
    assert isinstance(agent, Agent)

    # Agent Config
    assert agent_component.name == agent.name
    assert agent_component.description == agent.description
    assert agent_component.system_prompt == agent.default_options["instructions"]

    # Llm Config
    assert isinstance(agent_component.llm_config, VllmConfig)
    assert isinstance(agent.client, OpenAIChatCompletionClient)
    assert agent_component.llm_config.url in agent.client.service_url()
    assert agent_component.llm_config.model_id == agent.client.model
    default_generation_parameters = agent_component.llm_config.default_generation_parameters
    assert default_generation_parameters is not None
    assert default_generation_parameters.temperature == agent.additional_properties["temperature"]
    assert default_generation_parameters.top_p == agent.additional_properties["top_p"]
    assert default_generation_parameters.max_tokens == agent.additional_properties["max_tokens"]

    # Tools
    assert len(agent_component.tools) == 1
    assert len(agent_component.tools) == len(agent.default_options["tools"])  # type: ignore
    assert agent_component.tools[0].name == agent.default_options["tools"][0].name  # type: ignore
    tool = agent.default_options["tools"][0]  # type: ignore
    assert isinstance(tool, FunctionTool)
    tool_schema = tool.input_model.model_json_schema()
    assert "properties" in tool_schema and "city" in tool_schema["properties"]


def test_agent_with_server_tool_runs_after_config_load(weather_agent_server_tool: str) -> None:

    from agent_framework import Agent

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    loader = AgentSpecLoader(tool_registry={"get_weather": get_weather})
    agent = loader.load_yaml(weather_agent_server_tool)
    assert isinstance(agent, Agent)
    result = anyio.run(agent.run, "What is the weather like in Agadir?")
    contents = result.messages[-1].contents
    assert len(contents) > 0


def test_remote_tool_with_agent(weather_agent_remote_tool: str) -> None:

    from agent_framework import Agent

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent = AgentSpecLoader().load_yaml(weather_agent_remote_tool)
    assert isinstance(agent, Agent)

    result = anyio.run(agent.run, "What is the weather like in Agadir?")
    contents = result.messages[-1].contents
    assert len(contents) > 0
    last_content = contents[-1]
    assert all(x in last_content.text.lower() for x in ("agadir", "sunny"))


def test_server_tool_requires_confirmation_with_agent(
    weather_agent_server_tool_confirmation: str,
) -> None:

    from agent_framework import Agent, FunctionTool, Message

    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    loader = AgentSpecLoader(tool_registry={"get_weather": get_weather})
    agent = loader.load_yaml(weather_agent_server_tool_confirmation)
    assert isinstance(agent, Agent)

    # Ensure approval mode is set to always_require for the converted tool
    tools = agent.default_options["tools"] or []
    assert len(tools) == 1
    t = tools[0]
    assert isinstance(t, FunctionTool)
    assert t.approval_mode == "always_require"

    async def run_agent_with_confirmation(agent):
        # First run should request user approval for the function call
        first_result = await agent.run("What is the weather like in Agadir?")
        assert (
            first_result.user_input_requests
        ), "Expected a user approval request before tool execution"
        req = first_result.user_input_requests[0]
        # Verify it is asking to call the expected tool
        assert getattr(req.function_call, "name", "") == "get_weather"

        # Now add a single approval response and continue
        final_result = await agent.run(
            [
                "What is the weather like in Agadir?",
                Message(role="assistant", contents=[req]),
                Message(role="user", contents=[req.to_function_approval_response(True)]),
            ],
        )
        contents = final_result.messages[-1].contents
        assert len(contents) > 0
        last_content = contents[-1]
        assert all(x in last_content.text.lower() for x in ("agadir", "sunny"))

    anyio.run(run_agent_with_confirmation, agent)
