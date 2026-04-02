import { describe, it, expect } from "vitest";
import {
  createConversationSummarizationTransform,
  createMessageSummarizationTransform,
  createOpenAiCompatibleConfig,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("ConversationSummarizationTransform validation", () => {
  it("should throw when minNumMessages > maxNumMessages", () => {
    expect(() =>
      createConversationSummarizationTransform({
        name: "conv-summary",
        llm: makeLlmConfig(),
        minNumMessages: 100,
        maxNumMessages: 10,
      }),
    ).toThrow("minNumMessages (100) must be <= maxNumMessages (10)");
  });

  it("should accept minNumMessages equal to maxNumMessages", () => {
    const transform = createConversationSummarizationTransform({
      name: "conv-summary",
      llm: makeLlmConfig(),
      minNumMessages: 25,
      maxNumMessages: 25,
    });
    expect(transform.minNumMessages).toBe(25);
    expect(transform.maxNumMessages).toBe(25);
  });

  it("should accept a custom datastore", () => {
    const transform = createConversationSummarizationTransform({
      name: "conv-summary",
      llm: makeLlmConfig(),
      datastore: { type: "redis", host: "localhost" },
    });
    expect(transform.datastore).toEqual({ type: "redis", host: "localhost" });
  });

  it("should have default summarizedConversationTemplate", () => {
    const transform = createConversationSummarizationTransform({
      name: "conv-summary",
      llm: makeLlmConfig(),
    });
    expect(transform.summarizedConversationTemplate).toContain(
      "{{summary}}",
    );
  });

  it("should accept custom cache settings", () => {
    const transform = createConversationSummarizationTransform({
      name: "conv-summary",
      llm: makeLlmConfig(),
      maxCacheSize: 5000,
      maxCacheLifetime: 7200,
      cacheCollectionName: "custom-cache",
    });
    expect(transform.maxCacheSize).toBe(5000);
    expect(transform.maxCacheLifetime).toBe(7200);
    expect(transform.cacheCollectionName).toBe("custom-cache");
  });
});

describe("MessageSummarizationTransform edge cases", () => {
  it("should accept a custom datastore", () => {
    const transform = createMessageSummarizationTransform({
      name: "msg-summary",
      llm: makeLlmConfig(),
      datastore: { type: "memory" },
    });
    expect(transform.datastore).toEqual({ type: "memory" });
  });

  it("should have default summarizedMessageTemplate", () => {
    const transform = createMessageSummarizationTransform({
      name: "msg-summary",
      llm: makeLlmConfig(),
    });
    expect(transform.summarizedMessageTemplate).toContain("{{summary}}");
  });

  it("should accept custom cache settings", () => {
    const transform = createMessageSummarizationTransform({
      name: "msg-summary",
      llm: makeLlmConfig(),
      maxCacheSize: 2000,
      maxCacheLifetime: 3600,
      cacheCollectionName: "msg-cache",
    });
    expect(transform.maxCacheSize).toBe(2000);
    expect(transform.maxCacheLifetime).toBe(3600);
    expect(transform.cacheCollectionName).toBe("msg-cache");
  });
});
