# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

# Step 1. Setting up the environment

# Step 2. Creating your MCP Server

# Step 3. Utils for the Flow

from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.node import Node

def create_control_flow_edge(from_node: Node, to_node: Node, from_branch: str | None = None) -> ControlFlowEdge:
    return ControlFlowEdge(
        name=f"{from_node.name}_{to_node.name}_{from_branch}",
        from_node=from_node,
        to_node=to_node,
        from_branch=from_branch,
    )

def create_data_flow_edge(source_node: Node, destination_node: Node, property_name: str) -> DataFlowEdge:
    return DataFlowEdge(
        name=f"{source_node.name}_{destination_node.name}_{property_name}",
        source_node=source_node,
        source_output=property_name,
        destination_node=destination_node,
        destination_input=property_name,
    )

data_flow_edges: list[DataFlowEdge] = []
control_flow_edges: list[ControlFlowEdge] = []
flow_nodes: list[Node] = []

# Step 4. Defining the Detection Tools

from pyagentspec.property import DictProperty, ListProperty, StringProperty
from pyagentspec.mcp.clienttransport import StreamableHTTPTransport
from pyagentspec.mcp.tools import MCPTool


# Defining the needed AgentSpec property objects
# The tenancy ID input by the user
tenancy_id_property = StringProperty(title="tenancy_id", description='The tenancy identifier.')
# The tenancy graph containing the resources from which the findings can be computed
tenancy_graph_property = DictProperty(title="tenancy_graph", description="Tenancy of the graph resources", value_type=StringProperty())
# The list of findings
findings_property = ListProperty(title="findings", description="List of findings", item_type=DictProperty(title="finding", value_type=StringProperty(title="field")))
# Whether findings were detected
has_findings_property = StringProperty(title="has_findings", description='Whether detection yielded findings.')

# This is unauthenticated for tutorial purposes, so avoid in a production scenario
mcp_transport = StreamableHTTPTransport(
    name="CyberSecurity MCP Server Transport",
    description="Transport for the CyberSecurity MCP server",
    url="http://localhost:8081/mcp"
)

# All tools correspond to a tool in the MCP server
retrieve_tenancy_graph_tool = MCPTool(
    name="retrieve_tenancy_graph",
    description="Tool to retrieve tenancy graph",
    client_transport=mcp_transport,
    inputs=[tenancy_id_property],
    outputs=[tenancy_graph_property]
)

find_networking_vulnerabilities_tool = MCPTool(
    name="find_networking_vulnerabilities",
    description="Tool to find networking vulnerabilities",
    client_transport=mcp_transport,
    inputs=[tenancy_graph_property],
    outputs=[findings_property]
)

find_sensitive_files_tool = MCPTool(
    name="find_sensitive_files",
    description="Tool to find sensitive files in NFS and OS",
    client_transport=mcp_transport,
    inputs=[tenancy_graph_property, findings_property],
    outputs=[findings_property]
)

evaluate_exploits_tool = MCPTool(
    name="evaluate_exploits",
    description="Tool to safely try exploits",
    client_transport=mcp_transport,
    inputs=[tenancy_graph_property, findings_property],
    outputs=[findings_property]
)

has_findings_tool = MCPTool(
    name="has_findings",
    description="Tool to evaluate whether there are findings",
    client_transport=mcp_transport,
    inputs=[findings_property],
    outputs=[has_findings_property]
)

# Step 5. Beginning of the Flow

from pyagentspec.flows.nodes import EndNode, InputMessageNode, OutputMessageNode, StartNode

start_node = StartNode(name="start_node")
exit_node = EndNode(name="exit_node")

flow_nodes.extend([start_node, exit_node])

presentation_message_node = OutputMessageNode(
    name="presentation_message",
    message="Hi, I am the CyberSecurity Assistant. Please insert the ID of the Tenancy you would like to investigate."
)

get_tenancy_id_node = InputMessageNode(
    name="get_tenancy_id",
    outputs=[tenancy_id_property],
)

flow_nodes.extend([presentation_message_node, get_tenancy_id_node])

control_flow_edges.extend(
    [
        # From start to opening message
        create_control_flow_edge(start_node, presentation_message_node),
        # From opening message to user input
        create_control_flow_edge(presentation_message_node, get_tenancy_id_node),
    ]
)

# Step 6. Detection Sequence

from pyagentspec.flows.nodes import ToolNode

def create_tool_node(tool: MCPTool) -> ToolNode:
    return ToolNode(
        name=f"{tool.name} Node",
        description=tool.description,
        tool=tool
    )

