import { describe, it, expect } from "vitest";
import {
  createMessageSummarizationTransform,
  createConversationSummarizationTransform,
  createOpenAiCompatibleConfig,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("MessageSummarizationTransform", () => {
  it("should create with required fields", () => {
    const transform = createMessageSummarizationTransform({
      name: "msg-summary",
      llm: makeLlmConfig(),
    });
    expect(transform.componentType).toBe("MessageSummarizationTransform");
    expect(transform.maxMessageSize).toBe(20000);
  });

  it("should accept custom parameters", () => {
    const transform = createMessageSummarizationTransform({
      name: "msg-summary",
      llm: makeLlmConfig(),
      maxMessageSize: 5000,
      summarizationInstructions: "Summarize briefly.",
      cacheCollectionName: "my-cache",
    });
    expect(transform.maxMessageSize).toBe(5000);
    expect(transform.summarizationInstructions).toBe("Summarize briefly.");
    expect(transform.cacheCollectionName).toBe("my-cache");
  });

  it("should be frozen", () => {
    const transform = createMessageSummarizationTransform({
      name: "t",
      llm: makeLlmConfig(),
    });
    expect(Object.isFrozen(transform)).toBe(true);
  });
});

describe("ConversationSummarizationTransform", () => {
  it("should create with required fields", () => {
    const transform = createConversationSummarizationTransform({
      name: "conv-summary",
      llm: makeLlmConfig(),
    });
    expect(transform.componentType).toBe(
      "ConversationSummarizationTransform",
    );
    expect(transform.maxNumMessages).toBe(50);
    expect(transform.minNumMessages).toBe(10);
  });

  it("should accept custom parameters", () => {
    const transform = createConversationSummarizationTransform({
      name: "conv-summary",
      llm: makeLlmConfig(),
      maxNumMessages: 100,
      minNumMessages: 5,
      summarizationInstructions: "Keep it brief.",
    });
    expect(transform.maxNumMessages).toBe(100);
    expect(transform.minNumMessages).toBe(5);
  });

  it("should be frozen", () => {
    const transform = createConversationSummarizationTransform({
      name: "t",
      llm: makeLlmConfig(),
    });
    expect(Object.isFrozen(transform)).toBe(true);
  });
});
