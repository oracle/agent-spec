# Mastra Adapter

The Mastra adapter connects Agent Spec's portable agent definitions with Mastra
agent, tool, storage, and workflow runtime objects. It supports both directions:

- load Agent Spec components into a Mastra runtime
- export serializable Mastra-style agent configs back into Agent Spec YAML or JSON

The adapter keeps Mastra optional at package install time. `agentspec` does not
make `@mastra/core`, `@mastra/pg`, or other Mastra packages hard dependencies.
When the adapter is used, the default runtime binder resolves Mastra packages
from the consuming application.

## Design

Agent Spec is the portable contract. Mastra is the runtime that executes it.
The adapter keeps those responsibilities separate:

- Agent Spec defines the agent, model config, prompt, tools, schemas, flows, and
  datastore configuration.
- The adapter supplies default Mastra `Agent`, `createTool`, `createWorkflow`,
  and `createStep` bindings for normal loading.
- The application supplies executable behavior such as tool functions, workflow
  node executors, storage provider packages, or custom runtime overrides.
- Resolver hooks translate framework-specific model and tool details without
  forcing those choices into the Agent Spec core model.

This follows the same adapter shape as the Python integrations: a loader
converts Agent Spec into a framework runtime, while an exporter converts
framework-side configuration back into Agent Spec when the data is serializable.

## Agent Spec To Mastra

Use `AgentSpecLoader` when the source of truth is Agent Spec YAML, JSON, a plain
serialized dictionary, or an already-created Agent Spec component.

```ts
import { AgentSpecLoader } from "agentspec/adapters/mastra";

const mastraAgent = new AgentSpecLoader({
  toolRegistry,
}).loadYaml(agentSpecYaml);
```

The loader supports Agent Spec `Agent` components with:

- `id`, `name`, `description`, and `metadata`
- `systemPrompt` as Mastra instructions
- `OpenAiConfig`, `OpenAiCompatibleConfig`, `OllamaConfig`, and `VllmConfig`
- `ServerTool` through a user-supplied `toolRegistry`
- tool input and output schemas as JSON Schema object descriptors

For disaggregated Agent Spec configs, load referenced components first and pass
the returned registry into the main load:

```ts
const registry = loader.loadYaml(referencedYaml, {
  importOnlyReferencedComponents: true,
});

const mastraAgent = loader.loadYaml(mainYaml, {
  componentsRegistry: registry,
});
```

The loader rejects unsupported Agent features explicitly instead of silently
dropping them.

## Runtime Binding

For normal use, the loader creates real Mastra agent and tool objects through
`@mastra/core/agent` and `@mastra/core/tools`. The consuming application must
have `@mastra/core` installed, but it does not need to pass `Agent` or
`createTool` manually.

```ts
const loader = new AgentSpecLoader({
  toolRegistry: {
    lookup_account: async (input) => lookupAccount(input.accountId),
  },
});

const mastraAgent = loader.loadYaml(agentSpecYaml);
```

Agent Spec stores the tool contract: name, description, input schema, and output
schema. The runtime registry supplies the actual JavaScript function.

Applications with custom Mastra setup can override runtime construction:

```ts
const loader = new AgentSpecLoader({
  runtime: {
    createAgent: (config) => new Agent({ ...config, memory }),
    createTool: (config) => createTool(config),
  },
  toolRegistry,
});
```

## Model Resolution

The default model resolver maps common Agent Spec LLM configs into Mastra-style
model targets:

- `OpenAiConfig` -> `openai/<model>`
- `OpenAiCompatibleConfig` -> `{ id, url, apiKey? }`
- `OllamaConfig` -> `{ id: "ollama/<model>", url, apiKey? }`
- `VllmConfig` -> `{ id: "vllm/<model>", url, apiKey? }`

Applications can provide `modelResolver` when they need a different Mastra model
binding, provider-specific object, headers, custom endpoint handling, fallback
models, or organization-specific model naming.

## Tools

The default tool resolver supports Agent Spec `ServerTool`.

```ts
const loader = new AgentSpecLoader({
  toolRegistry: {
    get_current_weather: async ({ city }) => getWeather(city),
  },
});
```

The resolver looks up tools by name first, because that is the identifier the
LLM sees. It also accepts the Agent Spec tool id as a fallback for applications
that use stable internal identifiers.

Runtime-specific retrieval, vector stores, and embedding pipelines are not
modeled as first-class Mastra adapter concepts. They can still be exposed
portably as ordinary tools, with the actual retrieval implementation provided by
the target runtime.

## Mastra To Agent Spec

Use `AgentSpecExporter` when the source is a Mastra-style config or an object
previously created by the adapter.

```ts
import { AgentSpecExporter } from "agentspec/adapters/mastra";

const yaml = new AgentSpecExporter(exportOptions).toYaml(weatherAgent);
```

The exporter has five entry points:

