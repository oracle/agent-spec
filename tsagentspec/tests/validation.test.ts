/**
 * Validation tests — test that the SDK correctly validates inputs and rejects
 * invalid configurations via Zod schema validation.
 */
import { describe, it, expect } from "vitest";
import {
  createAgent,
  createOpenAiCompatibleConfig,
  createVllmConfig,
  createOpenAiConfig,
  createServerTool,
  createClientTool,
  createRemoteTool,
  createBuiltinTool,
  createStartNode,
  createEndNode,
  createLlmNode,
  createBranchingNode,
  createToolNode,
  createAgentNode,
  createFlowNode,
  createMapNode,
  createFlow,
  createControlFlowEdge,
  createSwarm,
  createManagerWorkers,
  stringProperty,
  integerProperty,
  booleanProperty,
  FlowBuilder,
  HandoffMode,
  AgentSpecSerializer,
  AgentSpecDeserializer,
} from "../src/index.js";

/* ---------- helpers ---------- */

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeSimpleFlow() {
  const start = createStartNode({
    name: "start",
    inputs: [stringProperty({ title: "q" })],
  });
  const end = createEndNode({
    name: "end",
    outputs: [stringProperty({ title: "r" })],
  });
  return createFlow({
    name: "flow",
    startNode: start,
    nodes: [start, end],
    controlFlowConnections: [
      createControlFlowEdge({ name: "e", fromNode: start, toNode: end }),
    ],
  });
}

/* ================================================================
   VALID CONFIGURATIONS
   ================================================================ */

