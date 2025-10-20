# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes.endnode import EndNode
from pyagentspec.flows.nodes.mapnode import MapNode, ReductionMethod
from pyagentspec.flows.nodes.startnode import StartNode
from pyagentspec.flows.nodes.toolnode import ToolNode
from pyagentspec.property import (
    FloatProperty,
    Property,
)
from pyagentspec.tools.servertool import ServerTool


@pytest.fixture
def server_tool() -> ServerTool:
    number_property = FloatProperty(title="some_number")
    server_tool = ServerTool(
        name="double_number",
        description="Returns the number doubled",
        inputs=[number_property],
        outputs=[number_property],
    )
    return server_tool


def test_tool_node_has_inputs_inferred_from_tool(server_tool: ServerTool) -> None:
    number_property = FloatProperty(title="some_number")
    tool_node = ToolNode(name="node", tool=server_tool)
    assert tool_node.inputs == [number_property]
    assert tool_node.outputs == [number_property]


def test_tool_node_raises_on_renamed_inputs_from_tool(server_tool: ServerTool) -> None:
    number_property = FloatProperty(title="INCORRECT_NAME")
    with pytest.raises(ValueError, match="INCORRECT_NAME"):
        ToolNode(name="node", tool=server_tool, inputs=[number_property])


def test_tool_node_raises_on_renamed_outputs_from_tool(server_tool: ServerTool) -> None:
    number_property = FloatProperty(title="INCORRECT_NAME")
    with pytest.raises(ValueError, match="INCORRECT_NAME"):
        ToolNode(name="node", tool=server_tool, outputs=[number_property])
