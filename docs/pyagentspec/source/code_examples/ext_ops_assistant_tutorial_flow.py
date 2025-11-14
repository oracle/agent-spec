# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

"""
Code example for the tutorial:
Building an LLM Operations Flow-based Agent with Open Agent Spec and WayFlow
"""

# Step 1. Setting up the environment
# Make sure `pyagentspec` and `wayflowcore` are installed to run this code example.

# python -m venv venv-agentspec
# source venv-agentspec/bin/activate # On Windows: venv-agentspec\Scripts\activate
# pip install pyagentspec wayflowcore


# Step 1.5 Getting the tools from the previous tutorial

from ext_ops_assistant_tutorial_agent import (
    read_jira_ticket,
    read_jira_ticket_tool,
    read_runbook,
    read_runbook_tool,
    get_alarm_status,
    get_alarm_status_tool,
    read_logs,
    read_logs_tool,
)

# Step 2. Defining the basics

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.node import Node

def create_data_flow_edge(source_node: Node, destination_node: Node, property_name: str) -> DataFlowEdge:
    return DataFlowEdge(
        name=f"{source_node.name}_{destination_node.name}_{property_name}",
        source_node=source_node,
        source_output=property_name,
        destination_node=destination_node,
        destination_input=property_name,
    )

def create_control_flow_edge(from_node: Node, to_node: Node, from_branch: str | None = None) -> ControlFlowEdge:
    return ControlFlowEdge(
        name=f"{from_node.name}_{to_node.name}_{from_branch}",
        from_node=from_node,
        to_node=to_node,
        from_branch=from_branch,
    )

data_flow_edges: list[DataFlowEdge] = []
control_flow_edges: list[ControlFlowEdge] = []
flow_nodes: list[Node] = []

# Step 3. Head and tail of the Flow

from pyagentspec.flows.nodes import EndNode, StartNode

start_node = StartNode(name="start_node")
exit_node = EndNode(name="exit_node")

flow_nodes.extend([start_node, exit_node])

# Step 4. Getting the Jira Issue ID from the user

from pyagentspec.flows.nodes import InputMessageNode, OutputMessageNode
from pyagentspec.property import StringProperty

jira_issue_id_property = StringProperty(title="jira_issue_id", description='The Jira issue key, e.g., "INC-12345"')

presentation_message_node = OutputMessageNode(
    name="presentation_message",
    message=(
        "Hi, I am the Operations Assistant. "
        "Please insert the Jira issue ID you would like to investigate. "
        "Write `exit` if you don't want to proceed."
    ),
)

get_jira_issue_node = InputMessageNode(
    name="get_jira_issue",
    # We rename the output to "jira_issue_id" so that it better represents the information it contains
    outputs=[jira_issue_id_property],
)

flow_nodes.extend([presentation_message_node, get_jira_issue_node])

control_flow_edges.extend(
    [
        create_control_flow_edge(start_node, presentation_message_node),
        create_control_flow_edge(presentation_message_node, get_jira_issue_node),
    ]
)

# Step 5. The first branching

from pyagentspec.flows.nodes import BranchingNode, ToolNode

exit_branching_node = BranchingNode(
    name="exit_branching",
    description="Exit the flow if the user writes `exit`",
    mapping={"exit": "exit"},
    inputs=[jira_issue_id_property],
)

# First node of the `default` branch, we continue by reading the Jira ticket info
read_jira_ticket_tool_node = ToolNode(
    name="read_jira_ticket_tool_node",
    tool=read_jira_ticket_tool,
)

flow_nodes.extend([exit_branching_node, read_jira_ticket_tool_node])

control_flow_edges.extend(
    [
        # Edge that takes from the user input node to the branching one
        create_control_flow_edge(get_jira_issue_node, exit_branching_node),
        # Edge that takes from the branching node to the exit
        create_control_flow_edge(exit_branching_node, exit_node, from_branch="exit"),
        # Edge that takes from the branching node to the read Jira ticket
        create_control_flow_edge(exit_branching_node, read_jira_ticket_tool_node, from_branch="default"),
    ]
)