describe("Valid configurations", () => {
  it("should create a minimal agent", () => {
    const agent = createAgent({
      name: "minimal",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    expect(agent.componentType).toBe("Agent");
  });

  it("should create an agent with all optional fields", () => {
    const agent = createAgent({
      id: "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      name: "full",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are a {{role}} helper.",
      description: "A full agent",
      metadata: { version: "1.0", tags: ["test"] },
      humanInTheLoop: false,
      tools: [
        createServerTool({ name: "tool1" }),
        createClientTool({ name: "tool2" }),
      ],
      outputs: [stringProperty({ title: "answer" })],
    });
    expect(agent.id).toBe("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11");
    expect(agent.description).toBe("A full agent");
    expect(agent.humanInTheLoop).toBe(false);
    expect(agent.tools).toHaveLength(2);
  });

  it("should create all LLM config types", () => {
    const oai = createOpenAiCompatibleConfig({
      name: "oai",
      url: "http://example.com",
      modelId: "gpt-4",
    });
    expect(oai.componentType).toBe("OpenAiCompatibleConfig");

    const vllm = createVllmConfig({
      name: "vllm",
      url: "http://example.com",
      modelId: "mistral",
    });
    expect(vllm.componentType).toBe("VllmConfig");

    const openai = createOpenAiConfig({
      name: "openai",
      modelId: "gpt-4o",
    });
    expect(openai.componentType).toBe("OpenAiConfig");
  });

  it("should create all tool types", () => {
    const server = createServerTool({
      name: "server",
      inputs: [stringProperty({ title: "x" })],
    });
    expect(server.componentType).toBe("ServerTool");

    const client = createClientTool({ name: "client" });
    expect(client.componentType).toBe("ClientTool");

    const remote = createRemoteTool({
      name: "remote",
      url: "http://example.com",
      httpMethod: "GET",
    });
    expect(remote.componentType).toBe("RemoteTool");

    const builtin = createBuiltinTool({
      name: "builtin",
      toolType: "code_exec",
    });
    expect(builtin.componentType).toBe("BuiltinTool");
  });

  it("should create properties with valid titles", () => {
    expect(stringProperty({ title: "valid_title" }).title).toBe("valid_title");
    expect(integerProperty({ title: "x" }).title).toBe("x");
    expect(booleanProperty({ title: "flag123" }).title).toBe("flag123");
  });

  it("should create a complete flow", () => {
    const flow = makeSimpleFlow();
    expect(flow.componentType).toBe("Flow");
  });

  it("should create a swarm with valid configuration", () => {
    const a = createAgent({
      name: "a",
      llmConfig: makeLlmConfig(),
      systemPrompt: "A",
    });
    const b = createAgent({
      name: "b",
      llmConfig: makeLlmConfig(),
      systemPrompt: "B",
    });
    const swarm = createSwarm({
      name: "swarm",
      firstAgent: a,
      relationships: [[a, b]],
      handoff: HandoffMode.ALWAYS,
    });
    expect(swarm.componentType).toBe("Swarm");
  });

  it("should create a manager-workers with valid configuration", () => {
    const manager = createAgent({
      name: "manager",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Manage",
    });
    const worker = createAgent({
      name: "worker",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Work",
    });
    const mw = createManagerWorkers({
      name: "team",
      groupManager: manager,
      workers: [worker],
    });
    expect(mw.componentType).toBe("ManagerWorkers");
  });
});

/* ================================================================
   INVALID CONFIGURATIONS - Zod validation errors
   ================================================================ */

describe("Invalid configurations", () => {
  describe("Agent validation", () => {
    it("should throw when name is missing", () => {
      expect(() =>
        createAgent({
          name: undefined as unknown as string,
          llmConfig: makeLlmConfig(),
          systemPrompt: "Hello",
        }),
      ).toThrow();
    });

    it("should throw when llmConfig is missing", () => {
      expect(() =>
        createAgent({
          name: "agent",
          llmConfig: undefined as any,
          systemPrompt: "Hello",
        }),
      ).toThrow();
    });

    it("should throw when systemPrompt is missing", () => {
      expect(() =>
        createAgent({
          name: "agent",
          llmConfig: makeLlmConfig(),
          systemPrompt: undefined as unknown as string,
        }),
      ).toThrow();
    });
  });

  describe("LLM config validation", () => {
    it("should throw when OpenAiCompatibleConfig is missing url", () => {
      expect(() =>
        createOpenAiCompatibleConfig({
          name: "llm",
          url: undefined as unknown as string,
          modelId: "gpt-4",
        }),
      ).toThrow();
    });

    it("should throw when OpenAiCompatibleConfig is missing modelId", () => {
      expect(() =>
        createOpenAiCompatibleConfig({
          name: "llm",
          url: "http://example.com",
          modelId: undefined as unknown as string,
        }),
      ).toThrow();
    });

    it("should throw when VllmConfig is missing url", () => {
      expect(() =>
        createVllmConfig({
          name: "vllm",
          url: undefined as unknown as string,
          modelId: "mistral",
        }),
      ).toThrow();
    });

    it("should throw when OpenAiConfig is missing modelId", () => {
      expect(() =>
        createOpenAiConfig({
          name: "openai",
          modelId: undefined as unknown as string,
        }),
      ).toThrow();
    });
  });

  describe("Property validation", () => {
    it("should throw for property title with period", () => {
      expect(() => stringProperty({ title: "invalid.title" })).toThrow();
    });

    it("should throw for property title with comma", () => {
      expect(() => stringProperty({ title: "invalid,title" })).toThrow();
    });

    it("should throw for property title with curly braces", () => {
      expect(() => stringProperty({ title: "invalid{title}" })).toThrow();
    });

    it("should throw for property title with space", () => {
      expect(() => stringProperty({ title: "invalid title" })).toThrow();
    });

    it("should throw for property title with newline", () => {
      expect(() => stringProperty({ title: "invalid\ntitle" })).toThrow();
    });

    it("should throw for property title with quotes", () => {
      expect(() => stringProperty({ title: "invalid'title" })).toThrow();
      expect(() => stringProperty({ title: 'invalid"title' })).toThrow();
    });

    it("should throw for empty property title", () => {
      expect(() => stringProperty({ title: "" })).toThrow();
    });
  });

  describe("Node validation", () => {
    it("should throw when LlmNode is missing promptTemplate", () => {
      expect(() =>
        createLlmNode({
          name: "llm",
          llmConfig: makeLlmConfig(),
          promptTemplate: undefined as unknown as string,
        }),
      ).toThrow();
    });

    it("should throw when LlmNode is missing llmConfig", () => {
      expect(() =>
        createLlmNode({
          name: "llm",
          llmConfig: undefined as any,
          promptTemplate: "Hello",
        }),
      ).toThrow();
    });

    it("should throw when BranchingNode is missing mapping", () => {
      expect(() =>
        createBranchingNode({
          name: "branch",
          mapping: undefined as unknown as Record<string, string>,
        }),
      ).toThrow();
    });

    it("should throw when ToolNode is missing tool", () => {
      expect(() =>
        createToolNode({
          name: "tool-node",
          tool: undefined as any,
        }),
      ).toThrow();
    });

    it("should throw when AgentNode is missing agent", () => {
      expect(() =>
        createAgentNode({
          name: "agent-node",
          agent: undefined as any,
        }),
      ).toThrow();
    });
  });

  describe("Flow validation", () => {
    it("should throw when flow is missing startNode", () => {
      const end = createEndNode({ name: "end" });
      expect(() =>
        createFlow({
          name: "flow",
          startNode: undefined as any,
          nodes: [end],
          controlFlowConnections: [],
        }),
      ).toThrow();
    });

    it("should throw when flow is missing nodes", () => {
      const start = createStartNode({ name: "start" });
      expect(() =>
        createFlow({
          name: "flow",
          startNode: start,
          nodes: undefined as any,
          controlFlowConnections: [],
        }),
      ).toThrow();
    });
  });

  describe("FlowBuilder validation", () => {
    it("should throw on duplicate node names", () => {
      const llm1 = createLlmNode({
        name: "same",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const llm2 = createLlmNode({
        name: "same",
        llmConfig: makeLlmConfig(),
        promptTemplate: "B",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm1);
      expect(() => builder.addNode(llm2)).toThrow("already exists");
    });

    it("should throw on missing entry point", () => {
      const builder = new FlowBuilder();
      expect(() => builder.build()).toThrow();
    });

    it("should throw on missing finish node", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm");
      expect(() => builder.build()).toThrow("Missing finish node");
    });

    it("should throw on double setEntryPoint", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm");
      expect(() => builder.setEntryPoint("llm")).toThrow("Entry point already set");
    });

    it("should throw buildLinearFlow with empty nodes", () => {
      expect(() => FlowBuilder.buildLinearFlow({ nodes: [] })).toThrow(
        "nodes list must not be empty",
      );
    });

    it("should throw buildLinearFlow with StartNode in nodes", () => {
      const start = createStartNode({ name: "start" });
      expect(() =>
        FlowBuilder.buildLinearFlow({ nodes: [start] }),
      ).toThrow("not necessary to add a StartNode");
    });

    it("should throw buildLinearFlow with EndNode in nodes", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const end = createEndNode({ name: "end" });
      expect(() =>
        FlowBuilder.buildLinearFlow({ nodes: [llm, end] }),
      ).toThrow("not necessary to add an EndNode");
    });

    it("should throw when referencing non-existent node", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      expect(() => builder.addEdge("llm", "nonexistent")).toThrow(
        "not found",
      );
    });
  });

  describe("Swarm validation", () => {
    it("should throw when firstAgent is missing", () => {
      expect(() =>
        createSwarm({
          name: "swarm",
          firstAgent: undefined as any,
          relationships: [],
        }),
      ).toThrow();
    });
  });

  describe("ManagerWorkers validation", () => {
    it("should throw when groupManager is missing", () => {
      expect(() =>
        createManagerWorkers({
          name: "mw",
          groupManager: undefined as any,
          workers: [],
        }),
      ).toThrow();
    });

    it("should throw when workers is missing", () => {
      const agent = createAgent({
        name: "mgr",
        llmConfig: makeLlmConfig(),
        systemPrompt: "M",
      });
      expect(() =>
        createManagerWorkers({
          name: "mw",
          groupManager: agent,
          workers: undefined as any,
        }),
      ).toThrow();
    });
  });
});

/* ================================================================
   SERIALIZATION VALIDATION
   ================================================================ */

describe("Serialization validation", () => {
  it("should produce valid YAML from complex agent", () => {
    const agent = createAgent({
      name: "complex-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are a {{role}} for {{company}}.",
      tools: [
        createServerTool({
          name: "search",
          inputs: [stringProperty({ title: "query" })],
          outputs: [stringProperty({ title: "result" })],
        }),
        createRemoteTool({
          name: "api-call",
          url: "https://example.com/{{endpoint}}",
          httpMethod: "POST",
          data: { payload: "{{content}}" },
        }),
      ],
    });

    const serializer = new AgentSpecSerializer();
    const yaml = serializer.toYaml(agent);

    // YAML should contain the component type
    expect(yaml).toContain("Agent");
    // Should contain snake_case keys
    expect(yaml).toContain("component_type");
    expect(yaml).toContain("system_prompt");
  });

  it("should produce valid JSON from complex agent", () => {
    const agent = createAgent({
      name: "json-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello {{name}}.",
    });

    const serializer = new AgentSpecSerializer();
    const json = serializer.toJson(agent);
    const parsed = JSON.parse(json);

    expect(parsed.component_type).toBe("Agent");
    expect(parsed.system_prompt).toBe("Hello {{name}}.");
    expect(parsed.name).toBe("json-agent");
  });

  it("should handle round trip for agent with metadata", () => {
    const agent = createAgent({
      name: "meta-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      metadata: { version: "2.0", nested: { key: "value" } },
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const json = serializer.toJson(agent);
    const restored = deserializer.fromJson(json) as Record<string, unknown>;

    expect(restored["name"]).toBe("meta-agent");
    const meta = restored["metadata"] as Record<string, unknown>;
    expect(meta["version"]).toBe("2.0");
    expect((meta["nested"] as Record<string, unknown>)["key"]).toBe("value");
  });

  it("should handle empty tools list in round trip", () => {
    const agent = createAgent({
      name: "no-tools",
      llmConfig: makeLlmConfig(),
      systemPrompt: "No tools here.",
      tools: [],
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const json = serializer.toJson(agent);
    const restored = deserializer.fromJson(json) as Record<string, unknown>;

    expect(restored["tools"]).toEqual([]);
  });

  it("should produce sorted keys with component_type first", () => {
    const agent = createAgent({
      name: "sorted-keys",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Test",
    });

    const serializer = new AgentSpecSerializer();
    const json = serializer.toJson(agent);
    const parsed = JSON.parse(json);
    const keys = Object.keys(parsed);

    // component_type should be first
    expect(keys[0]).toBe("component_type");
    // agentspec_version should be second (on root components)
    expect(keys[1]).toBe("agentspec_version");
    // id should be third
    expect(keys[2]).toBe("id");
    // name should be fourth
    expect(keys[3]).toBe("name");
  });
});
