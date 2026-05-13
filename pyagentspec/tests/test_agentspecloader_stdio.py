# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

from typing import Any, Dict, Optional

import pytest

from pyagentspec.adapters._agentspecloader import AdapterAgnosticAgentSpecLoader
from pyagentspec.component import Component
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode
from pyagentspec.mcp import MCPTool, StdioTransport
from pyagentspec.serialization import AgentSpecSerializer


class _IdentityConverter:
    def convert(
        self,
        agentspec_component: Component,
        tool_registry: Dict[str, Any],
        referenced_objects: Optional[Dict[str, Component]] = None,
        **kwargs: Any,
    ) -> Component:
        return agentspec_component


class _IdentityLoader(AdapterAgnosticAgentSpecLoader):
    @property
    def agentspec_to_runtime_converter(self) -> _IdentityConverter:
        return _IdentityConverter()

    @property
    def runtime_to_agentspec_converter(self) -> _IdentityConverter:
        return _IdentityConverter()


class CustomStdioTransport(StdioTransport):
    pass


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


def test_adapter_agnostic_loader_blocks_stdio_transport_from_yaml_by_default() -> None:
    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        _IdentityLoader().load_yaml(AgentSpecSerializer().to_yaml(_make_stdio_mcp_tool()))


def test_adapter_agnostic_loader_allows_stdio_transport_from_yaml_when_unblocked() -> None:
    loaded_tool = _IdentityLoader(blocked_components=[]).load_yaml(
        AgentSpecSerializer().to_yaml(_make_stdio_mcp_tool())
    )
    assert isinstance(loaded_tool, MCPTool)
    assert isinstance(loaded_tool.client_transport, StdioTransport)
    assert loaded_tool.client_transport.command == "python3"


def test_adapter_agnostic_loader_blocks_stdio_transport_from_component_by_default() -> None:
    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        _IdentityLoader().load_component(_make_stdio_mcp_tool())


def test_adapter_agnostic_loader_blocks_stdio_transport_subclasses_by_default() -> None:
    tool = MCPTool(
        name="custom_stdio_tool",
        client_transport=CustomStdioTransport(
            name="custom_stdio_transport",
            command="python3",
        ),
    )

    with pytest.raises(ValueError, match="CustomStdioTransport.*in the block list"):
        _IdentityLoader().load_component(tool)


def test_langgraph_loader_blocks_stdio_transport_from_component_by_default() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        AgentSpecLoader().load_component(_make_stdio_mcp_tool())


def test_component_convenience_loaders_respect_blocked_components() -> None:
    tool = _make_stdio_mcp_tool()
    serializer = AgentSpecSerializer()

    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        Component.from_yaml(serializer.to_yaml(tool), blocked_components=[StdioTransport])
    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        Component.from_json(serializer.to_json(tool), blocked_components=[StdioTransport])
    with pytest.raises(ValueError, match="StdioTransport.*in the block list"):
        Component.from_dict(serializer.to_dict(tool), blocked_components=[StdioTransport])


def test_adapter_agnostic_loader_respects_allowed_components() -> None:
    with pytest.raises(ValueError, match="MCPTool.*not in the allow list"):
        loader = _IdentityLoader(
            allowed_components=["StdioTransport"],
            blocked_components=[],
        )
        loader.load_component(_make_stdio_mcp_tool())


def test_openai_flow_codegen_load_component_validates_component_policy() -> None:
    from pyagentspec.adapters.openaiagents import AgentSpecLoader

    start_node = StartNode(name="start")
    end_node = EndNode(name="end")
    flow = Flow(
        name="blocked_flow",
        start_node=start_node,
        nodes=[start_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_end", from_node=start_node, to_node=end_node)
        ],
    )

    with pytest.raises(ValueError, match="Flow.*in the block list"):
        AgentSpecLoader(blocked_components=["Flow"]).load_component(flow)
