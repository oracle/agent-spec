# agentspec Examples

These examples demonstrate how to use the `agentspec` TypeScript SDK to define AI agents, tools, workflows, and multi-agent systems.

## Examples

| # | File | Description |
|---|------|-------------|
| 1 | [01-basic-agent.ts](./01-basic-agent.ts) | Create an agent with LLM config, system prompt, and template variables |
| 2 | [02-tools.ts](./02-tools.ts) | ServerTool, ClientTool, RemoteTool, and BuiltinTool |
| 3 | [03-multi-agent.ts](./03-multi-agent.ts) | Swarm, ManagerWorkers, and SpecializedAgent patterns |
| 4 | [04-flows.ts](./04-flows.ts) | Workflows with FlowBuilder: linear, branching, and data flow |
| 5 | [05-mcp-tools.ts](./05-mcp-tools.ts) | MCP tools with Stdio, SSE, and HTTP transports |
| 6 | [06-serialization.ts](./06-serialization.ts) | JSON/YAML serialization, camelCase, disaggregated components |
| 7 | [07-a2a-agent.ts](./07-a2a-agent.ts) | A2A (Agent-to-Agent) protocol and remote agents |
| 8 | [08-datastores.ts](./08-datastores.ts) | In-memory, Oracle DB, and PostgreSQL datastores |

## Running

Build the SDK first, then run any example with `tsx`:

```bash
# From the tsagentspec directory
npm run build
npx tsx examples/01-basic-agent.ts
```

Or use `ts-node` with ESM support:

```bash
npx ts-node --esm examples/01-basic-agent.ts
```
