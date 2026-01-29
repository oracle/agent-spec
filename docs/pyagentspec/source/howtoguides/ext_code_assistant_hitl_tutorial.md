Tutorial: Building a Human-Aware Code Assistant with Agent Spec and MCP (Part 2)

In this tutorial, we extend the Code Review Assistant with human-in-the-loop capabilities, adding explicit user interaction, approval workflows, and client-side tools for sensitive or privileged data.

The first part of this tutorial can be found here: Tutorial: Building a Code Review Assistant with MCP in Agent Spec

# Recap: Where We Left Off

In Part 1, we built a fully functional GitHub Pull Request Code Review Assistant using Agent Spec and MCP. The agent was capable of:
* Connecting to GitHub via MCP tools
* Reading pull requests and file diffs
* Analyzing code changes using an LLM
* Producing structured, actionable feedback
* Running unchanged across multiple runtimes (WayFlow and LangGraph)

At the end of the previous tutorial, our agent was fully autonomous: it decided when to fetch data, how to analyze it, and what final feedback to provide, without ever consulting a human once execution started.
In this article, we will intentionally break that autonomy.
Why? Because real-world systems often require human judgment, approvals, and private knowledge that an AI agent should not (or cannot) access on its own.

# What We Are Adding in This Part

We will introduce three human-interaction mechanisms supported by Agent Spec:

1. human_in_the_loop - allow the agent to ask questions and wait for user input
2. requires_confirmation on tools - require explicit approval before executing sensitive actions
3. Client-side tools (ClientTool) - tools executed by the application (client), not the agent

Together, these features enable safe, collaborative, and enterprise-ready agent workflows.

# Why Human-in-the-Loop Matters

Fully autonomous agents are powerful-but also risky:

* They may lack context only humans possess
* They may perform irreversible actions (e.g., posting comments, merging code)
* They may require access to restricted or private data

Agent Spec is designed to explicitly model these boundaries, rather than leaving them implicit or framework-specific.

# Step 1: Human-in-the-Loop Execution Flow

With `human_in_the_loop=True`, the agent's execution model changes fundamentally. Instead of producing a single uninterrupted response, the agent can pause, ask questions, and resume once the user replies.
This behavior is preserved across all Agent Spec–compatible runtimes.
Below, we walk through the execution flow step by step, exactly as we did in Part 1.

## Agent Configuration (Recap)
We start from the same code review agent defined in Part 1. First, we define its instructions and tools:

```python
from pyagentspec.llms import OllamaConfig
from pyagentspec.mcp.clienttransport import StreamableHTTPTransport
from pyagentspec.mcp.tools import MCPToolBox

llm_config = OllamaConfig(
    name="ollama-llm",
    model_id="model-id", # e.g. gpt-oss:20b
    url="url/to/ollama_model" # e.g. localhost:11434
)

mcp_server_url = "https://api.githubcopilot.com/mcp/"
headers = {"Authorization": f"Bearer {'GITHUB_PERSONAL_ACCESS_TOKEN'}"}

mcp_client = StreamableHTTPTransport(
    name="mcp_client", url=mcp_server_url, headers=headers
)
mcp_toolbox = MCPToolBox(
    name="mcp_toolbox",
    client_transport=mcp_client,
    tool_filter=[
        "list_pull_requests", "pull_request_read", "get_file_contents"
    ]
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
""".strip()
```

Then, we define the agent, with only one change, the `human_in_the_loop flag:
```python
from pyagentspec.agent import Agent

agent_config = Agent(
    name="github_agent",
    llm_config=llm_config,
    system_prompt=CUSTOM_INSTRUCTIONS,
    toolboxes=[mcp_toolbox],
    human_in_the_loop=True
)
```
Nothing else changes. The agent logic, tools, and instructions remain identical.

## Exporting the Agent to Agent Spec
As in the previous article, we export the agent to a framework-agnostic Agent Spec definition:
```python
from pyagentspec.serialization import AgentSpecSerializer

serialized_agent = AgentSpecSerializer().to_json(agent_config)
```

This exported JSON now includes the `human_in_the_loop` capability and can be reused unchanged across runtimes.

## Running the Agent with WayFlow
We can convert the agentspec agent into the native wayflow runtime:
```python
from wayflowcore.agentspec import AgentSpecLoader as WayFlowLoader
from wayflowcore.agent import Agent as RuntimeAgent
from wayflowcore.mcp import enable_mcp_without_auth

enable_mcp_without_auth()
agent: RuntimeAgent = WayFlowLoader().load_json(serialized_agent)
```
Note: Although `enable_mcp_without_auth()` is used, authentication still occurs through the Personal Access Token (PAT) described above. Ensure your PAT is securely stored and has the appropriate read/write permissions.
Now we have instantiated the agent. We can run it as:
```python
conversation = agent.start_conversation()
pr_link = "<LINK TO THE PR>"
user_query = f"Review changes of {pr_link}"

conversation.append_user_message(user_query)
status = conversation.execute()
```

## Running the Same Agent with LangGraph
Similarly, we can convert the agentspec agent into a langgraph agent:
```python
from langgraph_agentspec_adapter import AgentSpecLoader

langgraph_assistant = AgentSpecLoader().load_json(serialized_agent)
Now we have instantiated the agent. We can run it as:
import asyncio
config = {"configurable": {"thread_id": "1"}}

pr_link = "<PR LINK>"
user_query = f"Review changes of {pr_link}"

async def main():
    result = await langgraph_assistant.ainvoke(
        {"messages": [{"role": "user", "content": user_query}]}, config,
    )
    return result

