# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.agent import Agent
from pyagentspec.llms import LlmGenerationConfig, VllmConfig
from pyagentspec.mcp import (
    MCPTool,
    SSEmTLSTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPmTLSTransport,
    StreamableHTTPTransport,
)
from pyagentspec.mcp.clienttransport import ClientTransport
from pyagentspec.serialization.deserializer import AgentSpecDeserializer
from pyagentspec.serialization.serializer import AgentSpecSerializer


def get_example_agent_with_mcp_tool(client_transport: ClientTransport) -> Agent:
    llm_config = VllmConfig(
        id="some_model",
        name="vllm",
        url="http://some.where",
        model_id="some-model",
        default_generation_parameters=LlmGenerationConfig(
            temperature=0.5,
            max_tokens=123,
        ),
    )
    mcp_tool = MCPTool(id="mcp_tool", name="mcp_tool", client_transport=client_transport)
    return Agent(
        id="agent_with_mcp_tool",
        name="agent_with_mcp_tool",
        llm_config=llm_config,
        tools=[mcp_tool],
        system_prompt="Use the tools to answer questions.",
    )


@pytest.mark.parametrize(
    "client_transport",
    argvalues=[
        StdioTransport(
            id="client_transport_component_id",
            name="stdio_mcp_transport",
            command="python3",
            args=["servers/your_stdio_server.py"],
            env={"PYTHON": "3.12"},
        ),
        SSETransport(
            id="client_transport_component_id",
            name="sse_mcp_transport",
            url="https://some.where/sse",
        ),
        SSEmTLSTransport(
            id="client_transport_component_id",
            name="sse_mtls_mcp_transport",
            url="https://some.where/sse",
            key_file="client.key",
            cert_file="client.crt",
            ca_file="trustedCA.pem",
        ),
        StreamableHTTPTransport(
            id="client_transport_component_id",
            name="shttp_mcp_transport",
            url="https://some.where/mcp",
        ),
        StreamableHTTPmTLSTransport(
            id="client_transport_component_id",
            name="shttp_mtls_mcp_transport",
            url="https://some.where/mcp",
            key_file="client.key",
            cert_file="client.crt",
            ca_file="trustedCA.pem",
        ),
    ],
    ids=[
        "Stdio",
        "SSE",
        "SSE_mTLS",
        "StreamableHTTP",
        "StreamableHTTP_mTLS",
    ],
)
def test_agent_with_mcp_tool_can_be_serialized_then_deserialized(
    client_transport: ClientTransport,
) -> None:
    example_agent_with_mcp_tool = get_example_agent_with_mcp_tool(client_transport)
    ser_obj = AgentSpecSerializer().to_yaml(example_agent_with_mcp_tool)
    new_agent = AgentSpecDeserializer().from_yaml(
        ser_obj,
        components_registry={
            "client_transport_component_id.key_file": "client.key",
            "client_transport_component_id.cert_file": "client.crt",
            "client_transport_component_id.ca_file": "trustedCA.pem",
        },
    )
    assert example_agent_with_mcp_tool == new_agent
