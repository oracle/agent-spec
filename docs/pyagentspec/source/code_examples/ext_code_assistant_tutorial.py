# Copyright (C) 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.
# isort:skip_file
# fmt: off
# mypy: ignore-errors

from pyagentspec.llms import OpenAiConfig

llm_config = OpenAiConfig(
    name="openai-llm",
    model_id="model-id", # e.g. "gpt-4.1"
)

# Defining the MCP server and tools
from pyagentspec.mcp.clienttransport import StreamableHTTPTransport
from pyagentspec.mcp.tools import MCPToolBox

mcp_server_url = "https://api.githubcopilot.com/mcp/"
headers = {"Authorization": f"Bearer {'GITHUB_PERSONAL_ACCESS_TOKEN'}"}

mcp_client = StreamableHTTPTransport(name="mcp_client", url=mcp_server_url, headers=headers)
mcp_toolbox = MCPToolBox(
    name="mcp_toolbox",
    client_transport=mcp_client,
    tool_filter=["list_pull_requests", "pull_request_read", "get_file_contents"],
)

CUSTOM_INSTRUCTIONS = """
You are an experienced code reviewer analyzing GitHub pull requests. Your primary goal is to understand proposed changes and deliver thorough, constructive feedback that enhances code quality and project alignment.

**Workflow:**
- **1. PR Overview:** Begin by gathering high-level details about the pull request.
- **2. Changed Files & Diffs:** Retrieve and review all modified files and code diffs.
- **3. Context Gathering:** Load any additional related files as needed (tests, configs). Review repository structure for context if necessary.
- **4. Code Analysis:** Examine the code for correctness, maintainability, standards compliance, performance, security, and architectural impact.
- **5. Inline Comments:** Provide specific, actionable comments on significant code changes, including suggestions for improvement where relevant.
- **6. Summary Assessment:** Conclude with a clear summary, using this structure:
    i. **Description:** What the PR does.
    ii. **Strengths:** What's done well.
    iii. **Opportunities for Improvement:** Areas to address.
    iv. **Additional Suggestions:** Any further feedback.

**Guidelines:**
- Use Markdown. Use bullet points for everything.
- Include code snippets when suggesting changes.
- Complete all steps before responding.
- Keep feedback concise, specific, and actionable.
- Use all available tools to support your analysis. Most common usage for reference:
    - `list_pull_requests` when the user does not specify a PR link.
    - `pull_request_read` when the user gives a PR URL.
    - `get_file_contents` if you need to inspect related files beyond the diff.


Your review should help authors deliver higher-quality code and foster continuous improvement.
"""

# Defining the agent
from pyagentspec.agent import Agent
agent_config = Agent(
    name="github_agent",
    llm_config=llm_config,
    system_prompt=CUSTOM_INSTRUCTIONS,
    toolboxes=[mcp_toolbox],
)

# Serialization
from pyagentspec.serialization import AgentSpecSerializer

serialized_agent = AgentSpecSerializer().to_json(agent_config)

## Running with wayflow
# from wayflowcore.agent import Agent as RuntimeAgent
# from wayflowcore.agentspec import AgentSpecLoader as WayFlowLoader
# from wayflowcore.mcp import enable_mcp_without_auth

# enable_mcp_without_auth()

# agent: RuntimeAgent = WayFlowLoader().load_json(serialized_agent)
# conversation = agent.start_conversation()
# pr_link = "<PR LINK>"
# user_query = f"Review changes of {pr_link}"

# conversation.append_user_message(user_query)
# status = conversation.execute()

# # Running with langgraph
# import asyncio
# from langgraph_agentspec_adapter import AgentSpecLoader

# langgraph_assistant = AgentSpecLoader().load_json(serialized_agent)
# config = {"configurable": {"thread_id": "1"}}

# pr_link = "<PR LINK>"
# user_query = f"Review changes of {pr_link}"

# async def main():
#     result = await langgraph_assistant.ainvoke(
#         {"messages": [{"role": "user", "content": user_query}]}, config,
#     )
#     return result

# result = asyncio.run(main())
