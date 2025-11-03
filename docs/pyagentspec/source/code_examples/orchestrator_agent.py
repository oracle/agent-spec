# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# mypy: ignore-errors

from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    model_id="/storage/models/Llama-3.3-70B-Instruct",
    url="LLAMA_PLACEHOLDER_LINK",
    name="meta.llama-3.3-70b-instruct",
)


# .. start-tool:
from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool

username_property = StringProperty(title="username")
user_information_property = StringProperty(title="user_information")

tool = ServerTool(
    name="Gather user information tool",
    description="Tool that gathers user information based on its username",
    inputs=[username_property],
    outputs=[user_information_property],
)
# .. end-tool:


# .. start-orchestrator-agent:
from pyagentspec.agent import Agent
from pyagentspec.property import StringProperty

conversation_summary_property = StringProperty(
    title="conversation_summary", default="(No conversation)"
)
user_information_property = StringProperty(title="user_information")
topic_property = StringProperty(title="topic")

orchestrator_agent = Agent(
    name="Orchestrator Agent",
    description="Orchestrator agent that routes to different experts",
    inputs=[conversation_summary_property, user_information_property],
    llm_config=llm_config,
    outputs=[conversation_summary_property, topic_property],
    system_prompt="""You are an orchestrator assistant, and you are part of a larger
assistant called Oracle IT Assistant. You just have to understand the topic
of the problem, do not try to solve it.

CONTEXT
-------

The information about the user you are talking to is the following (in json
format):
```
{{user_information}}
```

The user might have already had a past conversation with the agent, here''s
the summary:
```
{{conversation_summary}}
```

TASK
----

Your task is to understand what is the CURRENT problem of the user, and based
on that, output the topic of the problem.
Do not resolve the specific problem. Someone else will take care of the solution.
You just have to understand and output the topic of the problem. Don''t ask
for confirmation to the user, when you know the topic, go ahead.
If the user had a problem in the past conversation summary, ask if the user
has other problems to solve.
Do not get the topic from the past conversation summary.

The available problem topics are:
- network
- device
- account
- unknown

If the user is done and wants to exit the conversation, you can output "unknown"
as topic. In that case, thank the user and say goodbye.

Another output you should provide is a summary of the past conversation you
had with the user. It should be a short summary, 2 sentences at most.

Once you understood the topic, submit it as the output, submit the conversation
summary, and exit.
Remember, do NOT try to solve the problem yourself.

If there''s no past conversation summary, do not talk about it in your messages.

Try to personalize your messages when you talk to the user.
Be always kind and nice.""",
    tools=[],
)
# .. end-orchestrator-agent:


# .. start-expert-agents:
from pyagentspec.agent import Agent
from pyagentspec.property import StringProperty

conversation_summary_property = StringProperty(title="conversation_summary")

account_agent = Agent(
    name="Account Agent",
    description="Expert in Oracle Account setup",
    llm_config=llm_config,
    system_prompt="""You are an expert assistant, part of the Oracle IT support assistant.
Your domain of expertise is Oracle account setup.

Please assist the user in solving his problem.


Here''s a summary of the ongoing conversation:

{{conversation_summary}}


When the user thinks that the problem is solved, or if you do not know how to
solve the problem, just submit and exit. Do not mention to the user that you
are submitting, just thank the user.


You should provide as an output a summary of the past conversation you had with
the user. It should be a short summary, 2 sentences at most. Do NOT submit the
conversation summary until the user says that the problem is solved.""",
    inputs=[conversation_summary_property],
    outputs=[conversation_summary_property],
)

