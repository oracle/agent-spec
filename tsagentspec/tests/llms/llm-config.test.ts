import { describe, it, expect } from "vitest";
import {
  LlmGenerationConfigSchema,
  OpenAIAPIType,
} from "../../src/index.js";

describe("LlmGenerationConfig", () => {
  it("should parse with all fields", () => {
    const config = LlmGenerationConfigSchema.parse({
      maxTokens: 1024,
      temperature: 0.7,
      topP: 0.9,
    });
    expect(config.maxTokens).toBe(1024);
    expect(config.temperature).toBe(0.7);
    expect(config.topP).toBe(0.9);
  });

  it("should allow all fields to be optional", () => {
    const config = LlmGenerationConfigSchema.parse({});
    expect(config.maxTokens).toBeUndefined();
    expect(config.temperature).toBeUndefined();
    expect(config.topP).toBeUndefined();
  });

  it("should allow extra fields (passthrough)", () => {
    const config = LlmGenerationConfigSchema.parse({
      maxTokens: 100,
      customParam: "value",
      anotherParam: 42,
    });
    expect(config.maxTokens).toBe(100);
    expect((config as Record<string, unknown>)["customParam"]).toBe("value");
    expect((config as Record<string, unknown>)["anotherParam"]).toBe(42);
  });

  it("should reject non-integer maxTokens", () => {
    expect(() =>
      LlmGenerationConfigSchema.parse({ maxTokens: 10.5 }),
    ).toThrow();
  });
});

describe("OpenAIAPIType", () => {
  it("should define CHAT_COMPLETIONS", () => {
    expect(OpenAIAPIType.CHAT_COMPLETIONS).toBe("chat_completions");
  });

  it("should define RESPONSES", () => {
    expect(OpenAIAPIType.RESPONSES).toBe("responses");
  });
});
