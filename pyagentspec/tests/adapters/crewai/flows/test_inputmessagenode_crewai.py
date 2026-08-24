# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, InputMessageNode, StartNode
from pyagentspec.property import StringProperty


@pytest.mark.usefixtures("mute_crewai_console_prints")
def test_inputmessagenode_can_be_imported_and_executed(monkeypatch) -> None:
    from crewai import Flow as CrewAIFlow

    from pyagentspec.adapters.crewai import AgentSpecLoader

    # Mock interactive input() used by InputMessageNodeExecutor
    monkeypatch.setattr("builtins.input", lambda: "3")

    custom_input_property = StringProperty(title="custom_input")
    input_message_node = InputMessageNode(
        name="input_message",
        outputs=[custom_input_property],
    )
    start_node = StartNode(name="start")
    end_node = EndNode(name="end", outputs=[custom_input_property])

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, input_message_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=input_message_node),
            ControlFlowEdge(name="node_to_end", from_node=input_message_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=input_message_node,
                source_output=custom_input_property.title,
                destination_node=end_node,
                destination_input=custom_input_property.title,
            ),
        ],
        outputs=[custom_input_property],
    )

    flow_instance = AgentSpecLoader().load_component(flow)

    assert isinstance(flow_instance, CrewAIFlow)

    result = flow_instance.kickoff()

    assert isinstance(result, dict)
    assert custom_input_property.title in result
    assert result[custom_input_property.title] == "3"
