import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecDeserializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createOllamaConfig,
  createVllmConfig,
  createOpenAiConfig,
  createServerTool,
  createClientTool,
  createRemoteTool,
  createBuiltinTool,
  createStartNode,
  createEndNode,
  createLlmNode,
  createControlFlowEdge,
  createFlow,
  FlowBuilder,
  stringProperty,
  integerProperty,
} from "../../src/index.js";

const serializer = new AgentSpecSerializer();
const deserializer = new AgentSpecDeserializer();

function roundTrip(component: Record<string, unknown>): Record<string, unknown> {
  const json = serializer.toJson(component as any) as string;
  return deserializer.fromJson(json) as Record<string, unknown>;
}

describe("Round-trip serialization", () => {
  describe("Agent", () => {
    it("should round-trip an Agent with OpenAiCompatibleConfig", () => {
      const agent = createAgent({
        name: "test-agent",
        llmConfig: createOpenAiCompatibleConfig({
          name: "llm",
          url: "http://localhost:8000",
          modelId: "gpt-4",
        }),
        systemPrompt: "You are a {{role}} assistant.",
      });
      const result = roundTrip(agent);
      expect(result["componentType"]).toBe("Agent");
      expect(result["name"]).toBe("test-agent");
      expect(result["systemPrompt"]).toBe("You are a {{role}} assistant.");
      expect(result["humanInTheLoop"]).toBe(true);
    });

    it("should round-trip an Agent with tools", () => {
      const tool = createServerTool({
        name: "search",
        inputs: [stringProperty({ title: "query" })],
        outputs: [stringProperty({ title: "result" })],
      });
      const agent = createAgent({
        name: "agent-with-tools",
        llmConfig: createOpenAiCompatibleConfig({
          name: "llm",
          url: "http://localhost",
          modelId: "gpt-4",
        }),
        systemPrompt: "You are helpful.",
        tools: [tool],
      });
      const result = roundTrip(agent);
      const tools = result["tools"] as Record<string, unknown>[];
      expect(tools).toHaveLength(1);
      expect(tools[0]!["componentType"]).toBe("ServerTool");
      expect(tools[0]!["name"]).toBe("search");
    });

    it("should preserve inferred inputs through round trip", () => {
      const agent = createAgent({
        name: "agent",
        llmConfig: createOpenAiCompatibleConfig({
          name: "llm",
          url: "http://localhost",
          modelId: "gpt-4",
        }),
        systemPrompt: "Help with {{topic}} for {{user}}.",
      });
      const result = roundTrip(agent);
      const inputs = result["inputs"] as { title: string }[];
      expect(inputs).toBeDefined();
      const titles = inputs.map((i) => i.title);
      expect(titles).toContain("topic");
      expect(titles).toContain("user");
    });
  });

  describe("LLM Configs", () => {
    it("should round-trip OpenAiCompatibleConfig", () => {
      const config = createOpenAiCompatibleConfig({
        name: "llm",
        url: "http://localhost:8000",
        modelId: "gpt-4",
        defaultGenerationParameters: { maxTokens: 1024, temperature: 0.7 },
      });
      const result = roundTrip(config);
      expect(result["componentType"]).toBe("OpenAiCompatibleConfig");
      expect(result["modelId"]).toBe("gpt-4");
      expect(result["url"]).toBe("http://localhost:8000");
    });

    it("should round-trip OllamaConfig", () => {
      const config = createOllamaConfig({
        name: "ollama",
        url: "http://localhost:11434",
        modelId: "llama2",
      });
      const result = roundTrip(config);
      expect(result["componentType"]).toBe("OllamaConfig");
      expect(result["modelId"]).toBe("llama2");
    });

    it("should round-trip VllmConfig", () => {
      const config = createVllmConfig({
        name: "vllm",
        url: "http://localhost:8000",
        modelId: "mistral",
      });
      const result = roundTrip(config);
      expect(result["componentType"]).toBe("VllmConfig");
      expect(result["modelId"]).toBe("mistral");
    });

    it("should round-trip OpenAiConfig", () => {
      const config = createOpenAiConfig({
        name: "openai",
        modelId: "gpt-4o",
      });
      const result = roundTrip(config);
      expect(result["componentType"]).toBe("OpenAiConfig");
      expect(result["modelId"]).toBe("gpt-4o");
      expect("url" in result).toBe(false);
    });
  });

  describe("Tools", () => {
    it("should round-trip ServerTool", () => {
      const tool = createServerTool({
        name: "server-tool",
        inputs: [stringProperty({ title: "input" })],
        outputs: [integerProperty({ title: "output" })],
      });
      const result = roundTrip(tool);
      expect(result["componentType"]).toBe("ServerTool");
      expect(result["name"]).toBe("server-tool");
    });

    it("should round-trip ClientTool", () => {
      const tool = createClientTool({
        name: "client-tool",
      });
      const result = roundTrip(tool);
      expect(result["componentType"]).toBe("ClientTool");
    });

    it("should round-trip RemoteTool", () => {
      const tool = createRemoteTool({
        name: "remote-tool",
        url: "https://api.example.com/{{resource}}",
        httpMethod: "GET",
      });
      const result = roundTrip(tool);
      expect(result["componentType"]).toBe("RemoteTool");
      expect(result["url"]).toBe("https://api.example.com/{{resource}}");
      expect(result["httpMethod"]).toBe("GET");
    });

    it("should round-trip BuiltinTool", () => {
      const tool = createBuiltinTool({
        name: "builtin-tool",
        toolType: "code_execution",
        configuration: { language: "python" },
      });
      const result = roundTrip(tool);
      expect(result["componentType"]).toBe("BuiltinTool");
      expect(result["toolType"]).toBe("code_execution");
    });
  });

  describe("Flow", () => {
    it("should round-trip a simple flow", () => {
      const start = createStartNode({
        name: "start",
        inputs: [stringProperty({ title: "query" })],
      });
      const end = createEndNode({
        name: "end",
        outputs: [stringProperty({ title: "result" })],
      });
      const edge = createControlFlowEdge({
        name: "e1",
        fromNode: start,
        toNode: end,
      });
      const flow = createFlow({
        name: "simple-flow",
        startNode: start,
        nodes: [start, end],
        controlFlowConnections: [edge],
      });
      const result = roundTrip(flow);
      expect(result["componentType"]).toBe("Flow");
      expect(result["name"]).toBe("simple-flow");
    });

    it("should round-trip a multi-node flow", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: createOpenAiCompatibleConfig({
          name: "llm-config",
          url: "http://localhost",
          modelId: "gpt-4",
        }),
        promptTemplate: "Translate: {{text}}",
      });
      const flow = FlowBuilder.buildLinearFlow({
        nodes: [llm],
        name: "translate-flow",
      });
      const result = roundTrip(flow);
      expect(result["componentType"]).toBe("Flow");
      expect(result["name"]).toBe("translate-flow");
      const nodes = result["nodes"] as Record<string, unknown>[];
      // start + llm + end
      expect(nodes.length).toBeGreaterThanOrEqual(3);
    });
  });
});
