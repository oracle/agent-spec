---
name: create-agent-spec
description: Create Open Agent Spec / PyAgentSpec agents or flows from business requirements, natural-language product ideas, or integration intents. Use when Codex must turn plain-English intent into an Agent Spec artifact, refine an existing Agent Spec artifact, choose between Agent and Flow designs, define LLM/tool/input/output contracts, add MCP tools or toolboxes, or validate an Agent Spec artifact without relying on a local agent-spec checkout.
---

# Create Agent Spec

## Goal

Produce a portable Agent Spec artifact from business intent by constructing PyAgentSpec SDK objects and exporting JSON or YAML from those objects.

Do not hand-write serialized Agent Spec JSON/YAML. Manual JSON snippets are acceptable only for inspecting or explaining already-exported output, not for creating the artifact. If the SDK cannot be installed or imported, stop and report the blocker instead of fabricating JSON.

When the current workspace is an Agent Spec checkout, prefer its local `pyagentspec` package and docs. Outside this repository, prefer installed PyAgentSpec, public Agent Spec docs, and bundled references. Use another local checkout only when the user explicitly points to one.

## Workflow

1. Parse the request into:
   - business goal and target users
   - expected user inputs and agent outputs
   - required knowledge sources, tools, APIs, approvals, or handoffs
   - LLM/provider constraints, if any
   - runtime or serialization constraints, if any

2. Choose the component shape:
   - Use `Agent` for one conversational assistant with optional tools/toolboxes.
   - Use `Flow` when the requirement has explicit ordered stages, deterministic preprocessing, branching, multiple agents, or structured orchestration.
   - Prefer the smallest component that faithfully represents the intent.

3. Read `references/agent-spec-config-guide.md` before creating a new artifact or making non-trivial edits.

4. Ensure PyAgentSpec is available:
   - Prefer `uv` for environment creation and package installation.
   - First check whether `pyagentspec` imports in the current environment.
   - If this is an Agent Spec checkout, prefer installing from `./pyagentspec`.
   - Outside this repository, use an explicitly provided checkout, PyPI, or the public GitHub source checkout.
   - Respect the user's existing network and proxy environment. Do not embed organization-specific proxy hosts or credentials.
   - If setup fails, report the failure and do not create a hand-written Agent Spec JSON/YAML substitute.
   - Read `references/agent-spec-config-guide.md` for exact setup commands.

5. Build with SDK component classes:
   - Core: `Agent`, `Flow`, `Property` subclasses, LLM configs such as `OpenAiConfig`, `OciGenAiConfig`, `OllamaConfig`, or another SDK-supported config.
   - Tools: use no tool when the intent only needs LLM reasoning or structured output.
   - When business intent implies a capability but does not specify implementation details, prefer `ServerTool` as the neutral runtime-executed contract.
   - Use MCP via `MCPToolBox`, `MCPToolSpec`, and transports such as `StreamableHTTPTransport`, `SSETransport`, or `StdioTransport` when an MCP server/toolbox exists or is explicitly desired.
   - Use `ClientTool` for client or host-application functions and `RemoteTool` only for concrete direct REST APIs.
   - Use stable, descriptive IDs in `snake_case`.
   - Keep secrets out of artifacts. Use environment-variable placeholders such as `${SERVICE_API_TOKEN}` only in non-secret fields when appropriate; do not embed real credentials.
   - Model every input/output as an SDK `Property` with at least `title` and type.
   - Set `requires_confirmation=True` for write actions or external side effects.

6. Export only through the SDK:
   - JSON: `component.to_json(indent=2)`
   - YAML: `component.to_yaml()`
   - Preserve a small builder script if the user wants reproducibility; otherwise the exported artifact is sufficient.

7. Validate:
   - Round-trip with the SDK, for example `Component.from_json(Path(file).read_text())` or `Component.from_yaml(...)`.
   - Run the bundled validator with an absolute skill path:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILL_DIR="$REPO_ROOT/.agents/skills/create-agent-spec"
python "$SKILL_DIR/scripts/validate_agentspec_config.py" path/to/artifact.agentspec.json
```

Run the validator with the Python environment where PyAgentSpec is installed. If validation fails with `ModuleNotFoundError`, install PyAgentSpec in that environment first.

8. Report:
   - output path
   - design summary
   - SDK export and validation results
   - assumptions and placeholders
   - any unresolved runtime/tooling prerequisites

## Public Sources

Use these public sources when more detail is needed:

- Agent Spec docs: `https://oracle.github.io/agent-spec/`
- Agent Spec GitHub: `https://github.com/oracle/agent-spec`

If online access is unavailable, continue with the bundled SDK patterns and clearly say that external docs checks were not performed.
