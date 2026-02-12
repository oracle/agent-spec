import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecVersion,
  createAgent,
  createOpenAiCompatibleConfig,
  createServerTool,
  createBuiltinTool,
  createSwarm,
  createMCPToolBox,
  createStdioTransport,
  stringProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("version-gated field serialization", () => {
  it("should exclude humanInTheLoop for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      humanInTheLoop: false,
    });
    const dict = serializer.toDict(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as Record<string, unknown>;
    expect("human_in_the_loop" in dict).toBe(false);
  });

  it("should include humanInTheLoop for version 25.4.2+", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      humanInTheLoop: false,
    });
    const dict = serializer.toDict(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_2,
    }) as Record<string, unknown>;
    expect("human_in_the_loop" in dict).toBe(true);
  });

  it("should exclude toolboxes for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const toolbox = createMCPToolBox({
      name: "toolbox",
      clientTransport: createStdioTransport({
        name: "stdio",
        command: "node",
      }),
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      toolboxes: [toolbox],
    });
    const dict = serializer.toDict(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as Record<string, unknown>;
    expect("toolboxes" in dict).toBe(false);
  });

  it("should exclude requiresConfirmation on tools for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createServerTool({
      name: "tool",
      inputs: [stringProperty({ title: "q" })],
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
    });
    const dict = serializer.toDict(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as Record<string, unknown>;
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("requires_confirmation" in tools[0]!).toBe(false);
  });

  it("should version-gate BuiltinTool _self fields for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      configuration: { language: "python" },
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
    });

    // For current version, BuiltinTool should appear with all fields
    const dictCurrent = serializer.toDict(agent) as Record<string, unknown>;
    const toolsCurrent = dictCurrent["tools"] as Record<string, unknown>[];
    const btCurrent = toolsCurrent.find(
      (t) => t["component_type"] === "BuiltinTool",
    );
    expect(btCurrent).toBeDefined();
    expect(btCurrent!["tool_type"]).toBe("code_execution");
  });

  it("should include everything for current version", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createServerTool({
      name: "tool",
      inputs: [stringProperty({ title: "q" })],
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
      humanInTheLoop: false,
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    expect("human_in_the_loop" in dict).toBe(true);
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("requires_confirmation" in tools[0]!).toBe(true);
  });
});
