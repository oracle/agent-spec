# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import sys
from contextlib import nullcontext

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import SecretStr

from pyagentspec.adapters.langgraph import AgentSpecExporter, AgentSpecLoader
from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.mcp.clienttransport import (
    SSEmTLSTransport,
    SSETransport,
    StreamableHTTPmTLSTransport,
    StreamableHTTPTransport,
)
from pyagentspec.mcp.tools import MCPTool, MCPToolBox, MCPToolSpec
from pyagentspec.property import IntegerProperty

CLIENT_TRANSPORT_NAMES = [
    "sse_client_transport",
    "sse_client_transport_https",
    "sse_client_transport_mtls",
    "streamablehttp_client_transport",
    "streamablehttp_client_transport_https",
    "streamablehttp_client_transport_mtls",
]


@pytest.fixture
def sse_client_transport(sse_mcp_server_http):
    return SSETransport(name="my server 1", url=sse_mcp_server_http)


@pytest.fixture
def sse_client_transport_https(sse_mcp_server_https):
    return SSETransport(name="my server 2", url=sse_mcp_server_https)


@pytest.fixture
def sse_client_transport_mtls(sse_mcp_server_mtls, client_cert_path, client_key_path, ca_cert_path):
    return SSEmTLSTransport(
        name="my server 3",
        url=sse_mcp_server_mtls,
        key_file=client_key_path,
        cert_file=client_cert_path,
        ca_file=ca_cert_path,
    )


@pytest.fixture
def streamablehttp_client_transport(streamablehttp_mcp_server_http):
    return StreamableHTTPTransport(name="my server 4", url=streamablehttp_mcp_server_http)


@pytest.fixture
def streamablehttp_client_transport_https(streamablehttp_mcp_server_https):
    return StreamableHTTPTransport(name="my server 5", url=streamablehttp_mcp_server_https)


@pytest.fixture
def streamablehttp_client_transport_mtls(
    streamablehttp_mcp_server_mtls, client_cert_path, client_key_path, ca_cert_path
):
    return StreamableHTTPmTLSTransport(
        name="my server 6",
        url=streamablehttp_mcp_server_mtls,
        key_file=client_key_path,
        cert_file=client_cert_path,
        ca_file=ca_cert_path,
    )


@pytest.fixture
def loaded_langgraph_agent(client_transport_name, big_llama, request):
    client_transport = request.getfixturevalue(client_transport_name)
    agentspec_agent = Agent(
        name="watashi no joshu",
        toolboxes=[MCPToolBox(name="good", client_transport=client_transport)],
        llm_config=big_llama,
        system_prompt="be kind and stay frosty",
    )
    return AgentSpecLoader().load_component(agentspec_agent)


@pytest.fixture(scope="function")
def agentspec_agent_with_mcp_toolbox(sse_client_transport, big_llama):
    return Agent(
        name="watashi no joshu",
        toolboxes=[
            MCPToolBox(
                name="drop_box",
                client_transport=sse_client_transport,
                tool_filter=[
                    "bwip_tool",
                    MCPToolSpec(
                        name="zbuk_tool",
                        description="something",
                        inputs=[
                            IntegerProperty(title="a"),
                            IntegerProperty(title="b"),
                        ],
                    ),
                ],
            )
        ],
        llm_config=big_llama,
        system_prompt="You must begin the conversation by telling the user what tools are available to you. Do not call any tools. You should generate only textual responses.",
    )


@pytest.mark.parametrize("client_transport_name", CLIENT_TRANSPORT_NAMES)
def test_can_import_agent_with_various_mcp_connections(loaded_langgraph_agent):
    assert isinstance(loaded_langgraph_agent, CompiledStateGraph)


@pytest.mark.parametrize("client_transport_name", CLIENT_TRANSPORT_NAMES)
def test_mcp_toolbox_exposes_proper_tools(loaded_langgraph_agent):
    assert set(loaded_langgraph_agent.builder.nodes["tools"].runnable.tools_by_name.keys()) == {
        "fooza_tool",
        "bwip_tool",
        "zbuk_tool",
        "generate_random_string",
    }


@pytest.mark.anyio
async def test_can_run_imported_agent_with_mcp_tools(agentspec_agent_with_mcp_toolbox):
    langgraph_agent = AgentSpecLoader().load_component(agentspec_agent_with_mcp_toolbox)

    response = await langgraph_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What tools do you have?",
                }
            ]
        },
        {"configurable": {"thread_id": "1"}},
    )
    output = ""
    for m in response["messages"][1:]:
        output += m.content
    assert output  # should not be empty


