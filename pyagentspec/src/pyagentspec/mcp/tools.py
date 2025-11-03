# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""Define MCP configuration abstraction and concrete classes for using tools exposed by MCP servers."""

from typing import List, Optional, Union

from pydantic import SerializeAsAny

from pyagentspec.component import ComponentWithIO
from pyagentspec.tools.tool import Tool
from pyagentspec.tools.toolbox import ToolBox

from .clienttransport import ClientTransport


class MCPTool(Tool):
    """Class for tools exposed by MCP servers"""

    client_transport: SerializeAsAny[ClientTransport]
    """Transport to use for establishing and managing connections to the MCP server."""


class MCPToolSpec(ComponentWithIO):
    """Specification of MCP tool"""


class MCPToolBox(ToolBox):
    """Class to dynamically expose a list of tools from a MCP Server."""

    client_transport: ClientTransport
    """Transport to use for establishing and managing connections to the MCP server."""

    tool_filter: Optional[List[Union[MCPToolSpec, str]]] = None
    """
	Optional filter to select specific tools.

	If None, exposes all tools from the MCP server.

 	* Specifying a tool name (``str``) indicates that a tool of the given name is expected from the MCP server.
   	* Specifying a tool signature (``MCPToolSpec``) validate the presence and signature of the specified tool in the MCP Server.
        * The name of the MCP tool should match the name of the tool from the MCP Server.
  		* Specifying a non-empty description will override the description of the tool from the MCP Server.
		* Inputs can be provided with description of each input. The names and types should match the MCP tool schema.
        * If provided, the outputs must be a single ``StringProperty`` with the expected tool output name and optional description.

    """
