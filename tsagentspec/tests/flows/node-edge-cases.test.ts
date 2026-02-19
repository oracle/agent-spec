import { describe, it, expect } from "vitest";
import {
  createAgentNode,
  createFlowNode,
  createInputMessageNode,
  createParallelFlowNode,
  createCatchExceptionNode,
  createAgent,
  createOpenAiCompatibleConfig,
  createFlow,
  createStartNode,
  createEndNode,
  createControlFlowEdge,
  stringProperty,
  integerProperty,
  DEFAULT_INPUT_MESSAGE_OUTPUT,
  CAUGHT_EXCEPTION_BRANCH,
  DEFAULT_EXCEPTION_INFO_VALUE,
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
    name: "test-agent",
    llmConfig: makeLlmConfig(),
    systemPrompt: "Hello",
    inputs: [stringProperty({ title: "query" })],
    outputs: [stringProperty({ title: "answer" })],
  });
}

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

/** Create a minimal Flow whose EndNodes have the given branch names. */
function makeTestFlowWithBranches(branchNames: string[]) {
  const start = createStartNode({ name: "start" });
  const endNodes = branchNames.map((bn, i) =>
    createEndNode({ name: `end-${i}`, branchName: bn }),
  );
  const edges = endNodes.map((end, i) =>
    createControlFlowEdge({
      name: `edge-${i}`,
      fromNode: start,
      toNode: end,
    }),
  );
  return createFlow({
    name: "test-flow",
    startNode: start,
    nodes: [start, ...endNodes],
    controlFlowConnections: edges,
  });
}

describe("AgentNode input/output inference", () => {
  it("should infer inputs and outputs from agent when not provided", () => {
    const agent = makeAgent();
    const node = createAgentNode({ name: "agent-node", agent });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("query");
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("answer");
  });

  it("should use provided inputs/outputs over agent's", () => {
    const agent = makeAgent();
    const customInput = integerProperty({ title: "custom_in" });
    const customOutput = integerProperty({ title: "custom_out" });
    const node = createAgentNode({
      name: "agent-node",
      agent,
      inputs: [customInput],
      outputs: [customOutput],
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("custom_in");
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("custom_out");
  });

  it("should default to empty inputs/outputs when agent has none", () => {
    const agent = createAgent({
      name: "no-io-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const node = createAgentNode({ name: "agent-node", agent });
    // Agent with no explicit inputs will have template-derived inputs (empty here)
    expect(node.inputs).toBeDefined();
    expect(node.outputs).toBeDefined();
  });
});

describe("FlowNode input/output inference", () => {
  it("should infer inputs/outputs from subflow", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "flow_in" })],
      outputs: [stringProperty({ title: "flow_out" })],
    });
    const node = createFlowNode({ name: "flow-node", subflow });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("flow_in");
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("flow_out");
  });

  it("should use provided inputs/outputs over subflow's", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "flow_in" })],
      outputs: [stringProperty({ title: "flow_out" })],
    });
    const customInput = integerProperty({ title: "custom" });
    const node = createFlowNode({
      name: "flow-node",
      subflow,
      inputs: [customInput],
      outputs: [],
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("custom");
    expect(node.outputs).toHaveLength(0);
  });

  it("should default to empty when subflow has no inputs/outputs", () => {
    const subflow = makeTestFlow();
    const node = createFlowNode({ name: "flow-node", subflow });
    expect(node.inputs).toEqual([]);
    expect(node.outputs).toEqual([]);
  });

  it("should extract branches from EndNodes in subflow", () => {
    const subflow = makeTestFlowWithBranches(["success", "failure"]);
    const node = createFlowNode({ name: "flow-node", subflow });
    expect(node.branches).toContain("success");
    expect(node.branches).toContain("failure");
  });
});

