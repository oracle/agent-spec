# Copyright © 2025, 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import os

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, EndNode, StartNode
from pyagentspec.llms import VllmConfig
from pyagentspec.property import StringProperty


def test_agentnode_can_be_imported_and_executed() -> None:
    from pyagentspec.adapters.langgraph import AgentSpecLoader

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


def test_langgraph_graph_with_agent_node_can_be_exported() -> None:
    from typing import TypedDict

    from langchain_openai.chat_models import ChatOpenAI
    from langgraph.graph import END, START, StateGraph
    from langgraph.prebuilt import create_react_agent
    from pydantic import SecretStr
    from typing_extensions import Dict, List

    from pyagentspec.adapters.langgraph import AgentSpecExporter

    class InternalState(TypedDict):
        # structured_response: Dict[str, str] = {}
        messages: List[Dict[str, str]]
        remaining_steps: int = 25

    agent = create_react_agent(
        model=ChatOpenAI(
            base_url=os.environ.get("LLAMA70BV33_API_URL"),
            model="/storage/models/Llama-3.3-70B-Instruct",
            api_key=SecretStr("t"),
        ),
        tools=[],
        state_schema=InternalState,
    )

    workflow = (
        StateGraph(InternalState)
        .add_node("myagent_node", agent)
        .add_edge(START, "myagent_node")
        .add_edge("myagent_node", END)
        .compile()
    )

    agentspec_config = AgentSpecExporter().to_component(workflow)

    assert isinstance(agentspec_config, Flow)
    assert len(agentspec_config.nodes) == 3
    agent_node = [node for node in agentspec_config.nodes if isinstance(node, AgentNode)]
    assert len(agent_node) == 1
    assert agent_node[0].name == "myagent_node"
    assert any(isinstance(node, StartNode) for node in agentspec_config.nodes)
    assert any(isinstance(node, EndNode) for node in agentspec_config.nodes)
    assert len(agentspec_config.outputs) == 1
    assert agentspec_config.outputs[0].title == "state"
    assert agentspec_config.outputs[0].type == "object"
    assert set(agentspec_config.outputs[0].json_schema["properties"].keys()) == {
        "messages",
        "remaining_steps",
    }
