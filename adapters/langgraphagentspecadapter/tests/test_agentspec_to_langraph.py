# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from unittest import mock

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from langgraph_agentspec_adapter import AgentSpecLoader

from .conftest import (
    IS_JSON_SERVER_RUNNING,
    JSON_SERVER_PORT,
    get_weather,
)


def test_weather_agent_with_server_tool(weather_agent_server_tool_yaml: str) -> None:
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_server_tool_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]},
        config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    tool_call_message = result["messages"][-2]
    assert isinstance(tool_call_message, ToolMessage)


def test_weather_agent_with_server_tool_ollama(weather_ollama_agent_yaml: str) -> None:
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_ollama_agent_yaml
    )
    assert isinstance(agent, CompiledStateGraph)


def test_weather_agent_with_server_tool_with_output_descriptors(
    weather_agent_with_outputs_yaml: str,
) -> None:
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_with_outputs_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]},
        config,
    )
    last_message = result["structured_response"]
    assert isinstance(last_message.temperature_rating, int)
    assert isinstance(last_message.weather, str)


def test_client_tool_with_agent(weather_agent_client_tool_yaml: str) -> None:
    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_yaml(weather_agent_client_tool_yaml)
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]}
    agent.invoke(
        messages,
        config,
    )
    result = agent.invoke(
        input=Command(resume={"weather": "sunny"}),
        config=config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    assert all(x in last_message.content.lower() for x in ("agadir", "sunny"))


def test_client_tool_with_two_inputs(ancestry_agent_with_client_tool_yaml: str) -> None:
    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_yaml(
        ancestry_agent_with_client_tool_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "Who's the son of Tim and Dorothy"}]}
    agent.invoke(
        messages,
        config,
    )
    result = agent.invoke(
        input=Command(resume={"son": "himothy"}),
        config=config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    assert "himothy" in last_message.content.lower()


@pytest.mark.skipif(
    not IS_JSON_SERVER_RUNNING, reason="Skipping test because json server is not running"
)
def test_remote_tool_with_agent(json_server, weather_agent_remote_tool_yaml: str) -> None:
    yaml_content = weather_agent_remote_tool_yaml
    agent = AgentSpecLoader().load_yaml(
        yaml_content.replace("[[remote_tools_server]]", f"http://localhost:{JSON_SERVER_PORT}")
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]}
    result = agent.invoke(
        messages,
        config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    assert all(x in last_message.content.lower() for x in ("agadir", "sunny"))


@pytest.fixture()
def weather_agent_server_tool_openaicompatible_yaml(weather_agent_server_tool_yaml: str) -> str:
    return weather_agent_server_tool_yaml.replace(
        "component_type: VllmConfig", "component_type: OpenAiCompatibleConfig"
    )


def test_weather_agent_with_server_tool_with_openaicompatible_llm_raises_without_api_key(
    weather_agent_server_tool_openaicompatible_yaml: str,
) -> None:
    """
    This test is checking the case of OpenAiCompatibleConfig.
    The VllmConfig is already tested in all the tests above
    """
    import openai

    with pytest.raises(
        openai.OpenAIError,
        match="The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable",
    ):
        AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
            weather_agent_server_tool_openaicompatible_yaml
        )


@mock.patch.dict(os.environ, {"OPENAI_API_KEY": "MOCKED_KEY"})
def test_execute_weather_agent_with_server_tool_with_openaicompatible_llm(
    weather_agent_server_tool_openaicompatible_yaml: str,
) -> None:
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_server_tool_openaicompatible_yaml
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]},
        config,
    )
    last_message = result["messages"][-1]
    assert last_message.type == "ai"
    tool_call_message = result["messages"][-2]
    assert isinstance(tool_call_message, ToolMessage)
