# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import anyio
import pytest

from pyagentspec.mcp import (
    MCPTool,
    SSETransport,
    StreamableHTTPTransport,
)

AGENTSPEC_CLIENT_TRANSPORT_NAMES = [
    "agentspec_sse_client_transport",
    "agentspec_sse_client_transport_https",
    "agentspec_streamablehttp_client_transport",
    # "agentspec_streamablehttp_client_transport_https",  # CrewAI/HTTPX verifies TLS certs; test server uses self-signed cert
]

CREWAI_MCP_SERVERS = [
    "crewai_sse_mcp_server_http",
    "crewai_streamablehttp_mcp_server_http",
]


@pytest.fixture
def agentspec_sse_client_transport(sse_mcp_server_http):
    return SSETransport(name="SSE HTTP", url=sse_mcp_server_http)


@pytest.fixture
def agentspec_sse_client_transport_https(sse_mcp_server_https):
    return SSETransport(name="SSE HTTPS", url=sse_mcp_server_https)


@pytest.fixture
def agentspec_streamablehttp_client_transport(streamablehttp_mcp_server_http):
    return StreamableHTTPTransport(name="Streamable HTTP", url=streamablehttp_mcp_server_http)


@pytest.fixture
def agentspec_streamablehttp_client_transport_https(streamablehttp_mcp_server_https):
    return StreamableHTTPTransport(name="Streamable HTTPS", url=streamablehttp_mcp_server_https)


@pytest.fixture
def crewai_sse_mcp_server_http(sse_mcp_server_http):
    from crewai.mcp import MCPServerSSE

    return MCPServerSSE(url=sse_mcp_server_http, streamable=False)


@pytest.fixture
def crewai_streamablehttp_mcp_server_http(streamablehttp_mcp_server_http):
    from crewai.mcp import MCPServerHTTP

    return MCPServerHTTP(url=streamablehttp_mcp_server_http)


@pytest.fixture
def agentspec_agent_with_mcp_tool(client_transport_name, default_llm_config, request):
    from pyagentspec.agent import Agent

    client_transport = request.getfixturevalue(client_transport_name)

    return Agent(
        name="agent",
        tools=[MCPTool(name="zwak_tool", client_transport=client_transport)],
        llm_config=default_llm_config,
        system_prompt="You're a zwak tool agent. You must use the zwak tool to help the user.",
    )


@pytest.mark.parametrize("client_transport_name", AGENTSPEC_CLIENT_TRANSPORT_NAMES)
def test_agentspec_agent_with_mcp_tool_conversion_to_crewai_agent(
    agentspec_agent_with_mcp_tool,
    monkeypatch,
):
    from crewai import Crew, Task

    from pyagentspec.adapters.crewai import AgentSpecLoader

    agent = AgentSpecLoader().load_component(agentspec_agent_with_mcp_tool)

    assert len(agent.tools) == 1
    tool = agent.tools[0]
    assert "zwak_tool" in tool.name
    assert "zwak_tool" in tool.description

    scripted_llm_outputs = iter(
        [
            f"Thought: I should use the tool.\n"
            f"Action: {tool.name}\n"
            f'Action Input: {{"a": 1, "b": 1}}\n',
            "Final Answer: 42",
        ]
    )

    def fake_llm_call(*args, **kwargs):
        return next(scripted_llm_outputs)

    monkeypatch.setattr(agent.llm, "call", fake_llm_call, raising=False)
    monkeypatch.setattr(agent.llm, "invoke", fake_llm_call, raising=False)

    task = Task(
        description="What is 1 zwak 1?",
        expected_output="The output must solely contain the output of the operation.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task])
    result = crew.kickoff()

    assert tool.current_usage_count >= 1
    assert "42" in result.raw


@pytest.fixture
def crewai_agent_with_mcp_tool(mcp_server, crewai_llama, request):
    from crewai import Agent

    mcp_server = request.getfixturevalue(mcp_server)

    return Agent(
        llm=crewai_llama,
        role="Agent",
        goal="Use tools at your disposal to answer the requests from users",
        backstory="Expert at tool calling to help the user",
        mcps=[mcp_server],
    )


@pytest.mark.parametrize("mcp_server", CREWAI_MCP_SERVERS)
def test_crewai_agent_with_mcp_tool_conversion_to_agentspec_agent(crewai_agent_with_mcp_tool):
    from pyagentspec.adapters.crewai import AgentSpecExporter

    agent = AgentSpecExporter().to_component(crewai_agent_with_mcp_tool)

    expected_mcp_tools = ["fooza_tool", "bwip_tool", "zbuk_tool", "zwak", "generate_random_string"]
    assert len(agent.tools) == len(expected_mcp_tools)
    for tool_name in expected_mcp_tools:
        assert any(tool.name == tool_name for tool in agent.tools)
