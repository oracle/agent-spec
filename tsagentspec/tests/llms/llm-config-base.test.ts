import { describe, it, expect } from "vitest";
import {
  createLlmConfig,
  AgentSpecSerializer,
  AgentSpecDeserializer,
  AgentSpecVersion,
} from "../../src/index.js";

const serializer = new AgentSpecSerializer();
const deserializer = new AgentSpecDeserializer();

describe("LlmConfig (bare)", () => {
  it("should create with only required fields", () => {
    const config = createLlmConfig({ name: "generic", modelId: "gpt-4o" });
    expect(config.componentType).toBe("LlmConfig");
    expect(config.modelId).toBe("gpt-4o");
    expect(config.provider).toBeUndefined();
    expect(config.apiProvider).toBeUndefined();
    expect(config.apiType).toBeUndefined();
    expect(config.url).toBeUndefined();
    expect(config.apiKey).toBeUndefined();
  });

  it("should accept all optional fields", () => {
    const config = createLlmConfig({
      name: "generic",
      modelId: "gpt-4o",
      provider: "openai",
      apiProvider: "openai",
      apiType: "chat_completions",
      url: "https://api.openai.com/v1",
      apiKey: "sk-test",
    });
    expect(config.provider).toBe("openai");
    expect(config.apiProvider).toBe("openai");
    expect(config.apiType).toBe("chat_completions");
    expect(config.url).toBe("https://api.openai.com/v1");
    expect(config.apiKey).toBe("sk-test");
  });

  it("should auto-generate an id and be frozen", () => {
    const config = createLlmConfig({ name: "generic", modelId: "m" });
    expect(config.id).toBeDefined();
    expect(Object.isFrozen(config)).toBe(true);
  });

  it("should serialise to snake_case YAML with expected fields", () => {
    const config = createLlmConfig({
      id: "test-id",
      name: "generic",
      modelId: "gpt-4o",
      provider: "openai",
      apiProvider: "openai",
      apiType: "chat_completions",
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).toContain("component_type: LlmConfig");
    expect(yaml).toContain("model_id: gpt-4o");
    expect(yaml).toContain("provider: openai");
    expect(yaml).toContain("api_provider: openai");
    expect(yaml).toContain("api_type: chat_completions");
  });

  it("should exclude apiKey from serialised output (sensitive field)", () => {
    const config = createLlmConfig({
      id: "test-id",
      name: "generic",
      modelId: "gpt-4o",
      apiKey: "sk-secret",
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).not.toContain("sk-secret");
  });

  it("should round-trip without apiKey", () => {
    const config = createLlmConfig({
      id: "test-id",
      name: "generic",
      modelId: "gpt-4o",
      provider: "openai",
      apiProvider: "openai",
      apiType: "chat_completions",
      url: "https://api.openai.com/v1",
    });
    const yaml = serializer.toYaml(config);
    const restored = deserializer.fromYaml(yaml);
    expect(restored).toEqual(config);
  });

  it("should throw when serialising at version before 26.2.0", () => {
    const config = createLlmConfig({ name: "generic", modelId: "m" });
    expect(() =>
      serializer.toYaml(config, { agentspecVersion: AgentSpecVersion.V25_4_2 }),
    ).toThrow(/26\.2\.0/);
  });
});
