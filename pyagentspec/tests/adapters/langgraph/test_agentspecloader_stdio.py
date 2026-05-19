# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.adapters.langgraph import AgentSpecLoader
from pyagentspec.mcp import MCPTool, StdioTransport


def _make_stdio_mcp_tool() -> MCPTool:
    return MCPTool(
        name="stdio_tool",
        client_transport=StdioTransport(
            name="stdio_transport",
            command="python3",
            args=["server.py"],
            env={"EXAMPLE": "1"},
            cwd=".",
        ),
    )


def test_langgraph_loader_blocks_stdio_transport_from_component_by_default() -> None:
    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        AgentSpecLoader().load_component(_make_stdio_mcp_tool())