network_agent = Agent(
    name="Network Agent",
    description="Expert in Oracle networking setup",
    llm_config=llm_config,
    system_prompt="""You are an expert assistant, part of the Oracle IT support assistant.
Your domain of expertise is computer networks.

Please assist the user in solving his problem.


Here''s a summary of the ongoing conversation:

{{conversation_summary}}


When the user thinks that the problem is solved, or if you do not know how to
solve the problem, just submit and exit. Do not mention to the user that you
are submitting, just thank the user.


You should provide as an output a summary of the past conversation you had with
the user. It should be a short summary, 2 sentences at most. Do NOT submit the
conversation summary until the user says that the problem is solved.""",
    inputs=[conversation_summary_property],
    outputs=[conversation_summary_property],
)

device_agent = Agent(
    name="Device Agent",
    description="Expert in Oracle devices setup",
    llm_config=llm_config,
    system_prompt="""You are an expert assistant, part of the Oracle IT support assistant.
Your domain of expertise is electronic devices.

Please assist the user in solving his problem.


Here''s a summary of the ongoing conversation:

{{conversation_summary}}


When the user thinks that the problem is solved, or if you do not know how to
solve the problem, just submit and exit. Do not mention to the user that you
are submitting, just thank the user.


You should provide as an output a summary of the past conversation you had with
the user. It should be a short summary, 2 sentences at most. Do NOT submit the
conversation summary until the user says that the problem is solved.""",
    inputs=[conversation_summary_property],
    outputs=[conversation_summary_property],
)
# .. end-expert-agents:

# .. start-nodes:
from pyagentspec.flows.nodes import (
    AgentNode,
    BranchingNode,
    EndNode,
    StartNode,
    ToolNode,
)

orchestrator_agent_node = AgentNode(
    name="Orchestrator Agent Execution",
    agent=orchestrator_agent,
)

account_agent_node = AgentNode(
    name="Account Agent Execution",
    agent=account_agent,
)

network_agent_node = AgentNode(
    name="Network Agent Execution",
    agent=network_agent,
)

device_agent_node = AgentNode(
    name="Device Agent Execution",
    agent=device_agent,
)

tool_node = ToolNode(
    name="Get user info tool Execution",
    tool=tool,
)

branching_node = BranchingNode(
    name="Branching",
    inputs=[topic_property],
    mapping={
        "account": "account",
        "device": "device",
        "network": "network",
    },
)

start_node = StartNode(name="Start", inputs=[username_property])
end_node = EndNode(name="End")
# .. end-nodes:


# .. start-control-edges:
from pyagentspec.flows.edges import ControlFlowEdge

control_flow_edges = [
    ControlFlowEdge(name="start_to_tool", from_node=start_node, to_node=tool_node),
    ControlFlowEdge(
        name="tool_to_orchestrator", from_node=tool_node, to_node=orchestrator_agent_node
    ),
    ControlFlowEdge(
        name="orchestrator_to_branching", from_node=orchestrator_agent_node, to_node=branching_node
    ),
    ControlFlowEdge(
        name="branching_to_network",
        from_node=branching_node,
        to_node=network_agent_node,
        from_branch="network",
    ),
    ControlFlowEdge(
        name="branching_to_device",
        from_node=branching_node,
        to_node=device_agent_node,
        from_branch="device",
    ),
    ControlFlowEdge(
        name="branching_to_account",
        from_node=branching_node,
        to_node=account_agent_node,
        from_branch="account",
    ),
    ControlFlowEdge(
        name="branching_to_end", from_node=branching_node, to_node=end_node, from_branch="default"
    ),
    ControlFlowEdge(
        name="network_to_orchestrator",
        from_node=network_agent_node,
        to_node=orchestrator_agent_node,
    ),
    ControlFlowEdge(
        name="device_to_orchestrator", from_node=device_agent_node, to_node=orchestrator_agent_node
    ),
    ControlFlowEdge(
        name="account_to_orchestrator",
        from_node=account_agent_node,
        to_node=orchestrator_agent_node,
    ),
]
# .. end-control-edges:


# .. start-data-edges:
from pyagentspec.flows.edges import DataFlowEdge

