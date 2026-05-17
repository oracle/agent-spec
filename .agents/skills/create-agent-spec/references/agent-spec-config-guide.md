# Agent Spec Config Guide

Use this guide to turn business intent into Open Agent Spec artifacts with the PyAgentSpec SDK. Do not hand-write serialized JSON/YAML; construct SDK objects and export them.

## Design Checklist

Ask only if the missing detail materially changes the artifact. Otherwise make a visible assumption.

- Goal: what outcome the agent or flow should produce.
- Users: employee, customer, analyst, operator, developer, etc.
- Inputs: question, account id, document, ticket id, product, region, date range.
- Outputs: answer, summary, recommendation, SQL, ticket id, JSON result, next action.
- Knowledge: RAG, database, SaaS API, internal API, web, static policy.
- Actions: create/update records, send email, open ticket, run SQL, call REST, request approval.
- Guardrails: human confirmation, read-only vs write access, safety checks, audit metadata.
- Tooling: server/orchestrator tool, MCP server/toolbox, host-provided client function, direct REST tool, or no tools.
- LLM: OCI GenAI, OpenAI, Ollama, vLLM/OpenAI-compatible, or placeholder.

## Component Choice

Use `Agent` when the requirement describes one conversational assistant with optional tools.

Use `Flow` when the requirement has explicit ordered stages, deterministic preprocessing, branching, multiple agents, or structured orchestration.

Prefer the smallest faithful artifact. A simple tool-using `Agent` is often better than a `Flow` when the workflow can be handled conversationally.

## SDK Setup

Prefer `uv` for setup and use Python 3.12. Respect the user's existing network settings, including any configured `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, package indexes, or certificate settings. Never embed organization-specific proxy hosts or credentials in a public skill.

Check for PyAgentSpec in the current environment:

```bash
uv run python -c "import pyagentspec; print('pyagentspec ok')"
```

If the workspace is not uv-managed, check with the active interpreter:

```bash
python -c "import pyagentspec; print('pyagentspec ok')"
```

If unavailable, create a dedicated Python 3.12 virtual environment with `uv`:

```bash
uv venv --python 3.12 .venv-agentspec
```

When the current workspace is an Agent Spec checkout, install from the local package so generated artifacts match the repository version:

```bash
uv pip install -p .venv-agentspec/bin/python -e ./pyagentspec
```

When another local Agent Spec checkout is explicitly provided, use that checkout:

```bash
uv pip install -p .venv-agentspec/bin/python -e /path/to/agent-spec/pyagentspec
```

Use extras only when needed by downstream work. In an Agent Spec checkout:

```bash
uv pip install -p .venv-agentspec/bin/python -e "./pyagentspec[langgraph]"
```

Outside an Agent Spec checkout, use PyPI as the default package source unless the user asks for a source checkout:

```bash
uv pip install -p .venv-agentspec/bin/python pyagentspec
```

For PyPI extras, install only the extras needed by the task:

```bash
uv pip install -p .venv-agentspec/bin/python "pyagentspec[langgraph]"
```

If source inspection is needed outside this repository, clone from the public GitHub repository and install the package editable:

```bash
git clone https://github.com/oracle/agent-spec.git .agent-spec-src
uv pip install -p .venv-agentspec/bin/python -e .agent-spec-src/pyagentspec
```

If `uv` is unavailable, use `python3.12 -m venv` and `python -m pip` as a fallback only after noting the fallback.

If SDK setup fails, stop and report the blocker. Do not create a hand-written serialized artifact as a substitute.

## Tool Selection

Use no tool when the intent only needs LLM reasoning, prompt behavior, or structured output.

When business intent implies a capability but does not specify implementation details, prefer `ServerTool` as the neutral runtime-executed contract. This avoids inventing transport, URLs, credentials, or an MCP server.

Use MCP via `MCPToolBox`, `MCPToolSpec`, and transports such as `StreamableHTTPTransport`, `SSETransport`, or `StdioTransport` when an MCP server/toolbox exists or is explicitly desired.

