# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

"""
Script to auto-generate the valid Agent Spec configurations for MCP.
"""

from pathlib import Path

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.llms import OpenAiCompatibleConfig
from pyagentspec.mcp import MCPTool, MCPToolBox, StreamableHTTPTransport
from pyagentspec.property import StringProperty
from pyagentspec.serialization import AgentSpecSerializer

llm_config = OpenAiCompatibleConfig(
    name="llm",
    model_id="Llama-4-Maverick",
    url="http://localhost:5006",
)

MCP_SERVER_URL = "http://localhost:5007/mcp"
DIR_PATH = Path(__file__).parent

mcp_client_transport = StreamableHTTPTransport(name="MCP Client", url=MCP_SERVER_URL)

user_info_property = StringProperty(title="user_info")
get_user_session_tool = MCPTool(
    client_transport=mcp_client_transport,
    name="get_user_session",
    description="Return session details for the current user",
    outputs=[user_info_property],
)

payslip_mcptoolbox = MCPToolBox(name="Payslip MCP ToolBox", client_transport=mcp_client_transport)

# Agent with MCP Tool
agent_with_mcptool = Agent(
    name="Agent using MCP",
    llm_config=llm_config,
    system_prompt="Use tools at your disposal to assist the user.",
    tools=[get_user_session_tool],
)

with open(DIR_PATH / "agent_with_1_mcptool.yaml", "w") as f:
    f.write(AgentSpecSerializer().to_yaml(agent_with_mcptool))


# Agent with MCP ToolBox
agent_with_mcptoolbox = Agent(
    name="Agent using MCP",
    llm_config=llm_config,
    system_prompt="Use tools at your disposal to assist the user.",
    toolboxes=[payslip_mcptoolbox],
)

with open(DIR_PATH / "agent_with_1_mcptoolbox.yaml", "w") as f:
    f.write(AgentSpecSerializer().to_yaml(agent_with_mcptoolbox))


# Flow with MCP Tool
start_node = StartNode(name="start")

mcptool_node = ToolNode(
    name="mcp_tool",
    tool=get_user_session_tool,
)
end_node = EndNode(name="end", outputs=[user_info_property])

flow_with_mcptool = Flow(
    name="Flow using MCP",
    start_node=start_node,
    nodes=[start_node, mcptool_node, end_node],
    control_flow_connections=[
        ControlFlowEdge(name="start->mcptool", from_node=start_node, to_node=mcptool_node),
        ControlFlowEdge(name="mcptool->end", from_node=mcptool_node, to_node=end_node),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="user_info",
            source_node=mcptool_node,
            source_output="user_info",
            destination_node=end_node,
            destination_input="user_info",
        )
    ],
)

with open(DIR_PATH / "flow_with_1_mcptool.yaml", "w") as f:
    f.write(AgentSpecSerializer().to_yaml(flow_with_mcptool))
