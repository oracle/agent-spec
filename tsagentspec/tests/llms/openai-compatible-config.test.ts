import { describe, it, expect } from "vitest";
import {
  createOpenAiCompatibleConfig,
  OpenAIAPIType,
  AgentSpecSerializer,
  AgentSpecDeserializer,
} from "../../src/index.js";

describe("OpenAiCompatibleConfig", () => {
  it("should create with required fields", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test-llm",
      url: "http://localhost:8000",
      modelId: "gpt-4",
    });
    expect(config.componentType).toBe("OpenAiCompatibleConfig");
    expect(config.name).toBe("test-llm");
    expect(config.url).toBe("http://localhost:8000");
    expect(config.modelId).toBe("gpt-4");
  });

  it("should default apiType to CHAT_COMPLETIONS", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
    });
    expect(config.apiType).toBe(OpenAIAPIType.CHAT_COMPLETIONS);
  });

  it("should accept custom apiType", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
      apiType: OpenAIAPIType.RESPONSES,
    });
    expect(config.apiType).toBe(OpenAIAPIType.RESPONSES);
  });

  it("should auto-generate an id", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
    });
    expect(config.id).toBeDefined();
    expect(config.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
  });

  it("should accept custom id", () => {
    const id = "550e8400-e29b-41d4-a716-446655440000";
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
      id,
    });
    expect(config.id).toBe(id);
  });

  it("should accept defaultGenerationParameters", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
      defaultGenerationParameters: {
        maxTokens: 1024,
        temperature: 0.5,
      },
    });
    expect(config.defaultGenerationParameters).toBeDefined();
    expect(config.defaultGenerationParameters!.maxTokens).toBe(1024);
    expect(config.defaultGenerationParameters!.temperature).toBe(0.5);
  });

  it("should accept apiKey", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
      apiKey: "sk-secret",
    });
    expect(config.apiKey).toBe("sk-secret");
  });

  it("should be frozen", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });

  it("should default metadata to empty object", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
    });
    expect(config.metadata).toEqual({});
  });

  it("should accept TLS fields", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "https://localhost",
      modelId: "model1",
      keyFile: "/path/to/client.key",
      certFile: "/path/to/client.crt",
      caFile: "/path/to/ca.crt",
    });
    expect(config.keyFile).toBe("/path/to/client.key");
    expect(config.certFile).toBe("/path/to/client.crt");
    expect(config.caFile).toBe("/path/to/ca.crt");
  });

  it("should accept provider field", () => {
    const config = createOpenAiCompatibleConfig({
      name: "test",
      url: "http://localhost",
      modelId: "model1",
      provider: "custom-provider",
    });
    expect(config.provider).toBe("custom-provider");
  });

  it("should round-trip with provider field", () => {
    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const config = createOpenAiCompatibleConfig({
      id: "test-id",
      name: "test",
      url: "https://localhost",
      modelId: "model1",
      provider: "my-provider",
    });
    const yaml = serializer.toYaml(config);
    const restored = deserializer.fromYaml(yaml);
    expect(restored).toEqual(config);
  });
});
