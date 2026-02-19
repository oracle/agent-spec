import { describe, it, expect } from "vitest";
import {
  createMapNode,
  createFlow,
  createStartNode,
  createEndNode,
  createControlFlowEdge,
  stringProperty,
  integerProperty,
  ReductionMethod,
} from "../../src/index.js";

/** Create a minimal valid Flow with the given inputs and outputs. */
function makeTestFlow(opts?: {
  inputs?: ReturnType<typeof stringProperty>[];
  outputs?: ReturnType<typeof stringProperty>[];
}) {
  const start = createStartNode({
    name: "start",
    inputs: opts?.inputs,
  });
  const end = createEndNode({
    name: "end",
    outputs: opts?.outputs,
  });
  const edge = createControlFlowEdge({
    name: "edge",
    fromNode: start,
    toNode: end,
  });
  return createFlow({
    name: "test-flow",
    startNode: start,
    nodes: [start, end],
    controlFlowConnections: [edge],
  });
}

describe("MapNode with non-APPEND reducers", () => {
  it("should use SUM reducer and produce non-array output schema", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "item" })],
      outputs: [integerProperty({ title: "score" })],
    });
    const node = createMapNode({
      name: "map-sum",
      subflow,
      reducers: { score: ReductionMethod.SUM },
    });
    expect(node.reducers).toEqual({ score: "sum" });
    // SUM reducer should produce a collected_ output without array wrapping
    const output = node.outputs!.find(
      (o) => o.title === "collected_score",
    );
    expect(output).toBeDefined();
    // SUM outputs should not have type "array"
    expect(output!.jsonSchema["type"]).not.toBe("array");
  });

  it("should use AVERAGE reducer", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "item" })],
      outputs: [integerProperty({ title: "val" })],
    });
    const node = createMapNode({
      name: "map-avg",
      subflow,
      reducers: { val: ReductionMethod.AVERAGE },
    });
    const output = node.outputs!.find(
      (o) => o.title === "collected_val",
    );
    expect(output).toBeDefined();
  });

  it("should use MAX reducer", () => {
    const subflow = makeTestFlow({
      outputs: [integerProperty({ title: "val" })],
    });
    const node = createMapNode({
      name: "map-max",
      subflow,
      reducers: { val: ReductionMethod.MAX },
    });
    const output = node.outputs!.find(
      (o) => o.title === "collected_val",
    );
    expect(output).toBeDefined();
  });

  it("should use MIN reducer", () => {
    const subflow = makeTestFlow({
      outputs: [integerProperty({ title: "val" })],
    });
    const node = createMapNode({
      name: "map-min",
      subflow,
      reducers: { val: ReductionMethod.MIN },
    });
    const output = node.outputs!.find(
      (o) => o.title === "collected_val",
    );
    expect(output).toBeDefined();
  });

  it("should skip outputs that don't have a matching reducer", () => {
    const subflow = makeTestFlow({
      outputs: [
        integerProperty({ title: "val1" }),
        integerProperty({ title: "val2" }),
      ],
    });
    // Only reduce val1, val2 should be skipped
    const node = createMapNode({
      name: "map-partial",
      subflow,
      reducers: { val1: ReductionMethod.APPEND },
    });
    expect(node.outputs!.length).toBe(1);
    expect(node.outputs![0]!.title).toBe("collected_val1");
  });

  it("should handle subflow with no outputs", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "item" })],
    });
    const node = createMapNode({
      name: "map-no-out",
      subflow,
    });
    expect(node.outputs).toEqual([]);
    expect(node.reducers).toEqual({});
  });

  it("should handle subflow with no inputs", () => {
    const subflow = makeTestFlow({
      outputs: [stringProperty({ title: "out" })],
    });
    const node = createMapNode({
      name: "map-no-in",
      subflow,
    });
    expect(node.inputs).toEqual([]);
  });
});

describe("MapNode input inference", () => {
  it("should prefix inputs with 'iterated_'", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "item" })],
      outputs: [stringProperty({ title: "result" })],
    });
    const node = createMapNode({ name: "map-node", subflow });
    expect(node.inputs!.length).toBe(1);
    expect(node.inputs![0]!.title).toBe("iterated_item");
  });

  it("should default reducers to APPEND for all outputs", () => {
    const subflow = makeTestFlow({
      outputs: [
        stringProperty({ title: "out1" }),
        integerProperty({ title: "out2" }),
      ],
    });
    const node = createMapNode({ name: "map-node", subflow });
    expect(node.reducers).toEqual({
      out1: "append",
      out2: "append",
    });
  });
});
