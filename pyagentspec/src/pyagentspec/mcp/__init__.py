# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define MCP configuration abstraction and concrete classes for connecting to MCP servers."""

from .clienttransport import (
    SessionParameters,
    SSEmTLSTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPmTLSTransport,
    StreamableHTTPTransport,
)
from .tools import MCPTool, MCPToolBox, MCPToolSpec

__all__ = [
    "MCPTool",
    "MCPToolSpec",
    "MCPToolBox",
    "SessionParameters",
    "SSETransport",
    "SSEmTLSTransport",
    "StdioTransport",
    "StreamableHTTPmTLSTransport",
    "StreamableHTTPTransport",
]