# Connect the Jira ticket ID information where it is needed
data_flow_edges.extend(
    [
        create_data_flow_edge(get_jira_issue_node, exit_branching_node, "jira_issue_id"),
        create_data_flow_edge(get_jira_issue_node, read_jira_ticket_tool_node, "jira_issue_id"),
    ]
)

# Step 6. The second branching

# Now we should wonder: was the jira issue found?
# - if it was, we continue gathering more info from the runbook, logs, etc.;
# - if it was not found, we loop back, and we ask the user to re-insert another ID.

was_jira_issue_found_branching_node = BranchingNode(
    name="was_jira_issue_found_branching",
    description="Continue if we found the jira ticket details, loop back if we did not",
    mapping={"Ticket not found": "not_found"},
    inputs=[StringProperty(title="incident_summary")],
)

flow_nodes.append(was_jira_issue_found_branching_node)

control_flow_edges.append(
    create_control_flow_edge(read_jira_ticket_tool_node, was_jira_issue_found_branching_node)
)

data_flow_edges.append(
    create_data_flow_edge(read_jira_ticket_tool_node, was_jira_issue_found_branching_node, "incident_summary")
)

# Step 7. Looping back

# Jira issue not found, loop back informing the user

jira_issue_not_found_output_node = OutputMessageNode(
    name="jira_issue_not_found",
    message="Jira issue with ID `{{jira_issue_id}}` was not found. Please try again or type 'exit' to quit.",
    inputs=[jira_issue_id_property],
)

flow_nodes.append(jira_issue_not_found_output_node)

control_flow_edges.extend(
    [
        create_control_flow_edge(was_jira_issue_found_branching_node, jira_issue_not_found_output_node, from_branch="not_found"),
        create_control_flow_edge(jira_issue_not_found_output_node, get_jira_issue_node),
    ]
)

data_flow_edges.append(
    create_data_flow_edge(get_jira_issue_node, jira_issue_not_found_output_node, "jira_issue_id")
)

# Step 8. Gathering all the issue information

from pyagentspec.tools import ServerTool

# Jira issue found, we can continue by parsing the Jira issue summary
# to extract the information we need for the investigation tools

parse_incident_summary_tool = ServerTool(
    name="parse_incident_summary",
    description="Parse an incident summary string to extract relevant information in a structured format",
    inputs=[
        StringProperty(
            title="incident_summary",
            description="A human-readable incident summary including scope, runbook, and time window."
        )
    ],
    outputs=[
        # We extract all the information we need in the tools we use for the investigation
        StringProperty(title="from_project", description="Owning project (e.g., 'payments', 'inventory')", default=""),
        StringProperty(title="from_fleet", description="Service/fleet name", default=""),
        StringProperty(title="from_compartment", description="Environment/compartment (e.g., 'prod')", default=""),
        StringProperty(title="from_region", description="Cloud region", default=""),
        StringProperty(title="log_level", description="Minimum log level (string)", default=""),
        StringProperty(title="start_ts", description="ISO8601 start timestamp", default=""),
        StringProperty(title="end_ts", description="ISO8601 end timestamp", default=""),
        StringProperty(title="runbook_name", description="The canonical runbook name.", default=""),
        StringProperty(title="alarm_id", description="Alarm identifier (e.g., 'cw:payments-latency-high')", default=""),
    ],
)

def parse_incident_summary(incident_summary: str) -> dict[str, str]:
    import re

    parsed_summary = {}
    # Extract from Scope the information stored in there
    scope_match = re.search(
        r'Scope:\s*Project=([^,]+),\s*Fleet=([^,]+),\s*Compartment=([^,]+),\s*Region=([^\n]+)',
        incident_summary,
    )
    if scope_match:
        parsed_summary['from_project'] = scope_match.group(1).strip()
        parsed_summary['from_fleet'] = scope_match.group(2).strip()
        parsed_summary['from_compartment'] = scope_match.group(3).strip()
        parsed_summary['from_region'] = scope_match.group(4).strip()

    # Set log level (assuming DEBUG to retrieve everything)
    parsed_summary['log_level'] = 'DEBUG'

    # Extract suspected window timestamps
    window_match = re.search(r'Suspected window:\s*([^\s]+)\s*to\s*([^\s]+)', incident_summary)
    if window_match:
        parsed_summary['start_ts'] = window_match.group(1)
        parsed_summary['end_ts'] = window_match.group(2)

    # Extract runbook name
    runbook_match = re.search(r'Suggested runbook:\s*([^\n]+)', incident_summary)
    if runbook_match:
        parsed_summary['runbook_name'] = runbook_match.group(1).strip()

    # Extract alarm ID
    alarm_match = re.search(r'Detected by:\s*Alarm\s*([^\n]+)', incident_summary)
    if alarm_match:
        parsed_summary['alarm_id'] = alarm_match.group(1).strip()

    return parsed_summary

