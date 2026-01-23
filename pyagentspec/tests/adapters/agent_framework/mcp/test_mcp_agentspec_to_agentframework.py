# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import anyio

from pyagentspec.adapters.agent_framework import AgentSpecLoader

from .conftest import MCP_SERVER_PORT


def test_mcp_server_streamable_http_with_agent(mcp_server, agent_with_zwak_mcp_tool: str) -> None:
    config = agent_with_zwak_mcp_tool.replace(
        "[[MCP_SERVER_PORT]]",
        str(MCP_SERVER_PORT),
    )
    agent = AgentSpecLoader().load_yaml(config)
    result = anyio.run(agent.run, "What is 1 zwak 1?")
    response = result.messages[-1].text
    assert "42" in response