describe("InputMessageNode", () => {
  it("should infer inputs from message placeholders", () => {
    const node = createInputMessageNode({
      name: "input-node",
      message: "Hello {{user_name}}, please provide {{topic}}",
    });
    expect(node.inputs!.length).toBe(2);
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("user_name");
    expect(titles).toContain("topic");
  });

  it("should use provided inputs over inferred ones", () => {
    const node = createInputMessageNode({
      name: "input-node",
      message: "Hello {{user_name}}",
      inputs: [integerProperty({ title: "custom_input" })],
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("custom_input");
  });

  it("should default to empty inputs when no message is given", () => {
    const node = createInputMessageNode({ name: "input-node" });
    expect(node.inputs).toEqual([]);
  });

  it("should default outputs to user_input", () => {
    const node = createInputMessageNode({ name: "input-node" });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe(DEFAULT_INPUT_MESSAGE_OUTPUT);
  });

  it("should use provided outputs", () => {
    const node = createInputMessageNode({
      name: "input-node",
      outputs: [stringProperty({ title: "custom_output" })],
    });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("custom_output");
  });
});

describe("ParallelFlowNode", () => {
  it("should aggregate inputs from multiple subflows", () => {
    const subflow1 = makeTestFlow({
      inputs: [stringProperty({ title: "input_a" })],
      outputs: [stringProperty({ title: "output_a" })],
    });
    const subflow2 = makeTestFlow({
      inputs: [stringProperty({ title: "input_b" })],
      outputs: [stringProperty({ title: "output_b" })],
    });
    const node = createParallelFlowNode({
      name: "parallel-node",
      subflows: [subflow1, subflow2],
    });
    expect(node.inputs!.length).toBe(2);
    expect(node.outputs!.length).toBe(2);
  });

  it("should use provided inputs/outputs over inferred ones", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "sub_in" })],
      outputs: [stringProperty({ title: "sub_out" })],
    });
    const node = createParallelFlowNode({
      name: "parallel-node",
      subflows: [subflow],
      inputs: [integerProperty({ title: "custom_in" })],
      outputs: [integerProperty({ title: "custom_out" })],
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("custom_in");
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("custom_out");
  });

  it("should handle no subflows", () => {
    const node = createParallelFlowNode({ name: "parallel-node" });
    expect(node.subflows).toEqual([]);
    expect(node.inputs).toEqual([]);
    expect(node.outputs).toEqual([]);
  });
});

describe("CatchExceptionNode", () => {
  it("should infer inputs from subflow", () => {
    const subflow = makeTestFlow({
      inputs: [stringProperty({ title: "sub_in" })],
      outputs: [stringProperty({ title: "sub_out" })],
    });
    const node = createCatchExceptionNode({
      name: "catch-node",
      subflow,
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("sub_in");
  });

  it("should append caught_exception_info to subflow outputs", () => {
    const subflow = makeTestFlow({
      outputs: [stringProperty({ title: "sub_out" })],
    });
    const node = createCatchExceptionNode({
      name: "catch-node",
      subflow,
    });
    expect(node.outputs!.length).toBe(2);
    expect(node.outputs![0]!.title).toBe("sub_out");
    expect(node.outputs![1]!.title).toBe(DEFAULT_EXCEPTION_INFO_VALUE);
  });

  it("should use provided outputs over inferred ones", () => {
    const subflow = makeTestFlow({
      outputs: [stringProperty({ title: "sub_out" })],
    });
    const node = createCatchExceptionNode({
      name: "catch-node",
      subflow,
      outputs: [integerProperty({ title: "custom_out" })],
    });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("custom_out");
  });

  it("should include caught_exception_branch in branches", () => {
    const subflow = makeTestFlow();
    const node = createCatchExceptionNode({
      name: "catch-node",
      subflow,
    });
    expect(node.branches).toContain(CAUGHT_EXCEPTION_BRANCH);
  });

  it("should include EndNode branches from subflow", () => {
    const subflow = makeTestFlowWithBranches(["done"]);
    const node = createCatchExceptionNode({
      name: "catch-node",
      subflow,
    });
    expect(node.branches).toContain(CAUGHT_EXCEPTION_BRANCH);
    expect(node.branches).toContain("done");
  });
});
