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
});
