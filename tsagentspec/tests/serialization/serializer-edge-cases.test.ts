import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createVllmConfig,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("AgentSpecSerializer YAML disaggregated", () => {
  it("should return a tuple when exportDisaggregatedComponents=true", () => {
    const serializer = new AgentSpecSerializer();
    const llmConfig = createVllmConfig({
      name: "shared-llm",
      url: "http://localhost:8000",
      modelId: "llama",
    });
    const agent = createAgent({
      name: "agent",
      llmConfig,
      systemPrompt: "Hello",
    });
    const [mainYaml, disagYaml] = serializer.toYaml(agent, {
      disaggregatedComponents: [llmConfig],
      exportDisaggregatedComponents: true,
    }) as [string, string];

    expect(mainYaml).toContain("component_type: Agent");
    expect(mainYaml).toContain("$component_ref:");
    expect(disagYaml).toContain("$referenced_components:");
  });
});

describe("AgentSpecSerializer disaggregate root component", () => {
  it("should throw when trying to disaggregate the root component", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    expect(() =>
      serializer.toJson(agent, {
        disaggregatedComponents: [agent],
        exportDisaggregatedComponents: true,
      }),
    ).toThrow("Cannot disaggregate the root component");
  });
});
