# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
import threading

import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP

from ..conftest import (
    CONFIGS,
    _get_free_tcp_port,
    _replace_config_placeholders,
    _start_app_server_in_thread,
)


@pytest.fixture()
def agent_with_zwak_mcp_tool() -> str:
    return _replace_config_placeholders((CONFIGS / "agent_with_zwak_mcp_tool.yaml").read_text())


def _import_mcp(host: str, port: int) -> FastMCP:
    """Import MCP from local mcp_server.py"""
    from .mcp_server import get_mcp_server

    mcp = get_mcp_server(host, port)
    if mcp is None:
        raise RuntimeError(
            "tests/mcp_server.py must expose a get_mcp_server function that returns a FastMCP instance."
        )
    return mcp


# Local MCP server for testing
MCP_SERVER_PORT: int | None = _get_free_tcp_port()
IS_MCP_SERVER_RUNNING: bool = False

_mcp_server_thread: threading.Thread | None = None
_mcp_server_instance: uvicorn.Server | None = None


@pytest.fixture(scope="session")
def mcp_server():
    """Session fixture starting/stopping FastMCP mcp server."""
    global IS_MCP_SERVER_RUNNING, _mcp_server_thread, _mcp_server_instance

    if MCP_SERVER_PORT is not None:
        IS_MCP_SERVER_RUNNING = True
        host = "127.0.0.1"
        _mcp_server_instance, _mcp_server_thread = _start_app_server_in_thread(
            _import_mcp(host, MCP_SERVER_PORT).streamable_http_app(), host, MCP_SERVER_PORT
        )
        try:
            yield
        finally:
            _mcp_server_instance.should_exit = True
            _mcp_server_thread.join(timeout=5)
            IS_MCP_SERVER_RUNNING = False
    else:
        IS_MCP_SERVER_RUNNING = False
        yield
