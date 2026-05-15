import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecVersion,
  createAgent,
  createOpenAiCompatibleConfig,
  createServerTool,
  createBuiltinTool,
  createMCPToolBox,
  createStdioTransport,
  createLlmConfig,
  createGeminiConfig,
  createGeminiAIStudioAuthConfig,
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
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as string;
    const dict = JSON.parse(json);
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
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_2,
    }) as string;
    const dict = JSON.parse(json);
    expect("human_in_the_loop" in dict).toBe(true);
  });

  it("should throw when serializing MCPToolBox at version before 25.4.2", () => {
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
    expect(() =>
      serializer.toJson(agent, {
        agentspecVersion: AgentSpecVersion.V25_4_1,
      }),
    ).toThrow(/Invalid agentspec_version.*25\.4\.1.*25\.4\.2.*toolbox/);
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
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as string;
    const dict = JSON.parse(json);
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
    const json = serializer.toJson(agent) as string;
    const dictCurrent = JSON.parse(json);
    const toolsCurrent = dictCurrent["tools"] as Record<string, unknown>[];
    const btCurrent = toolsCurrent.find(
      (t) => t["component_type"] === "BuiltinTool",
    );
    expect(btCurrent).toBeDefined();
    expect(btCurrent!["tool_type"]).toBe("code_execution");
  });

  it("should exclude MCPToolBox requiresConfirmation for versions before 26.2.0", () => {
    const serializer = new AgentSpecSerializer();
    const toolbox = createMCPToolBox({
      name: "toolbox",
      clientTransport: createStdioTransport({
        name: "stdio",
        command: "node",
      }),
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      toolboxes: [toolbox],
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_2,
    }) as string;
    const dict = JSON.parse(json);
    const toolboxes = dict["toolboxes"] as Record<string, unknown>[];
    expect("requires_confirmation" in toolboxes[0]!).toBe(false);
  });

  it("should include MCPToolBox requiresConfirmation for version 26.2.0+", () => {
    const serializer = new AgentSpecSerializer();
    const toolbox = createMCPToolBox({
      name: "toolbox",
      clientTransport: createStdioTransport({
        name: "stdio",
        command: "node",
      }),
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      toolboxes: [toolbox],
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V26_2_0,
    }) as string;
    const dict = JSON.parse(json);
    const toolboxes = dict["toolboxes"] as Record<string, unknown>[];
    expect("requires_confirmation" in toolboxes[0]!).toBe(true);
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
    expect("human_in_the_loop" in dict).toBe(true);
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("requires_confirmation" in tools[0]!).toBe(true);
  });

  it("should throw when serializing LlmConfig at version before 26.2.0", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createLlmConfig({ name: "generic", modelId: "gpt-4o" });
    expect(() =>
      serializer.toYaml(llm, { agentspecVersion: AgentSpecVersion.V25_4_2 }),
    ).toThrow(/26\.2\.0/);
  });

  it("should throw when serializing GeminiConfig at version before 26.2.0", () => {
    const serializer = new AgentSpecSerializer();
    const gemini = createGeminiConfig({
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth: createGeminiAIStudioAuthConfig({ name: "auth" }),
    });
    expect(() =>
      serializer.toYaml(gemini, { agentspecVersion: AgentSpecVersion.V25_4_2 }),
    ).toThrow(/26\.2\.0/);
  });

  it("should exclude retryPolicy from OpenAiCompatibleConfig for versions before 26.2.0", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiCompatibleConfig({
      name: "llm",
      url: "http://localhost",
      modelId: "model",
      retryPolicy: { maxAttempts: 5 },
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_2,
    }) as string;
    const dict = JSON.parse(json);
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("retry_policy" in llmDict).toBe(false);
  });

  it("should include retryPolicy from OpenAiCompatibleConfig for version 26.2.0+", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiCompatibleConfig({
      name: "llm",
      url: "http://localhost",
      modelId: "model",
      retryPolicy: { maxAttempts: 5 },
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V26_2_0,
    }) as string;
    const dict = JSON.parse(json);
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("retry_policy" in llmDict).toBe(true);
    expect((llmDict["retry_policy"] as Record<string, unknown>)["max_attempts"]).toBe(5);
  });

  it("should throw when serializing BuiltinTool at version before 25.4.2", () => {
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
    expect(() =>
      serializer.toJson(agent, {
        agentspecVersion: AgentSpecVersion.V25_4_1,
      }),
    ).toThrow(/Invalid agentspec_version.*25\.4\.1.*25\.4\.2.*code-exec/);
  });
});