parse_incident_summary_tool_node = ToolNode(
    name="parse_incident_summary_tool_node",
    tool=parse_incident_summary_tool,
)

flow_nodes.append(parse_incident_summary_tool_node)

control_flow_edges.append(
    create_control_flow_edge(was_jira_issue_found_branching_node, parse_incident_summary_tool_node, from_branch="default")
)

data_flow_edges.append(
    create_data_flow_edge(read_jira_ticket_tool_node, parse_incident_summary_tool_node, "incident_summary")
)

# Now that we parsed the Jira issue information, we can gather more information with the 3 known tools

from pyagentspec.flows.nodes import ToolNode

read_runbook_tool_node = ToolNode(
    name="read_runbook_tool_node",
    tool=read_runbook_tool,
)

get_alarm_status_tool_node = ToolNode(
    name="get_alarm_status_tool_node",
    tool=get_alarm_status_tool,
)

read_logs_tool_node = ToolNode(
    name="read_logs_tool_node",
    tool=read_logs_tool,
)

flow_nodes.extend([read_runbook_tool_node, get_alarm_status_tool_node, read_logs_tool_node])

control_flow_edges.extend(
    [
        # Sequentially call the tools
        create_control_flow_edge(parse_incident_summary_tool_node, read_runbook_tool_node),
        create_control_flow_edge(read_runbook_tool_node, get_alarm_status_tool_node),
        create_control_flow_edge(get_alarm_status_tool_node, read_logs_tool_node),
    ]
)

data_flow_edges.extend(
    [
        # Data edges for the read_runbook_tool_node
        create_data_flow_edge(parse_incident_summary_tool_node, read_runbook_tool_node, "runbook_name"),
        # Data edges for the get_alarm_status_tool_node
        create_data_flow_edge(parse_incident_summary_tool_node, get_alarm_status_tool_node, "alarm_id"),
        # One of the property names does not match between source and destination (`from_region` vs `region`)
        # With data flow edges this is not a problem, we can link them explicitly
        DataFlowEdge(
            name="parse_incident_summary-read_logs_tool-region",
            source_node=parse_incident_summary_tool_node,
            source_output="from_region",
            destination_node=get_alarm_status_tool_node,
            destination_input="region",
        ),
        # Data edges for the read_logs_tool_node
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "from_project"),
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "from_fleet"),
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "from_compartment"),
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "from_region"),
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "log_level"),
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "start_ts"),
        create_data_flow_edge(parse_incident_summary_tool_node, read_logs_tool_node, "end_ts"),
    ]
)

# Step 9. Defining the final conversational agent

CUSTOM_INSTRUCTIONS = """
# Agent background

You are an LLM-based operations assistant.
You have to help the operator solve the issue with Jira ID: {{jira_issue_id}}

# Information available

## Runbook

{{runbook_markdown}}

## Alarm Status

{{alarm_status}}

## Logs

{{log_lines}}

# Agent instructions

1) Form a hypothesis and recommended actions
    - Synthesize alarm status, logs, runbook guidance, and notes from the ticket.
    - Provide a clear, probable cause hypothesis with confidence qualifiers.
    - Recommend next steps aligned to the runbook.

2) In the first message, report results in a structured format.
Use this output template:
- Incident: <jira_issue_id>
- Summary: <one-liner from Jira or your concise rewrite>
- Scope: Project=<project>, Fleet=<fleet>, Compartment=<compartment>, Region=<region>
- Time window: <start_ts> to <end_ts> (from ticket or adjusted)
- Alarm: <alarm_id> — Status: <firing|not firing|unknown>
- Evidence:
- Ticket highlights: <key notes, deployments, flags>
- Logs (top 3-6 lines or patterns): <short bullets with timestamps and error types>
- Runbook: <name> — Key steps considered: <bulleted list of most relevant steps>
- Hypothesis: <probable cause and rationale>
- Recommended actions: <ordered list; include rollback/failover/tuning/monitoring>
- Validation: <what success looks like (e.g., P95 < threshold for X min)>
- Open questions/next checks: <only if needed>
- Artifacts: <any identifiers: deployment IDs, feature flags, trace IDs seen in logs>

3) Follow up and assist the users by answering additional questions they might have until
they tell you that they have solved their issue.
""".strip()

