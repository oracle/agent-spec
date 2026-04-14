import { describe, it, expect } from "vitest";
import {
  createFlow,
  createStartNode,
  createEndNode,
  createLlmNode,
  createControlFlowEdge,
  createDataFlowEdge,
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
    const llm = createLlmNode({
      name: "router",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Route",
    });
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
    const e0 = createControlFlowEdge({
      name: "e0",
      fromNode: start,
      toNode: llm,
    });
    const e1 = createControlFlowEdge({
      name: "e1",
      fromNode: llm,
      toNode: end1,
    });
    const e2 = createControlFlowEdge({
      name: "e2",
      fromNode: llm,
      toNode: end2,
    });
    const flow = createFlow({
      name: "flow",
      startNode: start,
      nodes: [start, llm, end1, end2],
      controlFlowConnections: [e0, e1, e2],
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

  it("should reject flow with no StartNode", () => {
    const end = createEndNode({ name: "end" });
    const start = createStartNode({ name: "start" });
    const edge = createControlFlowEdge({ name: "e1", fromNode: start, toNode: end });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [end],
        controlFlowConnections: [edge],
      }),
    ).toThrow(/exactly one StartNode/);
  });

  it("should reject flow with two StartNodes", () => {
    const start1 = createStartNode({ name: "start1" });
    const start2 = createStartNode({ name: "start2" });
    const end = createEndNode({ name: "end" });
    const e1 = createControlFlowEdge({ name: "e1", fromNode: start1, toNode: end });
    const e2 = createControlFlowEdge({ name: "e2", fromNode: start2, toNode: end });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start1,
        nodes: [start1, start2, end],
        controlFlowConnections: [e1, e2],
      }),
    ).toThrow(/exactly one StartNode.*2/);
  });

  it("should reject flow where startNode does not match StartNode in nodes", () => {
    const start1 = createStartNode({ name: "start-opts" });
    const start2 = createStartNode({ name: "start-nodes" });
    const end = createEndNode({ name: "end" });
    const edge = createControlFlowEdge({ name: "e1", fromNode: start2, toNode: end });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start1,
        nodes: [start2, end],
        controlFlowConnections: [edge],
      }),
    ).toThrow(/start_node.*not matching/);
  });

  it("should reject flow where StartNode has no outgoing edge", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, end],
        controlFlowConnections: [],
      }),
    ).toThrow(/exactly one outgoing control flow edge.*found 0/);
  });

  it("should reject flow with incoming edge to StartNode", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const e1 = createControlFlowEdge({ name: "e1", fromNode: start, toNode: end });
    const e2 = createControlFlowEdge({ name: "e2", fromNode: end, toNode: start });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, end],
        controlFlowConnections: [e1, e2],
      }),
    ).toThrow(/Transitions to StartNode is not accepted/);
  });

  it("should reject flow with no EndNode", () => {
    const start = createStartNode({ name: "start" });
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Hello",
    });
    const edge = createControlFlowEdge({ name: "e1", fromNode: start, toNode: llm });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, llm],
        controlFlowConnections: [edge],
      }),
    ).toThrow(/at least one EndNode/);
  });

  it("should reject EndNode without incoming control flow edge", () => {
    const start = createStartNode({ name: "start" });
    const end1 = createEndNode({ name: "end1" });
    const end2 = createEndNode({ name: "end2" });
    const edge = createControlFlowEdge({ name: "e1", fromNode: start, toNode: end1 });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, end1, end2],
        controlFlowConnections: [edge],
      }),
    ).toThrow(/end node without any incoming.*end2/);
  });

  it("should reject outgoing control flow edge from EndNode", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Hello",
    });
    const e1 = createControlFlowEdge({ name: "e1", fromNode: start, toNode: end });
    const e2 = createControlFlowEdge({ name: "e2", fromNode: end, toNode: llm });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, end, llm],
        controlFlowConnections: [e1, e2],
      }),
    ).toThrow(/Transitions from EndNode is not accepted/);
  });

  it("should reject control edge referencing node not in nodes", () => {
    const start = createStartNode({ name: "start" });
    const end = createEndNode({ name: "end" });
    const llm = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Hi",
    });
    const phantom = createLlmNode({
      name: "phantom",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Hi",
    });
    const e1 = createControlFlowEdge({ name: "e1", fromNode: start, toNode: llm });
    const e2 = createControlFlowEdge({ name: "e2", fromNode: llm, toNode: end });
    const e3 = createControlFlowEdge({ name: "e3", fromNode: llm, toNode: phantom });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, llm, end],
        controlFlowConnections: [e1, e2, e3],
      }),
    ).toThrow(/does not contain the destination node 'phantom'/);
  });

  it("should reject data edge referencing node not in nodes", () => {
    const start = createStartNode({
      name: "start",
      outputs: [stringProperty({ title: "x" })],
    });
    const end = createEndNode({
      name: "end",
      inputs: [stringProperty({ title: "x" })],
    });
    const phantom = createLlmNode({
      name: "phantom",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Hi",
    });
    const e1 = createControlFlowEdge({ name: "e1", fromNode: start, toNode: end });
    const dataEdge = createDataFlowEdge({
      name: "d1",
      sourceNode: phantom,
      sourceOutput: "generated_text",
      destinationNode: end,
      destinationInput: "x",
    });
    expect(() =>
      createFlow({
        name: "flow",
        startNode: start,
        nodes: [start, end],
        controlFlowConnections: [e1],
        dataFlowConnections: [dataEdge],
      }),
    ).toThrow(/does not contain the source node 'phantom'/);
  });
});
