import { describe, expect, it } from "vitest";
import {
  createBranchingNode,
  createControlFlowEdge,
  createEndNode,
  createFlow,
  createLlmNode,
  createOpenAiConfig,
  createStartNode,
} from "../../../src/index.js";
import {
  planLinearMastraFlow,
  UnsupportedMastraFlowNodeError,
  UnsupportedMastraFlowShapeError,
} from "../../../src/adapters/mastra/index.js";

const llmConfig = createOpenAiConfig({
  name: "llm",
  modelId: "gpt-4o-mini",
});

describe("Mastra linear flow planner", () => {
  it("orders a simple linear flow", () => {
    const start = createStartNode({ name: "start" });
    const llm = createLlmNode({
      name: "draft",
      llmConfig,
      promptTemplate: "Draft a reply.",
    });
    const end = createEndNode({ name: "end" });
    const flow = createFlow({
      name: "linear",
      startNode: start,
      nodes: [start, llm, end],
      controlFlowConnections: [
        createControlFlowEdge({ name: "start_to_draft", fromNode: start, toNode: llm }),
        createControlFlowEdge({ name: "draft_to_end", fromNode: llm, toNode: end }),
      ],
    });

    const plan = planLinearMastraFlow(flow);

    expect(plan.nodeOrder.map((node) => node.name)).toEqual([
      "start",
      "draft",
      "end",
    ]);
    expect(plan.executableNodes.map((node) => node.name)).toEqual(["draft"]);
  });

  it("rejects unsupported node types", () => {
    const start = createStartNode({ name: "start" });
    const branch = createBranchingNode({
      name: "branch",
      mapping: { yes: "yes_end" },
    });
    const end = createEndNode({ name: "end" });
    const flow = createFlow({
      name: "branching",
      startNode: start,
      nodes: [start, branch, end],
      controlFlowConnections: [
        createControlFlowEdge({ name: "start_to_branch", fromNode: start, toNode: branch }),
        createControlFlowEdge({ name: "branch_to_end", fromNode: branch, toNode: end }),
      ],
    });

    expect(() => planLinearMastraFlow(flow)).toThrow(
      UnsupportedMastraFlowNodeError,
    );
  });

  it("rejects control-flow splits in supported node types", () => {
    const start = createStartNode({ name: "start" });
    const llm = createLlmNode({
      name: "router",
      llmConfig,
      promptTemplate: "Route.",
    });
    const endA = createEndNode({ name: "end_a" });
    const endB = createEndNode({ name: "end_b" });
    const flow = createFlow({
      name: "split",
      startNode: start,
      nodes: [start, llm, endA, endB],
      controlFlowConnections: [
        createControlFlowEdge({ name: "start_to_router", fromNode: start, toNode: llm }),
        createControlFlowEdge({ name: "router_to_a", fromNode: llm, toNode: endA }),
        createControlFlowEdge({ name: "router_to_b", fromNode: llm, toNode: endB }),
      ],
    });

    expect(() => planLinearMastraFlow(flow)).toThrow(
      UnsupportedMastraFlowShapeError,
    );
  });
});