data_flow_edges = [
    DataFlowEdge(
        name="start_to_tool_username",
        source_node=start_node,
        source_output="username",
        destination_node=tool_node,
        destination_input="username",
    ),
    DataFlowEdge(
        name="tool_to_orchestrator_user_information",
        source_node=tool_node,
        source_output="user_information",
        destination_node=orchestrator_agent_node,
        destination_input="user_information",
    ),
    DataFlowEdge(
        name="tool_to_orchestrator_topic",
        source_node=orchestrator_agent_node,
        source_output="topic",
        destination_node=branching_node,
        destination_input="topic",
    ),
    DataFlowEdge(
        name="orchestrator_to_device_conversation_summary",
        source_node=orchestrator_agent_node,
        source_output="conversation_summary",
        destination_node=device_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="orchestrator_to_network_conversation_summary",
        source_node=orchestrator_agent_node,
        source_output="conversation_summary",
        destination_node=network_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="orchestrator_to_account_conversation_summary",
        source_node=orchestrator_agent_node,
        source_output="conversation_summary",
        destination_node=account_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="network_to_orchestrator_conversation_summary",
        source_node=network_agent_node,
        source_output="conversation_summary",
        destination_node=orchestrator_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="device_to_orchestrator_conversation_summary",
        source_node=device_agent_node,
        source_output="conversation_summary",
        destination_node=orchestrator_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="account_to_orchestrator_conversation_summary",
        source_node=account_agent_node,
        source_output="conversation_summary",
        destination_node=orchestrator_agent_node,
        destination_input="conversation_summary",
    ),
]
# .. end-data-edges:


# .. start-flow:
from pyagentspec.flows.flow import Flow

flow = Flow(
    name="Oracle IT Assistant Flow",
    description="Flow of the Oracle IT assistant",
    start_node=start_node,
    nodes=[
        start_node,
        tool_node,
        orchestrator_agent_node,
        branching_node,
        network_agent_node,
        device_agent_node,
        account_agent_node,
        end_node,
    ],
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
    inputs=[username_property],
)
# .. end-flow:


# .. start-serialization:
from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-serialization:


# .. start-full-code:
# LLama vLLM

from pyagentspec.llms import VllmConfig

llm_config = VllmConfig(
    model_id="/storage/models/Llama-3.3-70B-Instruct",
    url=" LLAMA_PLACEHOLDER_LINK",
    name="meta.llama-3.3-70b-instruct",
)


# Get user information ServerTool

from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool

username_property = StringProperty(title="username")
user_information_property = StringProperty(title="user_information")

tool = ServerTool(
    name="Gather user information tool",
    description="Tool that gathers user information based on its username",
    inputs=[username_property],
    outputs=[user_information_property],
)


# Orchestrator agent

from pyagentspec.agent import Agent
from pyagentspec.property import StringProperty

conversation_summary_property = StringProperty(
    title="conversation_summary", default="(No conversation)"
)
user_information_property = StringProperty(title="user_information")
topic_property = StringProperty(title="topic")

orchestrator_agent = Agent(
    name="Orchestrator Agent",
    description="Orchestrator agent that routes to different experts",
    inputs=[conversation_summary_property, user_information_property],
    llm_config=llm_config,
    outputs=[conversation_summary_property, topic_property],
    system_prompt="""You are an orchestrator assistant, and you are part of a larger
assistant called Oracle IT Assistant. You just have to understand the topic
of the problem, do not try to solve it.

CONTEXT
-------

The information about the user you are talking to is the following (in json
format):
```
{{user_information}}
```

The user might have already had a past conversation with the agent, here''s
the summary:
```
{{conversation_summary}}
```

TASK
----

Your task is to understand what is the CURRENT problem of the user, and based
on that, output the topic of the problem.
Do not resolve the specific problem. Someone else will take care of the solution.
You just have to understand and output the topic of the problem. Don''t ask
for confirmation to the user, when you know the topic, go ahead.
If the user had a problem in the past conversation summary, ask if the user
has other problems to solve.
Do not get the topic from the past conversation summary.

The available problem topics are:
- network
- device
- account
- unknown

If the user is done and wants to exit the conversation, you can output "unknown"
as topic. In that case, thank the user and say goodbye.

Another output you should provide is a summary of the past conversation you
had with the user. It should be a short summary, 2 sentences at most.

Once you understood the topic, submit it as the output, submit the conversation
summary, and exit.
Remember, do NOT try to solve the problem yourself.

If there''s no past conversation summary, do not talk about it in your messages.

Try to personalize your messages when you talk to the user.
Be always kind an nice.""",
    tools=[],
)

