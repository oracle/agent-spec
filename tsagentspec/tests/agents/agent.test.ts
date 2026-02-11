import { describe, it, expect } from "vitest";
import {
  createAgent,
  createOpenAiCompatibleConfig,
  createVllmConfig,
  createServerTool,
  stringProperty,
  integerProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("Agent", () => {
  it("should create with required fields", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are a helpful assistant.",
    });
    expect(agent.componentType).toBe("Agent");
    expect(agent.name).toBe("test-agent");
    expect(agent.systemPrompt).toBe("You are a helpful assistant.");
    expect(agent.llmConfig.componentType).toBe("OpenAiCompatibleConfig");
  });

  it("should auto-generate an id", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(agent.id).toBeDefined();
    expect(agent.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it("should default humanInTheLoop to true", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(agent.humanInTheLoop).toBe(true);
  });

  it("should accept humanInTheLoop=false", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
      humanInTheLoop: false,
    });
    expect(agent.humanInTheLoop).toBe(false);
  });

  it("should default tools to empty array", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(agent.tools).toEqual([]);
  });

  it("should default toolboxes to empty array", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(agent.toolboxes).toEqual([]);
  });

  it("should default transforms to empty array", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(agent.transforms).toEqual([]);
  });

  it("should default outputs to empty array", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(agent.outputs).toEqual([]);
  });

  it("should infer inputs from system prompt placeholders", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt:
        "You are a {{role}} assistant for {{company}}. Help with {{task}}.",
    });
    expect(agent.inputs).toBeDefined();
    const inputTitles = agent.inputs!.map((i) => i.title);
    expect(inputTitles).toContain("role");
    expect(inputTitles).toContain("company");
    expect(inputTitles).toContain("task");
    expect(agent.inputs).toHaveLength(3);
  });

  it("should have empty inputs when no placeholders", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are a helpful assistant.",
    });
    expect(agent.inputs).toEqual([]);
  });

  it("should use custom inputs when provided", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are a {{role}} assistant.",
      inputs: [integerProperty({ title: "custom_input" })],
    });
    expect(agent.inputs).toHaveLength(1);
    expect(agent.inputs![0]!.title).toBe("custom_input");
    expect(agent.inputs![0]!.type).toBe("integer");
  });

  it("should accept tools", () => {
    const tool = createServerTool({
      name: "search-tool",
      inputs: [stringProperty({ title: "query" })],
    });
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
      tools: [tool],
    });
    expect(agent.tools).toHaveLength(1);
    expect(agent.tools[0]!.name).toBe("search-tool");
  });

  it("should accept description and metadata", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
      description: "A test agent",
      metadata: { version: "1.0" },
    });
    expect(agent.description).toBe("A test agent");
    expect(agent.metadata).toEqual({ version: "1.0" });
  });

  it("should be frozen", () => {
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    expect(Object.isFrozen(agent)).toBe(true);
  });

  it("should work with different LLM config types", () => {
    const vllmConfig = createVllmConfig({
      name: "vllm",
      url: "http://localhost:8000",
      modelId: "llama-2",
    });
    const agent = createAgent({
      name: "vllm-agent",
      llmConfig: vllmConfig,
      systemPrompt: "You are helpful.",
    });
    expect(agent.llmConfig.componentType).toBe("VllmConfig");
  });
});
