# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

import pytest

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, LlmNode, StartNode
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.property import StringProperty


@pytest.mark.usefixtures("mute_crewai_console_prints")
def test_llmnode_can_be_imported_and_executed() -> None:
    from crewai import Flow as CrewAIFlow

    from pyagentspec.adapters.crewai import AgentSpecLoader

    nationality_property = StringProperty(title="nationality")
    car_property = StringProperty(title="car")
    llm_config = OpenAiCompatibleConfig(
        name="llm_config",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=os.environ.get("LLAMA_API_URL"),
    )
    llm_node = LlmNode(
        name="llm_node",
        llm_config=llm_config,
        prompt_template="What is the fastest {{nationality}} car? Output in the format <country>: <car_brand>",
        inputs=[nationality_property],
        outputs=[car_property],
    )
    start_node = StartNode(name="start", inputs=[nationality_property])
    end_node = EndNode(name="end", outputs=[car_property])

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, llm_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=llm_node),
            ControlFlowEdge(name="node_to_end", from_node=llm_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=nationality_property.title,
                destination_node=llm_node,
                destination_input=nationality_property.title,
            ),
            DataFlowEdge(
                name="car_edge",
                source_node=llm_node,
                source_output=car_property.title,
                destination_node=end_node,
                destination_input=car_property.title,
            ),
        ],
        outputs=[car_property],
    )

    flow_instance = AgentSpecLoader().load_component(flow)

    assert isinstance(flow_instance, CrewAIFlow)

    result = flow_instance.kickoff({"nationality": "italian"})

    assert isinstance(result, dict)
    assert car_property.title in result
    assert isinstance(result[car_property.title], str)
    assert result[car_property.title] != ""