# Expert agents

from pyagentspec.agent import Agent
from pyagentspec.property import StringProperty

conversation_summary_property = StringProperty(title="conversation_summary")

account_agent = Agent(
    name="Account Agent",
    description="Expert in Oracle Account setup",
    llm_config=llm_config,
    system_prompt="""You are an expert assistant, part of the Oracle IT support assistant.
Your domain of expertise is Oracle account setup.

Please assist the user in solving his problem.


Here''s a summary of the ongoing conversation:

{{conversation_summary}}


When the user thinks that the problem is solved, or if you do not know how to
solve the problem, just submit and exit. Do not mention to the user that you
are submitting, just thank the user.


You should provide as an output a summary of the past conversation you had with
the user. It should be a short summary, 2 sentences at most. Do NOT submit the
conversation summary until the user says that the problem is solved.""",
    inputs=[conversation_summary_property],
    outputs=[conversation_summary_property],
)

network_agent = Agent(
    name="Network Agent",
    description="Expert in Oracle networking setup",
    llm_config=llm_config,
    system_prompt="""You are an expert assistant, part of the Oracle IT support assistant.
Your domain of expertise is computer networks.

Please assist the user in solving his problem.


Here''s a summary of the ongoing conversation:

{{conversation_summary}}


When the user thinks that the problem is solved, or if you do not know how to
solve the problem, just submit and exit. Do not mention to the user that you
are submitting, just thank the user.


You should provide as an output a summary of the past conversation you had with
the user. It should be a short summary, 2 sentences at most. Do NOT submit the
conversation summary until the user says that the problem is solved.""",
    inputs=[conversation_summary_property],
    outputs=[conversation_summary_property],
)

device_agent = Agent(
    name="Device Agent",
    description="Expert in Oracle devices setup",
    llm_config=llm_config,
    system_prompt="""You are an expert assistant, part of the Oracle IT support assistant.
Your domain of expertise is electronic devices.

Please assist the user in solving his problem.


Here''s a summary of the ongoing conversation:

{{conversation_summary}}


When the user thinks that the problem is solved, or if you do not know how to
solve the problem, just submit and exit. Do not mention to the user that you
are submitting, just thank the user.


You should provide as an output a summary of the past conversation you had with
the user. It should be a short summary, 2 sentences at most. Do NOT submit the
conversation summary until the user says that the problem is solved.""",
    inputs=[conversation_summary_property],
    outputs=[conversation_summary_property],
)

# Flow Nodes

from pyagentspec.flows.nodes import (
    AgentNode,
    BranchingNode,
    EndNode,
    StartNode,
    ToolNode,
)

orchestrator_agent_node = AgentNode(
    name="Orchestrator Agent Execution",
    agent=orchestrator_agent,
)

account_agent_node = AgentNode(
    name="Account Agent Execution",
    agent=account_agent,
)

network_agent_node = AgentNode(
    name="Network Agent Execution",
    agent=network_agent,
)

device_agent_node = AgentNode(
    name="Device Agent Execution",
    agent=device_agent,
)

tool_node = ToolNode(
    name="Get user info tool Execution",
    tool=tool,
)

branching_node = BranchingNode(
    name="Branching",
    inputs=[topic_property],
    mapping={
        "account": "account",
        "device": "device",
        "network": "network",
    },
)