@pytest.mark.parametrize("client_transport_name", ["sse_client_transport"])
def test_cannot_export_langgraph_agent_with_mcp_tools_with_arbitrary_httpx_client(
    loaded_langgraph_agent,
):
    with pytest.raises(
        NotImplementedError,
        match="Conversion from langchain MCP connections with arbitrary httpx client factory objects is not yet implemented",
    ):
        AgentSpecExporter().to_component(loaded_langgraph_agent)


@pytest.mark.anyio
async def test_export_langgraph_agent_with_mcp_to_agentspec_agent_with_mcp(sse_client_transport):
    from langchain.agents import create_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_openai.chat_models import ChatOpenAI

    model_id = "Llama-3.1-70B-Instruct"
    url = "url.to.my.llama.model"
    model = ChatOpenAI(
        model=model_id,
        api_key=SecretStr("EMPTY"),
        base_url=f"http://{url}/v1",
    )
    client = MultiServerMCPClient(
        {
            "fooza_server": {
                "url": sse_client_transport.url,
                "transport": "sse",
            }
        }
    )
    tools = await client.get_tools()
    agent = create_agent(
        model=model,
        tools=tools,
    )
    agentspec_agent = AgentSpecExporter().to_component(agent)
    assert isinstance(agentspec_agent, Agent)
    config = agentspec_agent.llm_config
    assert isinstance(config, OpenAiCompatibleConfig)
    assert config.model_id == model_id
    assert config.url == f"http://{url}/v1"
    assert len(agentspec_agent.tools) == 4

    for tool in agentspec_agent.tools:
        assert isinstance(tool, MCPTool)
        assert isinstance(tool.client_transport, SSETransport)
        assert tool.client_transport.url == sse_client_transport.url
        assert tool.name in {"fooza_tool", "generate_random_string", "bwip_tool", "zbuk_tool"}


@pytest.mark.anyio
async def test_flow_with_mcp_tool_with_interrupt(sse_client_transport):
    from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    from pyagentspec.flows.flow import Flow
    from pyagentspec.flows.nodes import EndNode, InputMessageNode, StartNode, ToolNode
    from pyagentspec.mcp.tools import MCPTool
    from pyagentspec.property import Property

    # Define inputs and outputs
    a_property = Property(json_schema={"title": "a", "type": "number"})
    b_property = Property(json_schema={"title": "b", "type": "number"})
    result_property = Property(json_schema={"title": "my_result", "type": "number"})

    # MCP tool bound to SSE transport and exposing explicit IO
    fooza_tool = MCPTool(
        name="fooza_tool",
        description=("Return the result of the fooza operation between numbers a and b."),
        client_transport=sse_client_transport,
        inputs=[a_property, b_property],
        outputs=[result_property],
    )

    # Flow: start -> tool -> end
    start_node = StartNode(name="start", inputs=[a_property, b_property])
    input_message_node = InputMessageNode(name="input_message")
    tool_node = ToolNode(name="fooza_tool_node", tool=fooza_tool)
    end_node = EndNode(name="end", outputs=[result_property])

    flow = Flow(
        name="Fooza flow",
        start_node=start_node,
        nodes=[start_node, input_message_node, tool_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(
                name="start_to_input", from_node=start_node, to_node=input_message_node
            ),
            ControlFlowEdge(name="input_to_tool", from_node=input_message_node, to_node=tool_node),
            ControlFlowEdge(name="tool_to_end", from_node=tool_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="a_edge",
                source_node=start_node,
                source_output="a",
                destination_node=tool_node,
                destination_input="a",
            ),
            DataFlowEdge(
                name="b_edge",
                source_node=start_node,
                source_output="b",
                destination_node=tool_node,
                destination_input="b",
            ),
            DataFlowEdge(
                name="result_edge",
                source_node=tool_node,
                source_output="my_result",
                destination_node=end_node,
                destination_input="my_result",
            ),
        ],
        outputs=[result_property],
    )

    # Execute the Flow via LangGraph
    langgraph_flow = AgentSpecLoader(checkpointer=MemorySaver()).load_component(flow)
    config = RunnableConfig({"configurable": {"thread_id": "1"}})

    is_py310 = sys.version_info < (3, 11)
    pytest_warning_raises = pytest.raises(
        RuntimeError, match="Called get_config outside of a runnable context"
    )
    with pytest_warning_raises if is_py310 else nullcontext():
        # in lower python versions, langchain interrupt does not support interrupts
        interrupted = await langgraph_flow.ainvoke({"inputs": {"a": 2, "b": 5}}, config=config)

    if is_py310:
        return

    assert "__interrupt__" in interrupted  # because of InputMessageNode

    result = await langgraph_flow.ainvoke(
        Command(resume="hey"), config=config
    )  # must be a string, since it's converted to a langchain message

    # Server fooza: a*2 + b*3 - 1 => 2*2 + 5*3 - 1 = 18
    assert result["outputs"]["my_result"] == 18
