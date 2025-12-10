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
from pyagentspec.versioning import AgentSpecVersionEnum

from .clienttransport import ClientTransport


class MCPTool(Tool):
    """Class for tools exposed by MCP servers"""

    client_transport: SerializeAsAny[ClientTransport]
    """Transport to use for establishing and managing connections to the MCP server."""


class MCPToolSpec(ComponentWithIO):
    """Specification of MCP tool"""

    requires_confirmation: bool = False
    """Flag to make tool require user confirmation before execution."""

    def _versioned_model_fields_to_exclude(
        self, agentspec_version: AgentSpecVersionEnum
    ) -> set[str]:
        fields_to_exclude = set()
        if agentspec_version < AgentSpecVersionEnum.v25_4_2:
            fields_to_exclude.add("requires_confirmation")
        return fields_to_exclude

    def _infer_min_agentspec_version_from_configuration(self) -> AgentSpecVersionEnum:
        parent_min_version = super()._infer_min_agentspec_version_from_configuration()
        current_object_min_version = self.min_agentspec_version
        if self.requires_confirmation:
            # If the tool requires confirmation, then we need to use the new AgentSpec version
            # If not, the old version will work as it was the de-facto
            current_object_min_version = AgentSpecVersionEnum.v25_4_2
        return max(current_object_min_version, parent_min_version)


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
        * If the tool requires confirmation before use, it overrides the exposed tool's confirmation flag.
    """
