# Copyright (C) 2024, 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# mypy: ignore-errors

from urllib.parse import urljoin

from pyagentspec.agent import Agent
from pyagentspec.flows.edges.controlflowedge import ControlFlowEdge
from pyagentspec.flows.edges.dataflowedge import DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import AgentNode, BranchingNode, EndNode, FlowNode, LlmNode, StartNode
from pyagentspec.llms.vllmconfig import VllmConfig
from pyagentspec.property import Property
from pyagentspec.serialization import AgentSpecSerializer
from pyagentspec.tools.remotetool import RemoteTool

remote_tools_url: str = "http://127.0.0.1:5000/"

llm_config = VllmConfig(
    name="Vllm model",
    url="vllm_url",
    model_id="model_id",
)

router_agent = Agent(
    name="Router agent",
    llm_config=llm_config,
    system_prompt="""Ignore any message you received up to this point.

You are an expert router. You have to select which route to take based on the user request.

The available routes are:
- Answer a question
- Update user profile

Start by informing the user with the list of routes that are available.

If you don''t understand which route to take, ask follow up questions to the user.

Please submit the name of the route when you understand it.

Focus only on the last message of the user.""",
    outputs=[
        Property(
            json_schema=dict(
                title="route",
                description="The route",
                type="string",
                default="no route",
            )
        )
    ],
)

update_profile_agent = Agent(
    name="Update profile agent",
    llm_config=llm_config,
    system_prompt="""You are a helpful agent that is able to update the user's profile.

Ask the user all the information you need to update the profile:
- username
- email

When you have all the information, update the profile, then exit.""",
    tools=[
        RemoteTool(
            name="Update User Profile Tool",
            description="Update User Profile Tool",
            url=urljoin(remote_tools_url, "update_user"),
            data={"username": "{{username}}", "email": "{{email}}"},
            http_method="GET",
            inputs=[
                Property(
                    json_schema=dict(
                        title="username",
                        description="The username",
                        type="string",
                    )
                ),
                Property(
                    json_schema=dict(
                        title="email",
                        description="The email",
                        type="string",
                    )
                ),
            ],
            outputs=[],
        ),
    ],
)

question_answering_agent = Agent(
    name="Question answering agent",
    llm_config=llm_config,
    system_prompt="""You are an helpful assistant. Help the user by answering their requests, and their request only (do not attempt to solve unrelated tasks).

When the user is done, you can exit.""",
)

# Nodes

start_node = StartNode(name="Start node")
end_node = EndNode(name="End node")
router_agent_node = AgentNode(name="Router agent node", agent=router_agent)
question_answering_agent_node = AgentNode(
    name="Question answering agent node", agent=question_answering_agent
)
update_profile_agent_node = AgentNode(name="Update profile agent node", agent=update_profile_agent)
branching_node = BranchingNode(
    name="Branching Node",
    mapping={
        "Answer a question": "information",
        "Update user profile": "update_profile",
    },
    inputs=[
        Property(
            json_schema=dict(
                title="next_step_name",
                description="The input to use as key for the mapping",
                type="string",
            )
        ),
    ],
)

nodes = [
    start_node,
    router_agent_node,
    branching_node,
    question_answering_agent_node,
    update_profile_agent_node,
    end_node,
]

# Control flow edges

control_flow_edges = [
    ControlFlowEdge(
        name="start_node_to_router_agent_node", from_node=start_node, to_node=router_agent_node
    ),
    ControlFlowEdge(
        name="router_agent_node_to_branching_node",
        from_node=router_agent_node,
        to_node=branching_node,
    ),
    ControlFlowEdge(
        name="branching_node_to_question_answering_agent_node",
        from_node=branching_node,
        from_branch="information",
        to_node=question_answering_agent_node,
    ),
    ControlFlowEdge(
        name="branching_node_to_update_profile_agent_node",
        from_node=branching_node,
        from_branch="update_profile",
        to_node=update_profile_agent_node,
    ),
    ControlFlowEdge(
        name="question_answering_agent_node_to_end_node",
        from_node=question_answering_agent_node,
        to_node=end_node,
    ),
    ControlFlowEdge(
        name="update_profile_agent_node_to_end_node",
        from_node=update_profile_agent_node,
        to_node=end_node,
    ),
]

# Data flow edges

data_flow_edges = [
    DataFlowEdge(
        name="router_agent_node_route_to_branching_node_next_step_name",
        source_node=router_agent_node,
        source_output="route",
        destination_node=branching_node,
        destination_input="next_step_name",
    ),
]

# Main Flow

final_assistant_flow = Flow(
    name="Routing agent flow",
    description="Flow that demonstrates a router agent with subagents",
    start_node=start_node,
    nodes=nodes,
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
)

serialized_agent = AgentSpecSerializer().to_yaml(final_assistant_flow)
