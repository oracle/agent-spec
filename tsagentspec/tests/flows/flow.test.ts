import { describe, it, expect } from "vitest";
import {
  createFlow,
  createStartNode,
  createEndNode,
  createLlmNode,
  createControlFlowEdge,
  createOpenAiCompatibleConfig,
  stringProperty,
  integerProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("Flow", () => {
  it("should create a simple flow", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end,
    });
    const flow = createFlow({
      name: "simple-flow",
      startNode: start,
      nodes: [start, end],
      controlFlowConnections: [edge],
    });
    expect(flow.componentType).toBe("Flow");
    expect(flow.name).toBe("simple-flow");
  });

  it("should auto-generate an id", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, end],
      controlFlowConnections: [edge],
    });
    expect(flow.id).toBeDefined();
  });

  it("should infer inputs from start node", () => {
    const start = createStartNode({
      name: "start",
      inputs: [stringProperty({ title: "query" })],
    });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, end],
      controlFlowConnections: [edge],
    });
    expect(flow.inputs).toHaveLength(1);
    expect(flow.inputs![0]!.title).toBe("query");
  });

  it("should infer outputs from EndNode outputs", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({
      name: "end",
      outputs: [stringProperty({ title: "result" })],
    });
    const edge = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, end],
      controlFlowConnections: [edge],
    });
    expect(flow.outputs).toHaveLength(1);
    expect(flow.outputs![0]!.title).toBe("result");
  });

  it("should infer outputs as intersection of all EndNode outputs", () => {
    const start = createStartNode({ name: "start" });
    const end1 = createEndNode({
      name: "end1",
      outputs: [
        stringProperty({ title: "common" }),
        stringProperty({ title: "only_end1" }),
      ],
    });
    const end2 = createEndNode({
      name: "end2",
      outputs: [
        stringProperty({ title: "common" }),
        stringProperty({ title: "only_end2" }),
      ],
    });
    const e1 = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end1,
    });
    const e2 = createControlFlowEdge({
      name: "e2",
      fromNode: start,
      toNode: end2,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, end1, end2],
      controlFlowConnections: [e1, e2],
    });
    const outputTitles = flow.outputs!.map((o) => o.title);
    expect(outputTitles).toContain("common");
    expect(outputTitles).not.toContain("only_end1");
    expect(outputTitles).not.toContain("only_end2");
  });

  it("should use custom inputs when provided", () => {
    const start = createStartNode({
      name: "start",
      inputs: [stringProperty({ title: "query" })],
    });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, end],
      controlFlowConnections: [edge],
      inputs: [integerProperty({ title: "custom_input" })],
    });
    expect(flow.inputs).toHaveLength(1);
    expect(flow.inputs![0]!.title).toBe("custom_input");
  });

  it("should create a multi-node flow", () => {
    const start = createStartNode({ name: "start" });
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Translate: {{text}}",
    });
    const end = createEndNode({ name: "end" });
    const e1 = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: llm,
    });
    const e2 = createControlFlowEdge({
      name: "e2",
      fromNode: llm,
      toNode: end,
    });
    const flow = createFlow({
      name: "translate-flow",
      startNode: start,
      nodes: [start, llm, end],
      controlFlowConnections: [e1, e2],
    });
    expect(flow.nodes).toHaveLength(3);
    expect(flow.controlFlowConnections).toHaveLength(2);
  });

  it("should be frozen", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({
      name: "e1",
      fromNode: start,
      toNode: end,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, end],
      controlFlowConnections: [edge],
    });
    expect(Object.isFrozen(flow)).toBe(true);
  });
});