start_node = StartNode(name="Start", inputs=[username_property])
end_node = EndNode(name="End")


# Control flow edges

from pyagentspec.flows.edges import ControlFlowEdge

control_flow_edges = [
    ControlFlowEdge(name="start_to_tool", from_node=start_node, to_node=tool_node),
    ControlFlowEdge(
        name="tool_to_orchestrator", from_node=tool_node, to_node=orchestrator_agent_node
    ),
    ControlFlowEdge(
        name="orchestrator_to_branching", from_node=orchestrator_agent_node, to_node=branching_node
    ),
    ControlFlowEdge(
        name="branching_to_network",
        from_node=branching_node,
        to_node=network_agent_node,
        from_branch="network",
    ),
    ControlFlowEdge(
        name="branching_to_device",
        from_node=branching_node,
        to_node=device_agent_node,
        from_branch="device",
    ),
    ControlFlowEdge(
        name="branching_to_account",
        from_node=branching_node,
        to_node=account_agent_node,
        from_branch="account",
    ),
    ControlFlowEdge(
        name="branching_to_end", from_node=branching_node, to_node=end_node, from_branch="default"
    ),
    ControlFlowEdge(
        name="network_to_orchestrator",
        from_node=network_agent_node,
        to_node=orchestrator_agent_node,
    ),
    ControlFlowEdge(
        name="device_to_orchestrator", from_node=device_agent_node, to_node=orchestrator_agent_node
    ),
    ControlFlowEdge(
        name="account_to_orchestrator",
        from_node=account_agent_node,
        to_node=orchestrator_agent_node,
    ),
]


# Data flow edges

from pyagentspec.flows.edges import DataFlowEdge

data_flow_edges = [
    DataFlowEdge(
        name="start_to_tool_username",
        source_node=start_node,
        source_output="username",
        destination_node=tool_node,
        destination_input="username",
    ),
    DataFlowEdge(
        name="tool_to_orchestrator_user_information",
        source_node=tool_node,
        source_output="user_information",
        destination_node=orchestrator_agent_node,
        destination_input="user_information",
    ),
    DataFlowEdge(
        name="tool_to_orchestrator_topic",
        source_node=orchestrator_agent_node,
        source_output="topic",
        destination_node=branching_node,
        destination_input="topic",
    ),
    DataFlowEdge(
        name="orchestrator_to_device_conversation_summary",
        source_node=orchestrator_agent_node,
        source_output="conversation_summary",
        destination_node=device_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="orchestrator_to_network_conversation_summary",
        source_node=orchestrator_agent_node,
        source_output="conversation_summary",
        destination_node=network_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="orchestrator_to_account_conversation_summary",
        source_node=orchestrator_agent_node,
        source_output="conversation_summary",
        destination_node=account_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="network_to_orchestrator_conversation_summary",
        source_node=network_agent_node,
        source_output="conversation_summary",
        destination_node=orchestrator_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="device_to_orchestrator_conversation_summary",
        source_node=device_agent_node,
        source_output="conversation_summary",
        destination_node=orchestrator_agent_node,
        destination_input="conversation_summary",
    ),
    DataFlowEdge(
        name="account_to_orchestrator_conversation_summary",
        source_node=account_agent_node,
        source_output="conversation_summary",
        destination_node=orchestrator_agent_node,
        destination_input="conversation_summary",
    ),
]


# Flow

from pyagentspec.flows.flow import Flow

flow = Flow(
    name="Oracle IT Assistant Flow",
    description="Flow of the Oracle IT assistant",
    start_node=start_node,
    nodes=[
        start_node,
        tool_node,
        orchestrator_agent_node,
        branching_node,
        network_agent_node,
        device_agent_node,
        account_agent_node,
        end_node,
    ],
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
    inputs=[username_property],
)


# Serialization

from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)
# .. end-full-code:
