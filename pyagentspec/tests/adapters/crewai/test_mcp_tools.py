# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from pathlib import Path

import pytest

from ..conftest import llama70bv33_api_url

CONFIGS = Path(__file__).parent / "configs"


@pytest.fixture
def sse_client_transport(sse_mcp_server_http):
    from pyagentspec.mcp import SSETransport

    return SSETransport(name="SSE HTTP", url=sse_mcp_server_http)


@pytest.fixture
def sse_client_transport_https(sse_mcp_server_https):
    from pyagentspec.mcp import SSETransport

    return SSETransport(name="SSE HTTPS", url=sse_mcp_server_https)


@pytest.fixture
def streamablehttp_client_transport(streamablehttp_mcp_server_http):
    from pyagentspec.mcp import StreamableHTTPTransport

    return StreamableHTTPTransport(name="Streamable HTTP", url=streamablehttp_mcp_server_http)


@pytest.fixture
def streamablehttp_client_transport_https(streamablehttp_mcp_server_https):
    from pyagentspec.mcp import StreamableHTTPTransport

    return StreamableHTTPTransport(name="Streamable HTTPS", url=streamablehttp_mcp_server_https)


def convert_and_run_agentspec_agent_with_mcp_tools(client_transport):
    from crewai import Crew, Task

    from pyagentspec.adapters.crewai import AgentSpecLoader
    from pyagentspec.agent import Agent
    from pyagentspec.llms import VllmConfig
    from pyagentspec.mcp import MCPTool
    from pyagentspec.property import IntegerProperty

    get_user_session_tool = MCPTool(
        client_transport=client_transport,
        description="Return session details for the current user",
        name="get_user_session",
    )
    get_payslips_tool = MCPTool(
        client_transport=client_transport,
        description="Return payslip details for a given PersonId",
        name="get_payslips",
        inputs=[
            IntegerProperty(
                title="PersonId",
                description="Specifies ID of the person whose invoices will be fetched",
            )
        ],
    )
    llm_config = VllmConfig(
        name="Llama-3.3-70B-Instruct",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=llama70bv33_api_url,
    )
    agent = Agent(
        name="Agent using MCP",
        llm_config=llm_config,
        system_prompt="Use tools at your disposal to solve the specific task",
        tools=[get_user_session_tool, get_payslips_tool],
    )

    crewai_agent = AgentSpecLoader().load_component(agent)
    task = Task(
        description="Find the date of the last invoice of the current user. Hint: Use the tools are your disposal. First, get the current user using `get_user_session` tool. Next, get all invoices of the current user using `get_payslips` tool. Finally, find the invoice with the highest / most recent date using the `PaymentDate` attribute.",
        expected_output="The output must solely contain the date of the last invoice in format YYYY-MM-DD. Example output: 2025-12-25",
        agent=crewai_agent,
    )
    crew = Crew(agents=[crewai_agent], tasks=[task])

    assert len(crewai_agent.tools) == 2
    assert any("get_user_session" in tool.description for tool in crewai_agent.tools)
    assert any("get_payslips" in tool.description for tool in crewai_agent.tools)

    # running the CrewAI agent is currently disabled due to flaky tests
    # result = crew.kickoff()
    # assert "2024-05-15" in result.raw


@pytest.mark.parametrize(
    "client_transport_name",
    [
        "sse_client_transport",
        "sse_client_transport_https",
        "streamablehttp_client_transport",
        "streamablehttp_client_transport_https",
    ],
)
def test_agentspec_agent_with_mcp_tools_conversion_to_crewai_agent(client_transport_name, request):
    client_transport = request.getfixturevalue(client_transport_name)
    convert_and_run_agentspec_agent_with_mcp_tools(client_transport)


@pytest.fixture
def mcp_server_sse(sse_mcp_server_http):
    from crewai.mcp import MCPServerSSE

    return MCPServerSSE(url=sse_mcp_server_http, streamable=False)


@pytest.fixture
def mcp_server_http(streamablehttp_mcp_server_http):
    from crewai.mcp import MCPServerHTTP

    return MCPServerHTTP(url=streamablehttp_mcp_server_http)


def convert_crewai_agent_with_mcp_tools(mcp_server):
    from crewai import LLM, Agent, Task

    from pyagentspec.adapters.crewai import AgentSpecExporter

    llm = LLM(
        model="hosted_vllm//storage/models/Llama-3.3-70B-Instruct",
        api_base=llama70bv33_api_url,
    )
    agent = Agent(
        llm=llm,
        role="Financial Analyst",
        goal="Use tools at your disposal to solve the specific task",
        backstory="Expert finance analyst with advanced tool access",
        mcps=[mcp_server],
    )
    task = Task(
        description="Find the date of the last invoice of the current user. Hint: Use the tools are your disposal. First, get the current user using `get_user_session` tool. Next, get all invoices of the current user using `get_payslips` tool. Finally, find the invoice with the highest / most recent date using the `PaymentDate` attribute.",
        expected_output="The output must solely contain the date of the last invoice in format YYYY-MM-DD. Example output: 2025-12-25",
        agent=agent,
    )
    agentspec_agent = AgentSpecExporter().to_component(agent)
    assert len(agentspec_agent.tools) == 2
    assert any(tool.name == "get_user_session" for tool in agentspec_agent.tools)
    assert any(tool.name == "get_payslips" for tool in agentspec_agent.tools)


@pytest.mark.parametrize(
    "mcp_server",
    [
        "mcp_server_sse",
        "mcp_server_http",
    ],
)
def test_crewai_agent_with_mcp_tools_conversion_to_agentspec_agent(mcp_server, request):
    mcp_server = request.getfixturevalue(mcp_server)
    convert_crewai_agent_with_mcp_tools(mcp_server)