- `toAgent`
- `toFlow`
- `toComponent`
- `toJson`
- `toYaml`

The lossless path is provenance-based: objects created by the adapter keep the
original Agent Spec component under `sourceAgentSpecAgent`,
`sourceAgentSpecFlow`, or `sourceAgentSpecTool`.

For native Mastra-like objects, export is intentionally conservative. The object
must expose serializable fields such as:

- `name`
- `description`
- `metadata`
- string `instructions` or `systemPrompt`
- a simple model id or model config object
- plain tool maps with JSON Schema input and output descriptors

Dynamic runtime functions, Zod-only schemas, model fallback arrays, and opaque
native workflow objects are rejected unless the caller provides an explicit
export hook.

## Export Hooks

Use hooks for framework-specific values that cannot be inferred safely:

```ts
const exporter = new AgentSpecExporter({
  nativeModelExporter(model) {
    return createOpenAiCompatibleConfig({
      name: "runtime-model",
      modelId: model.modelId,
      url: "runtime://langgraph/default-llm",
    });
  },

  nativeToolExporter(tool, context) {
    if (tool.kind !== "mcp") {
      return undefined;
    }

    return createMCPTool({
      name: tool.name ?? context.toolName,
      clientTransport: createStdioTransport({
        command: "python",
        args: ["weather_mcp_server.py"],
      }),
    });
  },
});
```

## Datastores And Storage

The adapter maps Agent Spec datastores into Mastra storage targets. Store
construction loads the resolved Mastra package/export by default:

- `InMemoryCollectionDatastore` -> `@mastra/core/storage` `InMemoryStore`
- `PostgresDatabaseDatastore` -> `@mastra/pg` `PostgresStore`

```ts
import { createMastraStorageBundle } from "agentspec/adapters/mastra";

const storageBundle = createMastraStorageBundle(datastore, {
  schemaName: "AGENTSPEC",
});
```

The bundle includes:

- `target`: the resolved datastore target
- `storage`: the constructed storage instance
- `mastraConfig`: `{ storage }` for a Mastra app
- `memoryConfig`: `{ storage }` for Mastra memory

`OracleDatabaseDatastore` remains an Agent Spec core datastore type, but this
adapter does not map it to a Mastra storage package until Mastra publishes an
official OracleDB storage provider.

## Flow Conversion

`convertAgentSpecFlowToMastraWorkflow` converts simple linear Agent Spec flows
into Mastra workflow runtime configs.

Supported linear shape:

```text
StartNode -> LlmNode/ToolNode/AgentNode... -> EndNode
```

The converter rejects branching, cycles, disconnected nodes, unsupported node
types, and ambiguous execution paths. This keeps workflow conversion exact
rather than turning a complex Agent Spec graph into an approximate Mastra
workflow.

LLM and Agent nodes require caller-supplied executor registries because prompt
execution and agent handoff are runtime behavior:

```ts
const workflow = convertAgentSpecFlowToMastraWorkflow(flow, {
  llmNodeRegistry,
  agentNodeRegistry,
  toolRegistry,
});
```

Applications with custom workflow construction can provide `runtime`.

## Unsupported Cases

The adapter intentionally fails fast for unsupported cases instead of silently
dropping fields or producing partial runtime behavior.

Current limitations include:

- non-server local tool execution modes that do not map cleanly to Mastra tools
- MCP toolbox runtime loading into Mastra MCP clients
- Agent Spec swarm, manager-worker, specialized-agent, remote-agent, and A2A
  roots
- advanced non-linear flow graphs
- framework-specific vector and semantic-memory semantics

## Examples

Small examples are available under:

```text
examples/adapters/mastra
```

They cover:

- Agent Spec agent -> Mastra-shaped runtime
- Mastra-style agent config -> Agent Spec YAML

## Test Coverage

The adapter tests cover:

- Agent Spec agent loading into Mastra
- default Mastra runtime binding
- tool registry binding
- tool schema conversion
- unsupported tool and agent feature failures
- model resolution
- Mastra-style config export
- provenance-based round trips
- datastore target resolution
- in-memory and Postgres storage bundle construction
- explicit unsupported handling for Oracle datastores
- linear flow planning
- Agent Spec flow to Mastra workflow conversion

## Next Steps

- Add Agent Spec-level vector and semantic-memory configuration.
- Map Agent Spec vector and memory concepts into Mastra vector stores and memory providers.
- Add MCP toolbox loading into Mastra MCP client/runtime setup.
- Add richer local, remote, and MCP tool support.
- Add multi-agent mapping for swarms, manager-worker patterns, specialized agents, remote agents, and A2A agents.
- Expand workflow conversion beyond linear flows.
- Support branching, conditional routing, parallel execution, map nodes, nested flows, and error handling nodes.
- Add validation helpers for the Mastra-supported Agent Spec subset.
- Add clearer diagnostics and conversion reports for unsupported fields.
