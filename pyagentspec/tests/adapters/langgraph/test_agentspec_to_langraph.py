# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os
from unittest import mock

import pytest

from ..conftest import _replace_config_placeholders
from .conftest import get_weather


def test_weather_agent_with_server_tool(weather_agent_server_tool_yaml: str) -> None:
    from langchain_core.messages import ToolMessage
    from langchain_core.runnables import RunnableConfig

    from pyagentspec.adapters.langgraph import AgentSpecLoader

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
    from langgraph.graph.state import CompiledStateGraph

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_ollama_agent_yaml
    )
    assert isinstance(agent, CompiledStateGraph)


def test_weather_agent_with_server_tool_with_output_descriptors(
    weather_agent_with_outputs_yaml: str,
) -> None:
    from langchain_core.runnables import RunnableConfig

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
        weather_agent_with_outputs_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What is the weather like in Agadir?"}]},
        config,
    )
    last_message = dict(result["structured_response"])
    assert isinstance(last_message["temperature_rating"], int)
    assert isinstance(last_message["weather"], str)


def test_client_tool_with_agent(weather_agent_client_tool_yaml: str) -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

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
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader(checkpointer=MemorySaver()).load_yaml(
        ancestry_agent_with_client_tool_yaml
    )
    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = {"messages": [{"role": "user", "content": "Who's the son of Tim and Dorothy?"}]}
    agent.invoke(
        messages,
        config,
    )
    result = agent.invoke(
        input=Command(resume={"son": "himothy"}),
        config=config,
    )
    messages = result["messages"]
    last_message = messages[-1]

    # Ensure the client tool ToolMessage carrying resume inputs exists and includes "himothy"
    get_child_msgs = [m for m in messages if m.type == "tool" and m.name == "get_child"]
    assert get_child_msgs, "Expected a ToolMessage from client tool 'get_child'"
    assert "himothy" in str(get_child_msgs[0].content).lower()

    # ancestry_agent_with_client_tool_yaml is an agent with outputs and with a client tool with outputs
    # With latest langchain, agents with outputs may be emitted either as:
    # - a ToolMessage created from a structured-output tool (ToolStrategy path), or
    # - an AIMessage with a structured-output tool_call (ProviderStrategy path).
    # - the langgraph adapter defaults to ToolStrategy, but the agent may fail to generate the AgentOutputModel tool call
    # - so it may try to re-generate the tool call (last_message being of type "AIMessage")
    structured_tool_msgs = [
        m for m in messages if m.type == "tool" and m.name == "AgentOutputModel"
    ]
    if structured_tool_msgs:
        assert structured_tool_msgs[-1] is last_message
    else:
        assert last_message.type == "ai"

    assert "structured_response" in result


def test_remote_tool_with_agent(json_server: str, weather_agent_remote_tool_yaml: str) -> None:
    from langchain_core.runnables import RunnableConfig

    yaml_content = weather_agent_remote_tool_yaml
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    agent = AgentSpecLoader().load_yaml(_replace_config_placeholders(yaml_content, json_server))
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

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    old_value = os.environ.pop("OPENAI_API_KEY", None)

    try:
        with pytest.raises(
            openai.OpenAIError,
            match="The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable",
        ):
            AgentSpecLoader(tool_registry={"get_weather": get_weather}).load_yaml(
                weather_agent_server_tool_openaicompatible_yaml
            )
    finally:
        if old_value is not None:
            os.environ["OPENAI_API_KEY"] = old_value


@mock.patch.dict(os.environ, {"OPENAI_API_KEY": "MOCKED_KEY"})
def test_execute_weather_agent_with_server_tool_with_openaicompatible_llm(
    weather_agent_server_tool_openaicompatible_yaml: str,
) -> None:
    from langchain_core.messages import ToolMessage
    from langchain_core.runnables import RunnableConfig

    from pyagentspec.adapters.langgraph import AgentSpecLoader

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


def test_execute_swarm(swarm_calculator_yaml: str) -> None:
    from langchain_core.runnables import RunnableConfig

    from pyagentspec.adapters.langgraph import AgentSpecLoader

    tools_called = []

    def add(a: int, b: int) -> int:
        """Add two numbers"""
        tools_called.append("add")
        return a + b

    def multiply(a: int, b: int) -> int:
        """Multiply two numbers"""
        tools_called.append("multiply")
        return a * b

    langgraph_swarm = AgentSpecLoader(tool_registry={"add": add, "multiply": multiply}).load_yaml(
        swarm_calculator_yaml
    )

    config = RunnableConfig({"configurable": {"thread_id": "1"}})
    messages = [{"role": "user", "content": "2+2"}]
    response = langgraph_swarm.invoke(input={"messages": messages}, config=config)
    last_message = response["messages"][-1]
    assert "4" in last_message.content
    assert "add" in tools_called

    messages.append({"role": "assistant", "content": last_message.content})
    messages.append({"role": "user", "content": "3*3"})
    response = langgraph_swarm.invoke(input={"messages": messages}, config=config)
    last_message = response["messages"][-1]
    assert "9" in last_message.content
    assert "multiply" in tools_called
