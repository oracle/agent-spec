# Mastra Adapter Examples

These examples show the two conversion directions supported by the TypeScript
Mastra adapter:

- `agentspec2mastra_tools.ts`: create an Agent Spec agent and load it into a
  Mastra-shaped runtime with `AgentSpecLoader`
- `mastra2agentspec_agent_with_tool.ts`: export a Mastra-style agent config to
  Agent Spec YAML with `AgentSpecExporter`

Run from the repository root after installing the TypeScript SDK dependencies:

```bash
npm --prefix tsagentspec install
npm --prefix tsagentspec run build
tsagentspec/node_modules/.bin/tsx examples/adapters/mastra/agentspec2mastra_tools.ts
tsagentspec/node_modules/.bin/tsx examples/adapters/mastra/mastra2agentspec_agent_with_tool.ts
```

