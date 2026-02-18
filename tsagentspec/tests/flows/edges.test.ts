import { describe, it, expect } from "vitest";
import {
  createControlFlowEdge,
  createDataFlowEdge,
  createStartNode,
  createEndNode,
  createLlmNode,
  createOpenAiCompatibleConfig,
  stringProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("ControlFlowEdge", () => {
  it("should create with required fields", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "edge1",
      fromNode: start,
      toNode: end,
    });
    expect(edge.componentType).toBe("ControlFlowEdge");
    expect(edge.name).toBe("edge1");
    expect((edge.fromNode as Record<string, unknown>)["name"]).toBe("start");
    expect((edge.toNode as Record<string, unknown>)["name"]).toBe("end");
  });

  it("should accept optional fromBranch", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "edge1",
      fromNode: start,
      toNode: end,
      fromBranch: "next",
    });
    expect(edge.fromBranch).toBe("next");
  });

  it("should default fromBranch to undefined", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "edge1",
      fromNode: start,
      toNode: end,
    });
    expect(edge.fromBranch).toBeUndefined();
  });

  it("should auto-generate an id", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "edge1",
      fromNode: start,
      toNode: end,
    });
    expect(edge.id).toBeDefined();
  });

  it("should be frozen", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "edge1",
      fromNode: start,
      toNode: end,
    });
    expect(Object.isFrozen(edge)).toBe(true);
  });
});

describe("DataFlowEdge", () => {
  it("should create with required fields", () => {
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Do something with {{input}}",
    });
    const end = createEndNode({
      name: "end",
      inputs: [stringProperty({ title: "generated_text" })],
    });
    const edge = createDataFlowEdge({
      name: "data-edge",
      sourceNode: llm,
      sourceOutput: "generated_text",
      destinationNode: end,
      destinationInput: "generated_text",
    });
    expect(edge.componentType).toBe("DataFlowEdge");
    expect(edge.sourceOutput).toBe("generated_text");
    expect(edge.destinationInput).toBe("generated_text");
  });

  it("should auto-generate an id", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createDataFlowEdge({
      name: "data-edge",
      sourceNode: start,
      sourceOutput: "x",
      destinationNode: end,
      destinationInput: "x",
    });
    expect(edge.id).toBeDefined();
  });

  it("should be frozen", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createDataFlowEdge({
      name: "data-edge",
      sourceNode: start,
      sourceOutput: "x",
      destinationNode: end,
      destinationInput: "x",
    });
    expect(Object.isFrozen(edge)).toBe(true);
  });

  it("should throw when sourceOutput does not exist on sourceNode outputs", () => {
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Say hello",
    });
    const end = createEndNode({
      name: "end",
      inputs: [stringProperty({ title: "generated_text" })],
    });
    expect(() =>
      createDataFlowEdge({
        name: "bad-edge",
        sourceNode: llm,
        sourceOutput: "nonexistent_output",
        destinationNode: end,
        destinationInput: "generated_text",
      }),
    ).toThrow(/nonexistent_output.*source node.*llm/);
  });

  it("should throw when destinationInput does not exist on destinationNode inputs", () => {
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Say hello",
    });
    const end = createEndNode({
      name: "end",
      inputs: [stringProperty({ title: "generated_text" })],
    });
    expect(() =>
      createDataFlowEdge({
        name: "bad-edge",
        sourceNode: llm,
        sourceOutput: "generated_text",
        destinationNode: end,
        destinationInput: "nonexistent_input",
      }),
    ).toThrow(/nonexistent_input.*destination node.*end/);
  });

  it("should throw when source and destination property types are incompatible", () => {
    const source = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Say hello",
    });
    const dest = createEndNode({
      name: "end",
      inputs: [
        { jsonSchema: { title: "generated_text", type: "null" }, title: "generated_text", type: "null" },
      ],
    });
    expect(() =>
      createDataFlowEdge({
        name: "type-mismatch",
        sourceNode: source,
        sourceOutput: "generated_text",
        destinationNode: dest,
        destinationInput: "generated_text",
      }),
    ).toThrow(/incompatible types/);
  });

  it("should allow edges when nodes have no inputs/outputs defined", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    // No outputs on start, no inputs on end — validation is skipped
    const edge = createDataFlowEdge({
      name: "loose-edge",
      sourceNode: start,
      sourceOutput: "anything",
      destinationNode: end,
      destinationInput: "anything",
    });
    expect(edge.componentType).toBe("DataFlowEdge");
  });
});
