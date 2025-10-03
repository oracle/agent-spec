# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl) or Apache License
# 2.0 (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0), at your option.

# isort:skip_file
# fmt: off
# mypy: ignore-errors

from pyagentspec.llms import VllmConfig
llm_config = VllmConfig(
    name="llm",
    model_id="model_id",
    url="url",
)

# .. start-##Create_a_MCP_Server
from mcp.server.fastmcp import FastMCP

PAYSLIPS = [
    {
        "Amount": 7612,
        "Currency": "USD",
        "PeriodStartDate": "2025/05/15",
        "PeriodEndDate": "2025/06/15",
        "PaymentDate": "",
        "DocumentId": 2,
        "PersonId": 2,
    },
    {
        "Amount": 5000,
        "Currency": "CHF",
        "PeriodStartDate": "2024/05/01",
        "PeriodEndDate": "2024/06/01",
        "PaymentDate": "2024/05/15",
        "DocumentId": 1,
        "PersonId": 1,
    },
    {
        "Amount": 10000,
        "Currency": "EUR",
        "PeriodStartDate": "2025/06/15",
        "PeriodEndDate": "2025/10/15",
        "PaymentDate": "",
        "DocumentsId": 3,
        "PersonId": 3,
    },
]

def create_server(host: str, port: int):
    """Create and configure the MCP server"""
    server = FastMCP(
        name="Example MCP Server",
        instructions="A MCP Server.",
        host=host,
        port=port,
    )

    @server.tool(description="Return session details for the current user")
    def get_user_session():
        print("called get_user_session")
        return {
            "PersonId": "1",
            "Username": "Bob.b",
            "DisplayName": "Bob B",
        }

    @server.tool(description="Return payslip details for a given PersonId")
    def get_payslips(PersonId: int):
        return [payslip for payslip in PAYSLIPS if payslip["PersonId"] == int(PersonId)]

    return server


def start_mcp_server() -> str:
    host: str = "localhost"
    port: int = 8080
    server = create_server(host=host, port=port)
    server.run(transport="sse")

    return f"http://{host}:{port}/sse"

# mcp_server_url = start_mcp_server() # <--- Move the code above to a separate file then uncomment
# .. end-##Create_a_MCP_Server
# .. start-##_Imports_for_this_guide

from pyagentspec.agent import Agent
from pyagentspec.flows.edges import ControlFlowEdge, DataFlowEdge
from pyagentspec.flows.flow import Flow
from pyagentspec.flows.nodes import EndNode, StartNode, ToolNode
from pyagentspec.mcp import MCPTool, SSETransport
from pyagentspec.property import StringProperty

mcp_server_url = f"http://localhost:8080/sse" # change to your own URL
# .. end-##_Imports_for_this_guide
# .. start-##_Connecting_an_agent_to_the_MCP_server
mcp_client = SSETransport(name="MCP Client", url=mcp_server_url)

get_user_session_tool = MCPTool(
    client_transport=mcp_client,
    description="Return session details for the current user",
    name="get_user_session",
)
get_payslips_tool = MCPTool(
    client_transport=mcp_client,
    description="Return payslip details for a given PersonId",
    name="get_payslips",
)
agent = Agent(
    name="Agent using MCP",
    llm_config=llm_config,
    system_prompt="Use tools at your disposal to assist the user.",
    tools=[get_user_session_tool, get_payslips_tool]
)
# .. end-##_Connecting_an_agent_to_the_MCP_server
# .. start-##_Export_Agent_to_IR
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(agent)
# .. end-##_Export_Agent_to_IR
# .. start-##_Connecting_a_flow_to_the_MCP_server

start_node = StartNode(name="start")
user_info_property = StringProperty(title="user_info")
get_user_session_tool = MCPTool(
    client_transport=mcp_client,
    name="get_user_session",
    description="Return session details for the current user",
    outputs=[user_info_property]
)
mcptool_node = ToolNode(
    name="mcp_tool",
    tool=get_user_session_tool,
)
end_node = EndNode(name="end", outputs=[user_info_property])

flow = Flow(
    name="Flow using MCP",
    start_node=start_node,
    nodes=[start_node, mcptool_node, end_node],
    control_flow_connections=[
        ControlFlowEdge(
            name="start->mcptool",
            from_node=start_node,
            to_node=mcptool_node
        ),
        ControlFlowEdge(
            name="mcptool->end",
            from_node=mcptool_node,
            to_node=end_node
        ),
    ],
    data_flow_connections=[
        DataFlowEdge(
            name="user_info",
            source_node=mcptool_node,
            source_output="user_info",
            destination_node=end_node,
            destination_input="user_info",
        )
    ]
)
# .. end-##_Connecting_a_flow_to_the_MCP_server
# .. start-##_Export_Flow_to_IR
from pyagentspec.serialization import AgentSpecSerializer

serialized_assistant = AgentSpecSerializer().to_json(flow)
# .. end-##_Export_Flow_to_IR
