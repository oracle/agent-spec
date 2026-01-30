# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, OutputMessageNode, StartNode
from pyagentspec.property import StringProperty


@pytest.mark.usefixtures("mute_crewai_console_prints")
def test_outputmessagenode_can_be_imported_and_executed(monkeypatch) -> None:
    from crewai import Flow as CrewAIFlow

    from pyagentspec.adapters.crewai import AgentSpecLoader

    # Capture printed message from OutputMessageNodeExecutor via Printer.print
    captured: dict[str, str] = {}

    def fake_print(self, content: str = "", color=None) -> None:
        captured["content"] = content

    monkeypatch.setattr("crewai.utilities.printer.Printer.print", fake_print, raising=True)

    custom_input_property = StringProperty(title="custom_input")
    output_message_node = OutputMessageNode(
        name="output_message",
        message="Hey {{custom_input}}",
        inputs=[custom_input_property],
    )
    start_node = StartNode(name="start", inputs=[custom_input_property])
    end_node = EndNode(name="end")

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, output_message_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(
                name="start_to_node", from_node=start_node, to_node=output_message_node
            ),
            ControlFlowEdge(name="node_to_end", from_node=output_message_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=custom_input_property.title,
                destination_node=output_message_node,
                destination_input=custom_input_property.title,
            ),
        ],
        inputs=[custom_input_property],
    )

    flow_instance = AgentSpecLoader().load_component(flow)

    assert isinstance(flow_instance, CrewAIFlow)

    result = flow_instance.kickoff({"custom_input": "custom"})

    assert isinstance(result, dict)
    assert result == {}
    assert "content" in captured
    assert captured["content"].strip() == "Hey custom"