retrieve_tenancy_graph_tool_node = create_tool_node(retrieve_tenancy_graph_tool)
find_networking_vulnerabilities_tool_node =  create_tool_node(find_networking_vulnerabilities_tool)
find_sensitive_files_tool_node = create_tool_node(find_sensitive_files_tool)
evaluate_exploits_tool_node = create_tool_node(evaluate_exploits_tool)
has_findings_tool_node = create_tool_node(has_findings_tool)

flow_nodes.extend([retrieve_tenancy_graph_tool_node, find_networking_vulnerabilities_tool_node, find_sensitive_files_tool_node, evaluate_exploits_tool_node, has_findings_tool_node])

control_flow_edges.extend(
    [
        # From user input to first tool
        create_control_flow_edge(get_tenancy_id_node, retrieve_tenancy_graph_tool_node),
        # Cascading tool calls
        create_control_flow_edge(retrieve_tenancy_graph_tool_node, find_networking_vulnerabilities_tool_node),
        create_control_flow_edge(find_networking_vulnerabilities_tool_node, find_sensitive_files_tool_node),
        create_control_flow_edge(find_sensitive_files_tool_node, evaluate_exploits_tool_node),
        create_control_flow_edge(evaluate_exploits_tool_node, has_findings_tool_node)
    ]
)

# Inputs and outputs will need to correspond to what is specified in the individual tools, and thus also to what the MCP server tools need
data_flow_edges.extend(
    [
        # Need the tenancy ID to retrieve the tenancy graph
        create_data_flow_edge(get_tenancy_id_node, retrieve_tenancy_graph_tool_node, "tenancy_id"),
        # Need the tenancy graph to compute the first findings
        create_data_flow_edge(retrieve_tenancy_graph_tool_node, find_networking_vulnerabilities_tool_node, "tenancy_graph"),
        # Second tool still needs the tenancy graph and enriches existing list of findings
        create_data_flow_edge(retrieve_tenancy_graph_tool_node, find_sensitive_files_tool_node, "tenancy_graph"),
        create_data_flow_edge(find_networking_vulnerabilities_tool_node, find_sensitive_files_tool_node, "findings"),
        # Last tool evaluates exploits on computed findings and still needs tenancy graph
        create_data_flow_edge(retrieve_tenancy_graph_tool_node, evaluate_exploits_tool_node, "tenancy_graph"),
        create_data_flow_edge(find_sensitive_files_tool_node, evaluate_exploits_tool_node, "findings"),
        create_data_flow_edge(evaluate_exploits_tool_node, has_findings_tool_node, "findings")
    ]
)

# Step 7. First Branching

from pyagentspec.flows.nodes import BranchingNode

# Maps the 'yes' outcome to the next node (the output message)
# or goes back to tenancy ID request by default
has_findings_branching_node = BranchingNode(
    name="has_findings_branch",
    description="Exit the flow if the are no detected findings",
    mapping={
        "yes": "has_findings",
    },
    inputs=[has_findings_property],
)

no_findings_output_node = OutputMessageNode(
    name="no_findings_message",
    message="There were no findings computed. Please input another tenancy ID."
)

flow_nodes.extend([has_findings_branching_node, no_findings_output_node])

control_flow_edges.extend(
    [
        # From last tool to branching node
        create_control_flow_edge(has_findings_tool_node, has_findings_branching_node),
        # Go to no findings message by default (will specify alternative behavior later) 
        create_control_flow_edge(has_findings_branching_node, no_findings_output_node, from_branch="default"),
        # From message to beginning
        create_control_flow_edge(no_findings_output_node, get_tenancy_id_node)
    ]
)

# Fetches boolean to see if there are findings
data_flow_edges.append(create_data_flow_edge(has_findings_tool_node, has_findings_branching_node, "has_findings"))


# Step 8: Defining the Summarization LLM

from pyagentspec.llms import VllmConfig
from pyagentspec.flows.nodes import LlmNode


# We will use a VllmConfig for this example
llm_config = VllmConfig(
    name="meta.llama-3.3-70b-instruct",
    model_id="/storage/models/Llama-3.3-70B-Instruct",
    url="model_id",
)

