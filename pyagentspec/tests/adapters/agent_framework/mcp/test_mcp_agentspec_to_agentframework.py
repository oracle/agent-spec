# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import anyio
import pytest

from pyagentspec.mcp.clienttransport import StreamableHTTPTransport

CLIENT_TRANSPORT_NAMES = [
    # Only streamablehttp_client_transport is currently supported
    "streamablehttp_client_transport",
]


@pytest.fixture
def streamablehttp_client_transport(streamablehttp_mcp_server_http):
    return StreamableHTTPTransport(name="my server 4", url=streamablehttp_mcp_server_http)


@pytest.fixture
def agentspec_agent_with_mcp_tool(client_transport_name, big_llama, request):
    from pyagentspec.agent import Agent
    from pyagentspec.mcp import MCPTool

    client_transport = request.getfixturevalue(client_transport_name)
    return Agent(
        name="agent",
        tools=[MCPTool(name="zwak_tool", client_transport=client_transport)],
        llm_config=big_llama,
        system_prompt="You're a zwak tool agent",
    )


@pytest.mark.parametrize("client_transport_name", CLIENT_TRANSPORT_NAMES)
def test_mcp_server_streamable_http_with_agent(agentspec_agent_with_mcp_tool) -> None:
    from pyagentspec.adapters.agent_framework import AgentSpecLoader

    agent = AgentSpecLoader().load_component(agentspec_agent_with_mcp_tool)
    result = anyio.run(agent.run, "What is 1 zwak 1?")
    response = result.messages[-1].text
    assert "42" in response
