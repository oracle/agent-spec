# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

"""Define MCP configuration abstraction and concrete classes for using tools exposed by MCP servers."""

from pydantic import SerializeAsAny

from pyagentspec.tools.tool import Tool

from .clienttransport import ClientTransport


class MCPTool(Tool):
    """Class for tools exposed by MCP servers"""

    client_transport: SerializeAsAny[ClientTransport]
    """Transport to use for establishing and managing connections to the MCP server."""
