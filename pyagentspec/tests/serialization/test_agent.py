# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import cast

import pytest

from pyagentspec import Component
from pyagentspec.agent import Agent
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.mcp.clienttransport import SSETransport
from pyagentspec.mcp.tools import MCPTool, MCPToolBox, MCPToolSpec
from pyagentspec.property import BooleanProperty, StringProperty
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool
from pyagentspec.versioning import AgentSpecVersionEnum

from ..conftest import read_agentspec_config_file
from .conftest import assert_serialized_representations_are_equal


@pytest.fixture()
def tools():
    city_input = StringProperty(
        title="city_name",
        default="zurich",
    )
    weather_output = StringProperty(
        title="forecast",
    )
    subscription_success_output = BooleanProperty(
        title="subscription_success",
    )

    weather_tool = ClientTool(
        id="weather_tool",
        name="get_weather",
        description="Gets the weather in specified city",
        inputs=[city_input],
        outputs=[weather_output],
    )

    history_tool = ServerTool(
        id="history_tool",
        name="get_city_history_info",
        description="Gets information about the city history",
        inputs=[city_input],
        outputs=[weather_output],
    )

    newsletter_subscribe_tool = RemoteTool(
        id="city_newsletter_subscribe_tool",
        name="subscribe_to_city_newsletter",
        description="Subscribe to the newsletter of a city",
        url="https://my.url/tool",
        http_method="POST",
        api_spec_uri="https://my.api.spec.url/tool",
        data={"city_name": "{{city_name}}"},
        query_params={"my_query_param": "abc"},
        headers={"my_header": "123"},
        # inputs=[city_input],  #  This is going to be inferred by the tool
        outputs=[subscription_success_output],
    )
    yield [weather_tool, history_tool, newsletter_subscribe_tool]


def test_agent_can_be_serialized(vllmconfig, tools) -> None:
    agent = Agent(
        id="agent1",
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        tools=tools,
    )
    serializer = AgentSpecSerializer()
    serialized_agent = serializer.to_yaml(agent)
    example_serialized_agent = read_agentspec_config_file(
        "example_serialized_agent_with_tools.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)


def test_agent_with_human_in_the_loop(vllmconfig, tools):
    serializer = AgentSpecSerializer()
    deserializer = AgentSpecDeserializer()

    # The min supported version for this agent is 25.4.1 (human in the loop was the default)
    # So this agent must serialize as 25.4.1
    agent = Agent(
        id="agent1",
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        tools=tools,
        human_in_the_loop=True,
    )
    serialized_agent = serializer.to_yaml(agent)
    example_serialized_agent = read_agentspec_config_file(
        "example_serialized_agent_with_tools.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)

    # Human in the loop should be set (and true!) when deserializing a 25.4.1 agent into 25.4.2
    deserialized_agent = deserializer.from_yaml(example_serialized_agent)
    assert deserialized_agent.human_in_the_loop

    # But the human_in_the_loop properties should be there when serializing to 25.4.2
    agent = Agent(
        id="agent1",
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        tools=tools,
        human_in_the_loop=True,
    )
    serialized_agent = serializer.to_yaml(agent, AgentSpecVersionEnum.v25_4_2)
    example_serialized_agent = read_agentspec_config_file(
        "example_serialized_agent_with_tools_25_4_2.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)

    # The minimum version for which we support human_in_the_loop=False is 25.4.2, so this is the
    # default serialization version in that case
    agent = Agent(
        id="agent1",
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        tools=tools,
        human_in_the_loop=False,
    )
    serialized_agent = serializer.to_yaml(agent)
    example_serialized_agent = read_agentspec_config_file(
        "example_serialized_agent_with_tools_no_human_in_the_loop.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = serializer.to_yaml(agent, agentspec_version=AgentSpecVersionEnum.v25_4_1)


def test_agent_with_toolbox_can_be_serialized() -> None:
    vllmconfig = VllmConfig(id="agi1", name="agi1", model_id="agi_model1", url="http://some.where")

    _mcp_client = SSETransport(
        id="mcp_transport", name="mcp_transport", url="https://some.where/sse"
    )
    mcp_tool = MCPTool(id="mcptool", name="my_mcp_tool", client_transport=_mcp_client)
    mcp_toolbox_without_filters = MCPToolBox(
        id="mcptoolbox_no_filter", name="MCP ToolBox", client_transport=_mcp_client
    )
    mcp_toolbox_with_filters = MCPToolBox(
        id="mcptoolbox_with_filter",
        name="MCP ToolBox",
        client_transport=_mcp_client,
        tool_filter=[
            "tool_name1",
            MCPToolSpec(
                id="tool_id2",
                name="tool_name2",
                description="description for tool2",
                requires_confirmation=True,
            ),
        ],
    )

    agent = Agent(
        id="agent1",
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="No matter what the user asks, don't reply but make a joke instead",
        tools=[mcp_tool],
        toolboxes=[mcp_toolbox_without_filters, mcp_toolbox_with_filters],
    )
    serializer = AgentSpecSerializer()
    serialized_agent = serializer.to_yaml(agent)
    example_serialized_agent = read_agentspec_config_file(
        "example_serialized_agent_with_tools_and_toolboxes.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)


@pytest.fixture
def agent_with_toolbox() -> Agent:
    vllmconfig = VllmConfig(id="agi1", name="agi1", model_id="agi_model1", url="http://some.where")
    _mcp_client = SSETransport(name="mcp_transport", url="https://some.where/sse")
    mcp_toolbox = MCPToolBox(name="MCP ToolBox", client_transport=_mcp_client)

    return Agent(
        name="Funny agent",
        llm_config=vllmconfig,
        system_prompt="Assistant instructions...",
        toolboxes=[mcp_toolbox],
    )


def test_serializing_agent_with_toolboxes_and_unsupported_version_raises(
    agent_with_toolbox: Agent,
) -> None:
    serializer = AgentSpecSerializer()
    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = serializer.to_yaml(agent_with_toolbox, agentspec_version=AgentSpecVersionEnum.v25_4_1)


def test_deserializing_agent_with_toolboxes_and_unsupported_version_raises(
    agent_with_toolbox: Agent,
) -> None:
    serializer = AgentSpecSerializer()
    serialized_node = serializer.to_yaml(agent_with_toolbox)
    assert "agentspec_version: 25.4.2" in serialized_node
    serialized_node = serialized_node.replace(
        "agentspec_version: 25.4.2", "agentspec_version: 25.4.1"
    )

    with pytest.raises(ValueError, match="Invalid agentspec_version"):
        _ = AgentSpecDeserializer().from_yaml(serialized_node)
