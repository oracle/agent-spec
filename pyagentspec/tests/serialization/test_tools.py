# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.mcp.clienttransport import SSETransport
from pyagentspec.mcp.tools import MCPTool
from pyagentspec.serialization import AgentSpecDeserializer, AgentSpecSerializer
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool, Tool
from pyagentspec.versioning import AgentSpecVersionEnum

from ..conftest import read_agentspec_config_file
from .conftest import assert_serialized_representations_are_equal


def make_client_tool():
    return ClientTool(
        name="tool",
        description="Tool requiring confirmation",
        id="tool123",
        requires_confirmation=True,
    )


def make_server_tool():
    return ServerTool(
        name="server_tool",
        description="Server tool requiring confirmation",
        id="server123",
        requires_confirmation=True,
        inputs=[],
        outputs=[],
    )


def make_remote_tool():
    return RemoteTool(
        name="remote_tool",
        description="Remote tool requiring confirmation",
        id="remote123",
        requires_confirmation=True,
        url="https://example.com/api",
        http_method="POST",
        api_spec_uri="https://example.com/openapi.yaml",
        data={},
        query_params={},
        headers={},
        outputs=[],
    )


def make_mcp_tool():
    transport = SSETransport(id="sse1", name="mcp_transport", url="https://example.com/sse")
    return MCPTool(
        name="mcp_tool",
        description="MCP tool requiring confirmation",
        id="mcp123",
        requires_confirmation=True,
        client_transport=transport,
    )


@pytest.mark.parametrize(
    "tool_factory,expected_name,expected_desc,expected_id",
    [
        (make_client_tool, "tool", "Tool requiring confirmation", "tool123"),
        (make_server_tool, "server_tool", "Server tool requiring confirmation", "server123"),
        (make_remote_tool, "remote_tool", "Remote tool requiring confirmation", "remote123"),
        (make_mcp_tool, "mcp_tool", "MCP tool requiring confirmation", "mcp123"),
    ],
)
def test_can_instantiate_tool(tool_factory, expected_name, expected_desc, expected_id):
    tool = tool_factory()
    assert tool.name == expected_name
    assert tool.description == expected_desc
    assert tool.id == expected_id
    assert getattr(tool, "requires_confirmation", False) is True


@pytest.mark.parametrize(
    "tool_factory",
    [
        make_client_tool,
        make_server_tool,
        make_remote_tool,
        make_mcp_tool,
    ],
)
def test_can_serialize_and_deserialize_tool(tool_factory):
    tool = tool_factory()
    # Should successfully serialize/deserialize with 25.4.2
    serialized_tool = AgentSpecSerializer().to_yaml(tool)
    assert len(serialized_tool.strip()) > 0
    deserialized_tool = AgentSpecDeserializer().from_yaml(serialized_tool)
    # Should fail for versions <25.4.2
    with pytest.raises(
        ValueError, match="Invalid agentspec_version:.*but the minimum allowed version is.*"
    ):
        _ = AgentSpecSerializer().to_json(tool, agentspec_version=AgentSpecVersionEnum.v25_4_1)
    assert isinstance(deserialized_tool, Tool)
    # Basic attribute comparison
    for attr in ["name", "description", "id", "requires_confirmation"]:
        assert getattr(deserialized_tool, attr) == getattr(tool, attr)


def test_serialized_representations_are_equal_in_agent_with_confirmation_tools(vllmconfig):
    tools = [make_client_tool(), make_server_tool(), make_remote_tool(), make_mcp_tool()]
    agent = Agent(
        id="dummy_agent",
        name="Dummy Agent With All Tools",
        system_prompt="Testing tools with requires_confirmation in v25.4.2",
        llm_config=vllmconfig,
        tools=tools,
    )
    serializer = AgentSpecSerializer()
    serialized_agent = serializer.to_yaml(agent)
    example_serialized_agent = read_agentspec_config_file(
        "example_tools_with_confirmation_25_4_2.yaml"
    )
    assert_serialized_representations_are_equal(serialized_agent, example_serialized_agent)
