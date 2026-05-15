import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createOllamaConfig,
  createVllmConfig,
  createOpenAiConfig,
  createRemoteTool,
  createGeminiConfig,
  createGeminiAIStudioAuthConfig,
  createGeminiVertexAIAuthConfig,
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("sensitive_headers" in tools[0]!).toBe(false);
  });

  it("should exclude apiKey from GeminiAIStudioAuthConfig", () => {
    const serializer = new AgentSpecSerializer();
    const auth = createGeminiAIStudioAuthConfig({ id: "auth-id", name: "auth", apiKey: "gk-secret" });
    const config = createGeminiConfig({
      id: "gemini-id",
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth,
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).not.toContain("gk-secret");
    expect(yaml).not.toContain("api_key");
  });

  it("should exclude credentials from GeminiVertexAIAuthConfig", () => {
    const serializer = new AgentSpecSerializer();
    const auth = createGeminiVertexAIAuthConfig({
      id: "va-id",
      name: "va",
      credentials: { private_key: "secret-key-data" },
    });
    const config = createGeminiConfig({
      id: "gemini-id",
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth,
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).not.toContain("secret-key-data");
    expect(yaml).not.toContain("credentials");
  });

  it("should exclude TLS cert fields from OpenAiCompatibleConfig", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiCompatibleConfig({
      name: "llm",
      url: "https://localhost",
      modelId: "model",
      keyFile: "/secret/client.key",
      certFile: "/secret/client.crt",
      caFile: "/secret/ca.crt",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect("key_file" in llmDict).toBe(false);
    expect("cert_file" in llmDict).toBe(false);
    expect("ca_file" in llmDict).toBe(false);
  });

  it("should include sensitive fields when includeSensitiveFields is true", () => {
    const serializer = new AgentSpecSerializer();
    const llm = createOpenAiCompatibleConfig({
      name: "llm",
      url: "http://localhost",
      modelId: "gpt-4",
      apiKey: "sk-secret",
      keyFile: "/secret/client.key",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: llm,
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, { includeSensitiveFields: true }) as string;
    const dict = JSON.parse(json);
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect(llmDict["api_key"]).toBe("sk-secret");
    expect(llmDict["key_file"]).toBe("/secret/client.key");
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
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
    const llmDict = dict["llm_config"] as Record<string, unknown>;
    expect(llmDict["url"]).toBe("http://localhost");
    expect(llmDict["model_id"]).toBe("gpt-4");
    expect(llmDict["name"]).toBe("llm");
  });
});
