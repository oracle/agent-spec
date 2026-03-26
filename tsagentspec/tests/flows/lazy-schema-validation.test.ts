import { describe, it, expect } from "vitest";
import {
  FlowSchema,
  FlowNodeSchema,
  ControlFlowEdgeSchema,
  createStartNode,
  createEndNode,
  createControlFlowEdge,
  createFlow,
} from "../../src/index.js";

/** Build a minimal valid flow for use in subflow tests */
function makeSimpleFlow() {
  const start = createStartNode({ name: "start" });
  const end = createEndNode({ name: "end" });
  const edge = createControlFlowEdge({
    name: "e1",
    fromNode: start,
    toNode: end,
  });
  return createFlow({
    name: "subflow",
    startNode: start,
    nodes: [start, end],
    controlFlowConnections: [edge],
  });
}

describe("Lazy schema validation", () => {
  describe("FlowSchema rejects invalid nodes", () => {
    it("should reject a bogus object in the nodes array", () => {
      const start = createStartNode({ name: "start" });
      const end = createEndNode({ name: "end" });
      const edge = createControlFlowEdge({
        name: "e1",
        fromNode: start,
        toNode: end,
      });

      const result = FlowSchema.safeParse({
        name: "flow",
        componentType: "Flow",
        startNode: start,
        nodes: [start, { bogus: true }],
        controlFlowConnections: [edge],
      });

      expect(result.success).toBe(false);
    });

    it("should reject an invalid startNode", () => {
      const start = createStartNode({ name: "start" });
      const end = createEndNode({ name: "end" });
      const edge = createControlFlowEdge({
        name: "e1",
        fromNode: start,
        toNode: end,
      });

      const result = FlowSchema.safeParse({
        name: "flow",
        componentType: "Flow",
        startNode: { not: "a node" },
        nodes: [start, end],
        controlFlowConnections: [edge],
      });

      expect(result.success).toBe(false);
    });

    it("should accept valid nodes", () => {
      const start = createStartNode({ name: "start" });
      const end = createEndNode({ name: "end" });
      const edge = createControlFlowEdge({
        name: "e1",
        fromNode: start,
        toNode: end,
      });

      const result = FlowSchema.safeParse({
        name: "flow",
        componentType: "Flow",
        startNode: start,
        nodes: [start, end],
        controlFlowConnections: [edge],
      });

      expect(result.success).toBe(true);
    });
  });

  describe("FlowNodeSchema rejects invalid subflow", () => {
    it("should reject a bogus subflow", () => {
      const result = FlowNodeSchema.safeParse({
        name: "flow-node",
        componentType: "FlowNode",
        subflow: { not: "a flow" },
      });

      expect(result.success).toBe(false);
    });

    it("should accept a valid subflow", () => {
      const flow = makeSimpleFlow();

      const result = FlowNodeSchema.safeParse({
        name: "flow-node",
        componentType: "FlowNode",
        subflow: flow,
      });

      expect(result.success).toBe(true);
    });
  });

  describe("ControlFlowEdgeSchema rejects invalid node refs", () => {
    it("should reject a bogus fromNode", () => {
      const end = createEndNode({ name: "end" });

      const result = ControlFlowEdgeSchema.safeParse({
        name: "edge",
        componentType: "ControlFlowEdge",
        fromNode: { bogus: true },
        toNode: end,
      });

      expect(result.success).toBe(false);
    });

    it("should reject a bogus toNode", () => {
      const start = createStartNode({ name: "start" });

      const result = ControlFlowEdgeSchema.safeParse({
        name: "edge",
        componentType: "ControlFlowEdge",
        fromNode: start,
        toNode: { bogus: true },
      });

      expect(result.success).toBe(false);
    });
  });
});
