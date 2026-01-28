# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from mcp.server.fastmcp import FastMCP


def get_mcp_server(host: str = "localhost", port: int = 8000) -> FastMCP:
    # Create an MCP server
    mcp = FastMCP("Demo", json_response=True, host=host, port=port)

    # Add an addition tool
    @mcp.tool()
    def zwak(a: int, b: int) -> int:
        """Zwaks two numbers"""
        return a + b + 40

    return mcp


# Run with streamable HTTP transport
if __name__ == "__main__":
    mcp = get_mcp_server()
    mcp.run(transport="streamable-http")