# In the prompt, the {{<input>}} token is used to pass the inputs
# and is mandatory if the Node specifies inputs 
SUMMARIZATION_INSTRUCTIONS = """
You are a CyberSecurity expert tasked to summarize security vulnerability findings.
You will receive a list of findings in the format:
- resource: <affected_resource_id>
- tenancy: <tenancy_id>
- summary: <summary, starts empty>
- verified: <boolean describing if the finding yielded a verified exploit>
- vuln_type: <'exposed_port', 'sensitive_object_storage_file', 'sensitive_nfs_file'>
- metadata: <added by tools>
- additional_details: <added by tools>
- severity: <ignore for now>

Here's the list of findings:
{{findings}}

Populate the summary field with a description of why the findings is problematic and what an attacker could do with it. Use less than 100 for each summary.
Also, return the updated findings.
"""

# Remember to specify inputs ad outputs
summarization_node = LlmNode(
    name="summarize_findings_node",
    llm_config=llm_config,
    prompt_template=SUMMARIZATION_INSTRUCTIONS,
    inputs=[findings_property],
    outputs=[findings_property]
)

# Notify user that next step is triaging
going_to_triage_output_node = OutputMessageNode(
    name="going_to_triage_message",
    message="Moving to triaging Agent. Please wait for triaging to finish."
)

flow_nodes.extend([summarization_node, going_to_triage_output_node])

control_flow_edges.extend(
    [   
        # summarize if there are findings
        create_control_flow_edge(has_findings_branching_node, summarization_node, from_branch="has_findings"),
        # when finished, notify the user that triaging is next
        create_control_flow_edge(summarization_node, going_to_triage_output_node)
    ]
)

# Feed findings to summarization node
data_flow_edges.append(create_data_flow_edge(evaluate_exploits_tool_node, summarization_node, "findings"))


# Step 9: Triaging Agent

from pyagentspec.agent import Agent
from pyagentspec.flows.nodes import AgentNode

find_lateral_movement_from_user = MCPTool(
    name="find_lateral_movement_from_user",
    description="Tool to evaluate where a compromised user has rights",
    client_transport=mcp_transport,
    inputs=[tenancy_graph_property, findings_property],
    outputs=[findings_property]
)

find_networking_lateral_movement = MCPTool(
    name="find_networking_lateral_movement",
    description="Tool to evaluate where an attacker could reach from a compromised IP",
    client_transport=mcp_transport,
    inputs=[tenancy_graph_property, findings_property],
    outputs=[findings_property]
)

TRIAGING_INSTRUCTIONS = """
You are an agent designed to triaging findings of security vulnerabilities within a Cloud tenancy.
Given a list of findings and a tenancy graph, you have to evaluate the possibilities of moving laterally from the findings entrypoints and their blast radius.

Here's the list of findings:
{{findings}}

Here's the tenancy graph:
{{tenancy_graph}}

1) Your workflow (starting from the list of findings and the tenancy graph)
- For each finding where Verified is True:
    - If finding is of type 'sensitive_object_storage_file' OR 'sensitive_nfs_file':
        1) Call find_lateral_movement_from_user(finding_metadata)
        2) Extract additional_details
    - if finding is of type 'exposed_port':
        1) Call find_networking_lateral_movement(finding_metadata)
        2) Extract additional_details

- For each finding where Verified is False:
    - Assign LOW Severity
    - Assign 'Finding could not be exploited' as Severity_Explanation

2) For the output, for each finding use the data in the "metadata" and "additional_details" fields to:
    - summarize the blast radius and lateral movement possibilities for the finding in less than 100 words
    - assign a severity in the severity field, either, 'LOW', 'MEDIUM' or 'HIGH'
    - mind that if a finding is verified, it is likely to have a higher severity

Then output the updated findings list with a small summary about the issues of the tenancy.
""".strip()

triaging_agent = Agent(
    name="Triaging_Agent",
    description="Agent equipped with tools to assist with computing blast radius and lateral movement possibilities from Cloud tenancy findings",
    llm_config=llm_config,
    tools=[find_lateral_movement_from_user, find_networking_lateral_movement],
    system_prompt=TRIAGING_INSTRUCTIONS,
    inputs=[findings_property, tenancy_graph_property],
    outputs=[findings_property]
)

triaging_agent_node = AgentNode(
    name="triaging_agent_node",
    agent=triaging_agent
)

# Tell the user to input 'yes' for reporting step
request_confirmation_message_node = OutputMessageNode(
    name="request_confirmation_message",
    message="Would you like to report the findings to their respective tenancy owner via mail? Enter 'yes' if that is the case, otherwise Flow will terminate."
)


flow_nodes.extend([triaging_agent_node, request_confirmation_message_node])

