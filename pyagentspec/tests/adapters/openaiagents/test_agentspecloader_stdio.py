# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.adapters.openaiagents import AgentSpecLoader
from pyagentspec.flows.edges import ControlFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode


def test_openai_flow_codegen_load_component_validates_component_policy() -> None:
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