from pyagentspec.agent import Agent
from pyagentspec.flows.nodes import AgentNode
from pyagentspec.llms import OpenAiConfig

llm_config = OpenAiConfig(
    name="openai-llm",
    model_id="model-id", # e.g. "gpt-4.1"
)

agent = Agent(
    name="Operator_Assistant",
    llm_config=llm_config,
    system_prompt=CUSTOM_INSTRUCTIONS
)

agent_node = AgentNode(
    name="operator_assistant_node",
    agent=agent,
)

flow_nodes.append(agent_node)

control_flow_edges.extend(
    [
        create_control_flow_edge(read_logs_tool_node, agent_node),
        create_control_flow_edge(agent_node, exit_node),
    ]
)

data_flow_edges.extend(
    [
        create_data_flow_edge(get_jira_issue_node, agent_node, "jira_issue_id"),
        create_data_flow_edge(read_runbook_tool_node, agent_node, "runbook_markdown"),
        create_data_flow_edge(get_alarm_status_tool_node, agent_node, "alarm_status"),
        create_data_flow_edge(read_logs_tool_node, agent_node, "log_lines"),
    ]
)

# Step 10. Creating the final flow instance

from pyagentspec.flows.flow import Flow

flow = Flow(
    name="Operator_Assistant_Flow",
    start_node=start_node,
    nodes=flow_nodes,
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
)

# Step 11. Exporting the Agent Spec configuration

from pyagentspec.serialization import AgentSpecSerializer

serialized_flow = AgentSpecSerializer().to_json(flow)

# Step 12. Running the Flow

# if __name__ == '__main__':
#
#     ## With WayFlow
#     from wayflowcore.agentspec import AgentSpecLoader
#     from wayflowcore.flow import Flow as RuntimeFlow
#     from wayflowcore.executors.executionstatus import UserMessageRequestStatus
#
#     tool_registry = {
#         "read_jira_ticket": read_jira_ticket,
#         "read_logs": read_logs,
#         "read_runbook": read_runbook,
#         "get_alarm_status": get_alarm_status,
#         "parse_incident_summary": parse_incident_summary,
#     }
#
#     flow: RuntimeFlow = AgentSpecLoader(tool_registry=tool_registry).load_json(serialized_flow)
#     conversation = flow.start_conversation()
#
#     while True:
#         status = conversation.execute()
#         if not isinstance(status, UserMessageRequestStatus):
#             break
#         assistant_reply = conversation.get_last_message()
#         if assistant_reply is not None:
#             print("\nAssistant >>>", assistant_reply.content)
#         user_input = input("\nUser >>> ")
#         conversation.append_user_message(user_input)


# # Running the Flow with LangGraph
#
# from langchain_core.runnables import RunnableConfig
# from langgraph.types import Command
# from langgraph.checkpoint.memory import MemorySaver
# from langgraph_agentspec_adapter import AgentSpecLoader as LangGraphLoader
#
# assistant = LangGraphLoader(tool_registry=tool_registry, checkpointer=MemorySaver()).load_json(serialized_flow)
# config = RunnableConfig({"configurable": {"thread_id": "1"}})
# result = assistant.invoke({"messages": []}, config)
#
# while True:
#     if result.get("__interrupt__", None) is None:
#         last_message = result["messages"][-1]
#         print("\nAssistant >>>", last_message["content"])
#         break
#     last_message = result["messages"][-1]
#     print("\nAssistant >>>", last_message["content"])
#     user_input = input("\nUser >>> ")
#     result = assistant.invoke(Command(resume=user_input), config=config)