control_flow_edges.extend(
    [   
        # From previous message to the triaging agent
        create_control_flow_edge(going_to_triage_output_node, triaging_agent_node),
        create_control_flow_edge(triaging_agent_node, request_confirmation_message_node)
    ]
)

data_flow_edges.extend(
    [   
        # Triaging agent needs tenancy graph and findings
        create_data_flow_edge(retrieve_tenancy_graph_tool_node, triaging_agent_node, "tenancy_graph"),
        create_data_flow_edge(summarization_node, triaging_agent_node, "findings")
    ]
)

# Step 10: Reporting Sequence

# A simple string property containing the user's confirmation
confirmation_property = StringProperty(title="confirmation", description='Confirmation for reporting.')

confirmation_input_node = InputMessageNode(
    name="get_confirmation",
    outputs=[confirmation_property],
)

reporting_branching_node = BranchingNode(
    name="reporting_decision",
    description="Report findings if the users decides to do so",
    mapping={
        "yes": "reporting",
    },
    inputs=[confirmation_property],
)

reporting_tool = MCPTool(
    name="report_findings",
    description="Finds the owner of a finding and reports it.",
    client_transport=mcp_transport,
    inputs=[findings_property]
)

reporting_node = ToolNode(
    name="reporting_node",
    description="Sends mail to the finding's tenancy owner.",
    tool=reporting_tool
)

flow_nodes.extend([confirmation_input_node, reporting_branching_node, reporting_node])

control_flow_edges.extend(
    [
        create_control_flow_edge(request_confirmation_message_node, confirmation_input_node),
        create_control_flow_edge(confirmation_input_node, reporting_branching_node),
        # If the user writes 'yes', move to the reporting tool node
        create_control_flow_edge(reporting_branching_node, reporting_node, from_branch="reporting"),
        # Otherwise exit
        create_control_flow_edge(reporting_branching_node, exit_node, from_branch="default"),
        # Exit after reporting
        create_control_flow_edge(reporting_node, exit_node)
    ]
)

data_flow_edges.extend(
    [
        # Pass confirmation to branching
        create_data_flow_edge(confirmation_input_node, reporting_branching_node, "confirmation"),
        # Pass findings to the reporting tool node
        create_data_flow_edge(triaging_agent_node, reporting_node, "findings")
    ]
)

# Step 11: Creating, Exporting, and Running the Flow
from pyagentspec.flows.flow import Flow
from pyagentspec.serialization import AgentSpecSerializer

flow = Flow(
    name="CyberSec_Assistant_Flow",
    start_node=start_node,
    nodes=flow_nodes,
    control_flow_connections=control_flow_edges,
    data_flow_connections=data_flow_edges,
)

serialized_flow = AgentSpecSerializer().to_json(flow)

# from wayflowcore.agentspec import AgentSpecLoader
# from wayflowcore.flow import Flow as RuntimeFlow
# from wayflowcore.executors.executionstatus import UserMessageRequestStatus
# from wayflowcore.mcp import enable_mcp_without_auth

# Needed as in this example we do not authenticate against the MCP server
# enable_mcp_without_auth()
# flow: RuntimeFlow = AgentSpecLoader().load_json(serialized_flow)

# conversation = flow.start_conversation()
# while True:
#     status = conversation.execute()
#     if not isinstance(status, UserMessageRequestStatus):
#         break
#     assistant_reply = conversation.get_last_message()
#     if assistant_reply is not None:
#         print("\nAssistant >>>", assistant_reply.content)
#     user_input = input("\nUser >>> ")
#     conversation.append_user_message(user_input)


# import asyncio
# from langchain_core.runnables import RunnableConfig
# from langgraph.types import Command
# from langgraph.checkpoint.memory import MemorySaver
# from langgraph_agentspec_adapter import AgentSpecLoader as LangGraphLoader

# async def conversation_loop():
#     config = RunnableConfig({"configurable": {"thread_id": "1"}})
#     assistant = LangGraphLoader(checkpointer=MemorySaver()).load_json(serialized_flow)
#     result = await assistant.ainvoke({"messages": []}, config=config)
#     while True:
#         if result.get("__interrupt__", None) is None:
#             last_message = result["messages"][-1]
#             print("\nAssistant >>>", last_message.content)
#             break
#         last_message = result["messages"][-1]
#         print("\nAssistant >>>", last_message.content)
#         user_input = input("\nUser >>> ")
#         result = await assistant.ainvoke(Command(resume=user_input), config=config)

# asyncio.run(conversation_loop())