Use `ClientTool` when the client or host application provides the callback implementation. Use `RemoteTool` only when the requirement includes a concrete REST API contract or the user asks for direct HTTP.

## Common Imports

```python
from pathlib import Path

from pyagentspec.agent import Agent
from pyagentspec.component import Component
from pyagentspec.llms import OpenAiConfig, OciGenAiConfig, OllamaConfig
from pyagentspec.mcp import MCPToolBox, MCPToolSpec, SSETransport, StdioTransport, StreamableHTTPTransport
from pyagentspec.property import DictProperty, ListProperty, ObjectProperty, Property, StringProperty
from pyagentspec.tools import ClientTool, RemoteTool, ServerTool
```

## Minimal Agent With MCP Toolbox

Use this pattern when the requirement describes tools exposed by an MCP server.

```python
from pathlib import Path

from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiConfig
from pyagentspec.mcp import MCPToolBox, MCPToolSpec, StreamableHTTPTransport
from pyagentspec.property import StringProperty

mcp_transport = StreamableHTTPTransport(
    id="support_mcp_transport",
    name="Support MCP transport",
    url="https://TODO.example.com/mcp",
)

support_tools = MCPToolBox(
    id="support_ops_mcp_tools",
    name="Support Ops MCP Tools",
    description="Tools for customer context, issue lookup, and escalation.",
    client_transport=mcp_transport,
    tool_filter=[
        MCPToolSpec(
            id="lookup_customer_spec",
            name="lookup_customer",
            description="Fetches customer account context.",
            inputs=[StringProperty(title="account_name")],
            outputs=[StringProperty(title="customer_context")],
        ),
        MCPToolSpec(
            id="search_known_issues_spec",
            name="search_known_issues",
            description="Searches known issues by customer problem summary.",
            inputs=[StringProperty(title="issue_summary")],
            outputs=[StringProperty(title="known_issue_summary")],
        ),
        MCPToolSpec(
            id="create_support_ticket_spec",
            name="create_support_ticket",
            description="Creates a support ticket after user confirmation.",
            inputs=[
                StringProperty(title="account_name"),
                StringProperty(title="severity"),
                StringProperty(title="summary"),
                StringProperty(title="recommended_action"),
            ],
            outputs=[StringProperty(title="ticket_id")],
            requires_confirmation=True,
        ),
    ],
)

agent = Agent(
    id="support_ops_assistant",
    name="Support Ops Assistant",
    description="Helps support teams triage customer issues and prepare responses.",
    metadata={"source_intent": "Natural-language business requirement"},
    inputs=[
        StringProperty(title="user_request", description="The support representative's request."),
    ],
    outputs=[
        StringProperty(title="response_draft"),
        StringProperty(title="recommended_action"),
    ],
    llm_config=OpenAiConfig(
        id="openai_llm",
        name="OpenAI model",
        model_id="TODO_OPENAI_MODEL_ID",
    ),
    system_prompt=(
        "You are a support operations assistant. Use the available tools to understand "
        "customer context and known issues for this request: {{user_request}}. "
        "Draft concise customer-safe responses. "
        "Ask for confirmation before creating tickets or taking external actions."
    ),
    tools=[],
    toolboxes=[support_tools],
    human_in_the_loop=True,
)

Path("support_ops_assistant.agentspec.json").write_text(
    agent.to_json(indent=2),
    encoding="utf-8",
)
```

## Server Tool Pattern

Use `ServerTool` when the tool implementation is registered with and executed by the orchestrator or runtime that loads the Agent Spec. The spec declares the contract only; it does not include executable code.

```python
from pyagentspec.property import StringProperty
from pyagentspec.tools import ServerTool

search_runbook = ServerTool(
    id="search_runbook",
    name="search_runbook",
    description="Searches approved operational runbooks for a matching procedure.",
    inputs=[StringProperty(title="incident_summary")],
    outputs=[StringProperty(title="runbook_guidance")],
    requires_confirmation=False,
)
```