result = asyncio.run(main())
```
## Execution Flow
The execution may look like:
```
User:
Review the latest pull request in this repository.

Agent:
I found multiple open pull requests.
Which one would you like me to review?

(User input required - execution pauses)

User:
Please review PR #42.

Agent:
Fetching pull request details...

Agent:
Analyzing code changes...

Agent:
Here is my structured review:
- Description: ...
- Strengths: ...
- Opportunities for Improvement: ...

User:
Can you focus your review on the asynchronous part and make sure no race conditions is possible?

Agent:
Sure! ...
```

In this example, the agent stops execution, waits for user clarification and continues seamlessly after receiving input
No custom logic was needed in the runtime, this behavior is driven entirely by the Agent Spec configuration.

## Why This Matters
With `human_in_the_loop=True`, your agent:
* Does not guess when information is missing
* Explicitly involves humans in decision points
* Remains fully declarative and portable

Most importantly, the interaction contract is encoded in Agent Spec, not hidden in runtime glue code.

# Step 2. Requiring Confirmation for Sensitive Tools
Reading data is usually safe. Writing data is not.
Posting comments on a pull request is a side-effecting operation that should often require explicit approval.
Agent Spec supports this via the `requires_confirmation` flag on tools.

## Example: Adding a Confirmation-Required MCP Tool
We will add a MCP GitHub tool that posts review comments, but require user approval before execution.
```python
from pyagentspec.mcp.tools import MCPTool

add_comment_tool = MCPTool(
    name="pull_request_review_write",
    client_transport=mcp_client,
    requires_confirmation=True,
    description="""Create and/or submit, delete review of a pull request.
Available methods
- create: Create a new review of a pull request. If "event" parameter is provided, the review is submitted. If "event" is omitted, a pending review is created.
- submit_pending: Submit an existing pending review of a pull request. This requires that a pending review exists for the current user on the specified pull request. The "body" and "event" parameters are used when submitting the review.
- delete_pending: Delete an existing pending review of a pull request. This requires that a pending review exists for the current user on the specified pull request.
"""
)
```
Now we attach this tool to the agent.
```python
agent_config = Agent(
    name="github_agent",
    llm_config=llm_config,
    system_prompt=CUSTOM_INSTRUCTIONS,
    toolboxes=[mcp_toolbox],
    tools=[add_comment_tool],
    human_in_the_loop=True
)
```
## What Happens at Runtime
The agent can pause execution, display tool parameters, allow edits or rejection and resume only after approval.
```
Agent:
I would like to post the following review comment to PR #42:

- Suggest adding unit tests for the new configuration parser.

Do you approve this action? (Y/N)

User:
Y

Agent: executes the tool and continues...
```
This pattern is critical for CI/CD pipelines, Enterprise governance and Production-grade agent deployments

# Step 3. Introducing Client-Side Tools (ClientTool)

Some information should never/can not be fetched by the agent directly.
Examples: Internal sensitive design documents, external secured platforms, private dashboards.
For this, Agent Spec provides ClientTools.

## What Is a ClientTool?
ClientTools are not executed by the agent runtime. The client application executes them and returns the result to the agent.
This mirrors OpenAI's function-calling model, but is explicitly modeled in Agent Spec.

## Example: Fetching a specific information on a protected space
Assume every feature must have an associated design document, but the design documents are secured on an environment that only users through their browser have access.
We can define the client tool, and execution will be a responsibility of the user's code:
```python
from pyagentspec.tools import ClientTool
from pyagentspec.property import Property

get_design_page = ClientTool(
    name="get_feature_design_page",
    description=(
        "Gets the design page of a feature. Each feature, before being "
        "able to merge it, needs to have an associated design page. "
        "Use this function to get the content of the design page to ensure "
        "the feature is implemented according to the design page."
    ),
    inputs=[
        Property(json_schema={
            "title": "feature_name",
            "type": "string"
        })
    ]
)

agent_config = Agent(
    name="github_agent",
    llm_config=llm_config,
    system_prompt=CUSTOM_INSTRUCTIONS,
    toolboxes=[mcp_toolbox],
    tools=[add_comment_tool, get_design_page],
    human_in_the_loop=True
)
```
During execution, the agent stops to ask for the client to execute a particular action (here, get the design page content about a specific content) and wait for the user to post the response:
```
Agent: I need to execute get_feature_design_page(feature_name=mcp)

(Client executes get_feature_design_page)

User passes the answer back:
Design page content:
- The parser must support nested configs
- Default behavior must remain unchanged
```
The client sends the result back to the agent, which can now validate implementation against design and reference design constraints in its review

# How These Features Work Together

1. human_in_the_loop enables questions, pauses, and clarification
2. requires_confirmation protects sensitive or side-effecting actions
3. ClientTool keeps private or privileged data out of the agent

Together, they enable Safer agents, Human-AI collaboration and Enterprise-grade control.

# When to Use Each Pattern

Use human_in_the_loop when:
* Input may be ambiguous
* Context may be missing
* Decisions require judgment

Use requires_confirmation when:
* Tools modify external state
* Actions are irreversible
* Compliance is required

Use ClientTool when:
* Data location is private or restricted
* Execution must happen outside the agent runtime

# Conclusion
In this second part of the tutorial, you transformed your Code Review Assistant from a fully autonomous agent into a collaborative, human-aware system.

You learned how to:
1. Enable interactive agent workflows
2. Require explicit approval for sensitive actions
3. Delegate privileged operations to the client
4. Maintain portability across runtimes using Agent Spec

These patterns are essential for moving from demos to real production systems. To learn more, you can
