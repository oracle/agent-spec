import { describe, it, expect } from "vitest";
import {
  createOpenAiConfig,
  OpenAIAPIType,
} from "../../src/index.js";

describe("OpenAiConfig", () => {
  it("should create with required fields", () => {
    const config = createOpenAiConfig({
      name: "openai-llm",
      modelId: "gpt-4o",
    });
    expect(config.componentType).toBe("OpenAiConfig");
    expect(config.name).toBe("openai-llm");
    expect(config.modelId).toBe("gpt-4o");
  });

  it("should NOT have a url field", () => {
    const config = createOpenAiConfig({
      name: "test",
      modelId: "gpt-4",
    });
    expect("url" in config).toBe(false);
  });

  it("should default apiType to CHAT_COMPLETIONS", () => {
    const config = createOpenAiConfig({
      name: "test",
      modelId: "gpt-4",
    });
    expect(config.apiType).toBe(OpenAIAPIType.CHAT_COMPLETIONS);
  });

  it("should accept a custom apiType", () => {
    const config = createOpenAiConfig({
      name: "test",
      modelId: "gpt-4",
      apiType: OpenAIAPIType.RESPONSES,
    });
    expect(config.apiType).toBe("responses");
  });

  it("should auto-generate an id", () => {
    const config = createOpenAiConfig({
      name: "test",
      modelId: "gpt-4",
    });
    expect(config.id).toBeDefined();
  });

  it("should be frozen", () => {
    const config = createOpenAiConfig({
      name: "test",
      modelId: "gpt-4",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });

  it("should accept defaultGenerationParameters", () => {
    const config = createOpenAiConfig({
      name: "test",
      modelId: "gpt-4",
      defaultGenerationParameters: {
        temperature: 0.8,
        topP: 0.95,
      },
    });
    expect(config.defaultGenerationParameters!.temperature).toBe(0.8);
    expect(config.defaultGenerationParameters!.topP).toBe(0.95);
  });
});
