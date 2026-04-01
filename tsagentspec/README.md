# agentspec TypeScript SDK

TypeScript SDK for the [Oracle Open Agent Specification](https://github.com/oracle/agent-spec).

## Supported component types

These types round-trip correctly between JSON/YAML and TypeScript objects:

- **Agents**: `Agent`, `Swarm`, `ManagerWorkers`, `RemoteAgent`, `SpecializedAgent`, `A2AAgent`
- **Flows**: `Flow`, `StartNode`, `EndNode`, `LlmNode`, `ToolNode`, `AgentNode`, `FlowNode`, `BranchingNode`, `MapNode`, `ParallelMapNode`, `ParallelFlowNode`, `ApiNode`, `InputMessageNode`, `OutputMessageNode`, `CatchExceptionNode`
- **Tools**: `ServerTool`, `ClientTool`, `RemoteTool`, `BuiltinTool`, `MCPTool`
- **LLM configs**: `OpenAiCompatibleConfig`, `OllamaConfig`, `VllmConfig`, `OpenAiConfig`, `OciGenAiConfig`
- **MCP**: `MCPToolBox`, `StdioTransport`, `SSETransport`, `StreamableHTTPTransport` (and mTLS variants)
- **Datastores**: `InMemoryCollectionDatastore`, `OracleDatabaseDatastore`, `PostgresDatabaseDatastore`
- **Other**: `ControlFlowEdge`, `DataFlowEdge`, `MessageSummarizationTransform`, `ConversationSummarizationTransform`

### Fixture compatibility

`tests/repo-fixtures.test.ts` is the CI contract: a curated list of 61 configs known to round-trip with the current SDK. Not every example or historical config file in the repo is covered here. Files using types outside the list above (e.g. `howto_swarm`, `howto_a2aagent`) are not yet supported.

## Installation

```bash
npm install agentspec
```

## Usage

See the [examples](./examples/README.md) directory.

## License

UPL-1.0 or Apache-2.0 — see [LICENSE-UPL.txt](../LICENSE-UPL.txt) and [LICENSE-APACHE.txt](../LICENSE-APACHE.txt).
