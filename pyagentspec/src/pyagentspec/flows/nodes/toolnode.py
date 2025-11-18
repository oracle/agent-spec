# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""This module defines several Agent Spec components."""

from typing import List

from pydantic import SerializeAsAny

from pyagentspec.flows.node import Node
from pyagentspec.property import Property
from pyagentspec.tools.tool import Tool


class ToolNode(Node):
    """The tool execution node is a node that will execute a tool as part of a flow.

    - **Inputs**
        Inferred from the definition of the tool to execute.
    - **Outputs**
        Inferred from the definition of the tool to execute.
    - **Branches**
        One, the default next.

    Examples
    --------
    >>> from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
    >>> from pyagentspec.flows.flow import Flow
    >>> from pyagentspec.flows.nodes import ToolNode, StartNode, EndNode
    >>> from pyagentspec.tools import ServerTool
    >>> from pyagentspec.property import Property
    >>>
    >>> x_property = Property(json_schema={"title": "x", "type": "number"})
    >>> x_square_root_property = Property(
    ...     json_schema={"title": "x_square_root", "type": "number"}
    ... )
    >>> square_root_tool = ServerTool(
    ...     name="compute_square_root",
    ...     description="Computes the square root of a number",
    ...     inputs=[x_property],
    ...     outputs=[x_square_root_property],
    ... )
    >>> start_node = StartNode(name="start", inputs=[x_property])
    >>> end_node = EndNode(name="end", outputs=[x_square_root_property])
    >>> tool_node = ToolNode(name="", tool=square_root_tool)
    >>> flow = Flow(
    ...     name="Compute square root flow",
    ...     start_node=start_node,
    ...     nodes=[start_node, tool_node, end_node],
    ...     control_flow_connections=[
    ...         ControlFlowEdge(name="start_to_tool", from_node=start_node, to_node=tool_node),
    ...         ControlFlowEdge(name="tool_to_end", from_node=tool_node, to_node=end_node),
    ...     ],
    ...     data_flow_connections=[
    ...         DataFlowEdge(
    ...             name="x_edge",
    ...             source_node=start_node,
    ...             source_output="x",
    ...             destination_node=tool_node,
    ...             destination_input="x",
    ...         ),
    ...         DataFlowEdge(
    ...             name="x_square_root_edge",
    ...             source_node=tool_node,
    ...             source_output="x_square_root",
    ...             destination_node=end_node,
    ...             destination_input="x_square_root"
    ...         ),
    ...     ],
    ... )

    """

    tool: SerializeAsAny[Tool]
    """The tool to be executed in this Node"""

    def _get_inferred_inputs(self) -> List[Property]:
        return (self.tool.inputs or []) if hasattr(self, "tool") else []

    def _get_inferred_outputs(self) -> List[Property]:
        return (self.tool.outputs or []) if hasattr(self, "tool") else []
