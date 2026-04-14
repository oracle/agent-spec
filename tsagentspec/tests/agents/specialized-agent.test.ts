import { describe, it, expect } from "vitest";
import {
  createSpecializedAgent,
  createAgentSpecializationParameters,
  createAgent,
  createOpenAiCompatibleConfig,
  createServerTool,
  stringProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeAgent() {
  return createAgent({
    name: "base-agent",
    llmConfig: makeLlmConfig(),
    systemPrompt: "You are a {{role}}.",
  });
}

describe("AgentSpecializationParameters", () => {
  it("should create with required fields", () => {
    const params = createAgentSpecializationParameters({
      name: "spec-params",
    });
    expect(params.componentType).toBe("AgentSpecializationParameters");
    expect(params.name).toBe("spec-params");
  });

  it("should extract template placeholders as inputs", () => {
    const params = createAgentSpecializationParameters({
      name: "spec-params",
      additionalInstructions: "Focus on {{topic}}.",
    });
    expect(params.inputs).toHaveLength(1);
    expect(params.inputs![0]!.title).toBe("topic");
  });

  it("should accept additional tools", () => {
    const tool = createServerTool({
      name: "my-tool",
      inputs: [stringProperty({ title: "q" })],
    });
    const params = createAgentSpecializationParameters({
      name: "spec-params",
      additionalTools: [tool],
    });
    expect(params.additionalTools).toHaveLength(1);
  });

  it("should be frozen", () => {
    const params = createAgentSpecializationParameters({ name: "p" });
    expect(Object.isFrozen(params)).toBe(true);
  });
});

describe("SpecializedAgent", () => {
  it("should create with required fields", () => {
    const agent = makeAgent();
    const params = createAgentSpecializationParameters({
      name: "spec-params",
      additionalInstructions: "Be concise.",
    });
    const specialized = createSpecializedAgent({
      name: "specialized",
      agent,
      agentSpecializationParameters: params,
    });
    expect(specialized.componentType).toBe("SpecializedAgent");
    expect(specialized.agent.name).toBe("base-agent");
  });

  it("should merge inputs from agent and specialization parameters", () => {
    const agent = makeAgent(); // has {{role}} input
    const params = createAgentSpecializationParameters({
      name: "spec-params",
      additionalInstructions: "Focus on {{topic}}.",
    });
    const specialized = createSpecializedAgent({
      name: "specialized",
      agent,
      agentSpecializationParameters: params,
    });
    const inputTitles = specialized.inputs!.map((i) => i.title).sort();
    expect(inputTitles).toContain("role");
    expect(inputTitles).toContain("topic");
  });

  it("should deduplicate overlapping inputs", () => {
    const agent = createAgent({
      name: "base",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Handle {{query}}.",
    });
    const params = createAgentSpecializationParameters({
      name: "params",
      additionalInstructions: "Process {{query}} carefully.",
    });
    const specialized = createSpecializedAgent({
      name: "specialized",
      agent,
      agentSpecializationParameters: params,
    });
    const queryInputs = specialized.inputs!.filter((i) => i.title === "query");
    expect(queryInputs).toHaveLength(1);
  });

  it("should be frozen", () => {
    const specialized = createSpecializedAgent({
      name: "specialized",
      agent: makeAgent(),
      agentSpecializationParameters: createAgentSpecializationParameters({
        name: "p",
      }),
    });
    expect(Object.isFrozen(specialized)).toBe(true);
  });
});