Use `requires_confirmation=True` on `ServerTool` when the runtime-side implementation performs writes, notifications, deletions, ticket creation, deployments, database changes, or other side effects.

## Client Tool Pattern

Use `ClientTool` when the host application provides the function implementation.

```python
from pyagentspec.property import Property, StringProperty
from pyagentspec.tools import ClientTool

lookup_customer = ClientTool(
    id="lookup_customer",
    name="lookup_customer",
    description="Fetches customer profile and recent support cases.",
    inputs=[StringProperty(title="account_name")],
    outputs=[
        Property(
            title="customer_context",
            json_schema={
                "title": "customer_context",
                "type": "object",
                "additionalProperties": True,
            },
        )
    ],
    requires_confirmation=False,
)
```

## Remote Tool Pattern

Use `RemoteTool` for a direct REST endpoint when there is no MCP server abstraction.

```python
from pyagentspec.property import StringProperty
from pyagentspec.tools import RemoteTool

create_service_ticket = RemoteTool(
    id="create_service_ticket",
    name="create_service_ticket",
    description="Creates a service ticket after user confirmation.",
    inputs=[StringProperty(title="ticket_summary")],
    outputs=[StringProperty(title="ticket_id")],
    requires_confirmation=True,
    url="https://TODO.example.com/api/tickets",
    http_method="POST",
    headers={"Content-Type": "application/json"},
    data={"summary": "{{ticket_summary}}"},
)
```

Use `requires_confirmation=True` for writes, purchases, deletions, notifications, ticket creation, database changes, or anything with external side effects.

## LLM Config Patterns

Use one unless the user specifies otherwise.

OpenAI:

```python
llm_config = OpenAiConfig(
    id="openai_llm",
    name="OpenAI model",
    model_id="TODO_OPENAI_MODEL_ID",
)
```

OCI GenAI requires an OCI client config. Use placeholders for account-specific values.

Ollama:

```python
llm_config = OllamaConfig(
    id="ollama_llm",
    name="Local Ollama model",
    url="http://localhost:11434",
    model_id="llama3.1",
)
```

## Flow Guidance

Use SDK flow classes when a `Flow` is required. Keep simple assistants as `Agent`.

Before creating a flow, inspect public PyAgentSpec examples or local installed docs for current constructor names. Do not hand-write a flow JSON structure.

At minimum, a flow should have:

- a clear `StartNode`
- one or more work nodes such as `LlmNode`, `AgentNode`, `ToolNode`, or `BranchingNode`
- an `EndNode`
- explicit control-flow edges
- data-flow edges when values need to move between nodes

## Validation

Round-trip with the SDK:

```python
from pathlib import Path
from pyagentspec.component import Component

Component.from_json(Path("artifact.agentspec.json").read_text(encoding="utf-8"))
```

Run the bundled validator:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILL_DIR="$REPO_ROOT/.agents/skills/create-agent-spec"
python "$SKILL_DIR/scripts/validate_agentspec_config.py" artifact.agentspec.json
```

The validator uses PyAgentSpec deserialization as the required validation path and fails if PyAgentSpec or its dependencies are unavailable.
Run it with the Python environment where PyAgentSpec is installed. If validation fails with `ModuleNotFoundError`, install PyAgentSpec in that environment first.

## Hygiene

- Export `component_type` and `agentspec_version` through the SDK.
- Reference declared Agent inputs in the prompt template, for example `{{user_request}}`; otherwise omit unused inputs.
- Keep `metadata` small and structured.
- Use template variables like `{{account_name}}` only for declared inputs or upstream outputs.
- Keep prompts clear: role, context, task, output expectations, constraints, and escalation rules.
- Add `human_in_the_loop=True` for general assistants unless the user explicitly wants autonomous execution.
- Never place real credentials in `api_key`, `headers`, or `sensitive_headers`.
