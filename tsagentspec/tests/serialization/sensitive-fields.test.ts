import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createOllamaConfig,
  createVllmConfig,
  createOpenAiConfig,
  createRemoteTool,
  stringProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("sensitive field exclusion", () => {
  it("should exclude apiKey from OpenAiCompatibleConfig", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiCompatibleConfig({
      name: "llm",
      url: "http://localhost",
      modelId: "gpt-4",
      apiKey: "sk-secret",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("api_key" in llmDict).toBe(false);
  });

  it("should exclude apiKey from OllamaConfig", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOllamaConfig({
      name: "ollama",
      url: "http://localhost:11434",
      modelId: "llama3",
      apiKey: "secret",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("api_key" in llmDict).toBe(false);
  });

  it("should exclude apiKey from VllmConfig", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createVllmConfig({
      name: "vllm",
      url: "http://localhost:8000",
      modelId: "model",
      apiKey: "secret",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("api_key" in llmDict).toBe(false);
  });

  it("should exclude apiKey from OpenAiConfig", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiConfig({
      name: "openai",
      modelId: "gpt-4",
      apiKey: "sk-secret",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("api_key" in llmDict).toBe(false);
  });

  it("should exclude sensitiveHeaders from RemoteTool", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createRemoteTool({
      name: "remote",
      url: "http://api.example.com",
      httpMethod: "POST",
      inputs: [stringProperty({ title: "q" })],
      sensitiveHeaders: { Authorization: "Bearer secret" },
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("sensitive_headers" in tools[0]!).toBe(false);
  });

  it("should keep non-sensitive fields intact", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiCompatibleConfig({
      name: "llm",
      url: "http://localhost",
      modelId: "gpt-4",
      apiKey: "sk-secret",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const dict = serializer.toDict(agent) as Record<string, unknown>;
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect(llmDict["url"]).toBe("http://localhost");
    expect(llmDict["model_id"]).toBe("gpt-4");
    expect(llmDict["name"]).toBe("llm");
  });
});
