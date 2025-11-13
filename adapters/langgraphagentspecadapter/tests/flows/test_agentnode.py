# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

from langgraph_agentspec_adapter import AgentSpecLoader

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import VllmConfig
from pyagentspec.property import StringProperty


def test_agentnode_can_be_imported_and_executed() -> None:

    nationality_property = StringProperty(title="nationality")
    car_property = StringProperty(title="car")
    llm_config = VllmConfig(
        name="llm_config",
        model_id="/storage/models/Llama-3.3-70B-Instruct",
        url=os.environ.get("LLAMA70BV33_API_URL"),
    )
    agent = Agent(
        name="agent",
        llm_config=llm_config,
        system_prompt="What is the fastest {{nationality}} car?",
        inputs=[nationality_property],
        outputs=[car_property],
    )
    agent_node = AgentNode(
        name="agent_node",
        agent=agent,
    )
    start_node = StartNode(name="start", inputs=[nationality_property])
    end_node = EndNode(name="end", outputs=[car_property])

    flow = Flow(
        name="flow",
        start_node=start_node,
        nodes=[start_node, agent_node, end_node],
        control_flow_connections=[
            ControlFlowEdge(name="start_to_node", from_node=start_node, to_node=agent_node),
            ControlFlowEdge(name="node_to_end", from_node=agent_node, to_node=end_node),
        ],
        data_flow_connections=[
            DataFlowEdge(
                name="input_edge",
                source_node=start_node,
                source_output=nationality_property.title,
                destination_node=agent_node,
                destination_input=nationality_property.title,
            ),
            DataFlowEdge(
                name="car_edge",
                source_node=agent_node,
                source_output=car_property.title,
                destination_node=end_node,
                destination_input=car_property.title,
            ),
        ],
        outputs=[car_property],
    )

    agent = AgentSpecLoader().load_component(flow)
    result = agent.invoke({"inputs": {"nationality": "italian"}})

    assert "outputs" in result
    assert "messages" in result

    outputs = result["outputs"]
    assert car_property.title in outputs
