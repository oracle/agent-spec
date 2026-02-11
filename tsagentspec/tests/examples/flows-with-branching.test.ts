/**
 * Flows with Branching examples — mirrors the Python SDK flow-with-branching tests.
 *
 * Covers BranchingNode in flows, the FlowBuilder.addConditional helper,
 * data flow edges across branches, and multiple EndNode branch names.
 */
import { describe, it, expect } from "vitest";
import {
  createStartNode,
  createEndNode,
  createLlmNode,
  createAgentNode,
  createBranchingNode,
  createControlFlowEdge,
  createDataFlowEdge,
  createFlow,
  createAgent,
  createVllmConfig,
  FlowBuilder,
  stringProperty,
  AgentSpecSerializer,
  AgentSpecDeserializer,
  DEFAULT_BRANCH,
  DEFAULT_INPUT,
} from "../../src/index.js";

/* ---------- helpers ---------- */

function makeLlmConfig() {
  return createVllmConfig({
    name: "agi1",
    url: "http://some.where",
    modelId: "agi_model1",
  });
}

/* ---------- manually-constructed branching flow ---------- */

describe("Flow with BranchingNode (manual construction)", () => {
  it("should build a flow with branching and multiple end nodes", () => {
    const input1 = stringProperty({ title: "Input_1", default: "yes" });
    const input2 = stringProperty({ title: "Input_2", default: "no" });

    const startNode = createStartNode({
      name: "Node 1",
      inputs: [input1, input2],
    });

    const branchingNode1 = createBranchingNode({
      name: "Branching Node",
      mapping: { yes: "Yes", no: "No", maybe: "Maybe" },
      inputs: [input1],
    });

    const branchingNode2 = createBranchingNode({
      name: "Branching Node 2",
      mapping: { yes: "Yes", no: "No" },
      inputs: [input2],
    });

    const endNode1 = createEndNode({
      name: "End Node 1",
      outputs: [input1],
    });
    const endNode2 = createEndNode({
      name: "End Node 2",
      outputs: [input2],
    });
    const endNode3 = createEndNode({
      name: "End Node 3",
      outputs: [],
    });

    // Control flow edges
    const ctrlEdge1 = createControlFlowEdge({
      name: "ctrl_1",
      fromNode: startNode,
      toNode: branchingNode1,
    });
    const ctrlEdge2 = createControlFlowEdge({
      name: "ctrl_2",
      fromNode: branchingNode1,
      fromBranch: "Yes",
      toNode: endNode1,
    });
    const ctrlEdge3 = createControlFlowEdge({
      name: "ctrl_3",
      fromNode: branchingNode1,
      fromBranch: "No",
      toNode: endNode3,
    });
    const ctrlEdge4 = createControlFlowEdge({
      name: "ctrl_4",
      fromNode: branchingNode1,
      fromBranch: "Maybe",
      toNode: branchingNode2,
    });
    const ctrlEdge5 = createControlFlowEdge({
      name: "ctrl_5",
      fromNode: branchingNode2,
      fromBranch: "Yes",
      toNode: endNode2,
    });
    const ctrlEdge6 = createControlFlowEdge({
      name: "ctrl_6",
      fromNode: branchingNode2,
      fromBranch: "No",
      toNode: endNode3,
    });

    // Data flow edges
    const dataEdge1 = createDataFlowEdge({
      name: "data_1",
      sourceNode: startNode,
      sourceOutput: "Input_1",
      destinationNode: branchingNode1,
      destinationInput: "Input_1",
    });
    const dataEdge2 = createDataFlowEdge({
      name: "data_2",
      sourceNode: startNode,
      sourceOutput: "Input_2",
      destinationNode: branchingNode2,
      destinationInput: "Input_2",
    });
    const dataEdge3 = createDataFlowEdge({
      name: "data_3",
      sourceNode: startNode,
      sourceOutput: "Input_1",
      destinationNode: endNode1,
      destinationInput: "Input_1",
    });
    const dataEdge4 = createDataFlowEdge({
      name: "data_4",
      sourceNode: startNode,
      sourceOutput: "Input_2",
      destinationNode: endNode2,
      destinationInput: "Input_2",
    });

    const flow = createFlow({
      name: "Example branching test flow",
      startNode: startNode,
      nodes: [
        startNode,
        branchingNode1,
        branchingNode2,
        endNode1,
        endNode2,
        endNode3,
      ],
      controlFlowConnections: [
        ctrlEdge1,
        ctrlEdge2,
        ctrlEdge3,
        ctrlEdge4,
        ctrlEdge5,
        ctrlEdge6,
      ],
      dataFlowConnections: [dataEdge1, dataEdge2, dataEdge3, dataEdge4],
      inputs: [input1, input2],
      outputs: [input1, input2],
    });

    expect(flow.componentType).toBe("Flow");
    expect(flow.nodes).toHaveLength(6);
    expect(flow.controlFlowConnections).toHaveLength(6);
    expect(flow.dataFlowConnections).toHaveLength(4);
    expect(flow.inputs).toHaveLength(2);
    expect(flow.outputs).toHaveLength(2);
  });

  it("should serialize and deserialize a branching flow", () => {
    const input1 = stringProperty({ title: "Input_1", default: "yes" });

    const startNode = createStartNode({
      name: "start",
      inputs: [input1],
    });
    const branchingNode = createBranchingNode({
      name: "branch",
      mapping: { a: "branch_a", b: "branch_b" },
    });
    const endA = createEndNode({ name: "end-a" });
    const endB = createEndNode({ name: "end-b" });
    const endDefault = createEndNode({ name: "end-default" });

    const flow = createFlow({
      name: "branching-roundtrip",
      startNode,
      nodes: [startNode, branchingNode, endA, endB, endDefault],
      controlFlowConnections: [
        createControlFlowEdge({
          name: "e1",
          fromNode: startNode,
          toNode: branchingNode,
        }),
        createControlFlowEdge({
          name: "e2",
          fromNode: branchingNode,
          fromBranch: "branch_a",
          toNode: endA,
        }),
        createControlFlowEdge({
          name: "e3",
          fromNode: branchingNode,
          fromBranch: "branch_b",
          toNode: endB,
        }),
        createControlFlowEdge({
          name: "e4",
          fromNode: branchingNode,
          fromBranch: DEFAULT_BRANCH,
          toNode: endDefault,
        }),
      ],
      dataFlowConnections: [
        createDataFlowEdge({
          name: "d1",
          sourceNode: startNode,
          sourceOutput: "Input_1",
          destinationNode: branchingNode,
          destinationInput: DEFAULT_INPUT,
        }),
      ],
    });

    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();

    const yaml = serializer.toYaml(flow);
    expect(yaml.length).toBeGreaterThan(0);

    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("Flow");
    expect(restored["name"]).toBe("branching-roundtrip");
    expect((restored["nodes"] as unknown[]).length).toBe(5);
    expect(
      (restored["controlFlowConnections"] as unknown[]).length,
    ).toBe(4);
  });
});

/* ---------- FlowBuilder.addConditional ---------- */

describe("FlowBuilder conditional branching", () => {
  it("should build a flow with addConditional", () => {
    const llmClassifier = createLlmNode({
      name: "classifier",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Classify the following: {{text}}",
    });

    const llmPositive = createLlmNode({
      name: "positive-handler",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Handle positive sentiment",
    });

    const llmNegative = createLlmNode({
      name: "negative-handler",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Handle negative sentiment",
    });

    const llmNeutral = createLlmNode({
      name: "neutral-handler",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Handle neutral sentiment",
    });

    const builder = new FlowBuilder();
    builder.addNode(llmClassifier);
    builder.addNode(llmPositive);
    builder.addNode(llmNegative);
    builder.addNode(llmNeutral);

    builder.setEntryPoint("classifier", [stringProperty({ title: "text" })]);

    builder.addConditional(
      "classifier",
      "generated_text",
      { positive: "positive-handler", negative: "negative-handler" },
      "neutral-handler",
    );

    builder.setFinishPoints(["positive-handler", "negative-handler", "neutral-handler"]);

    const flow = builder.build("sentiment-flow");
    expect(flow.componentType).toBe("Flow");
    expect(flow.name).toBe("sentiment-flow");

    // Should have: start, classifier, branching, positive, negative, neutral, 3 end nodes
    expect(flow.nodes.length).toBeGreaterThanOrEqual(6);
  });

  it("should throw if conditional destination uses reserved default branch", () => {
    const llm1 = createLlmNode({
      name: "llm1",
      llmConfig: makeLlmConfig(),
      promptTemplate: "A",
    });
    const llm2 = createLlmNode({
      name: "llm2",
      llmConfig: makeLlmConfig(),
      promptTemplate: "B",
    });

    const builder = new FlowBuilder();
    builder.addNode(llm1);
    builder.addNode(llm2);

    expect(() =>
      builder.addConditional(
        "llm1",
        "generated_text",
        { val: DEFAULT_BRANCH }, // "default" is reserved
        "llm2",
      ),
    ).toThrow("reserved branch label");
  });

  it("should create data flow edge for branching input", () => {
    const llm1 = createLlmNode({
      name: "llm1",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Classify {{text}}",
    });
    const llm2 = createLlmNode({
      name: "handler-a",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Handle A",
    });
    const llm3 = createLlmNode({
      name: "handler-b",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Handle B",
    });

    const builder = new FlowBuilder();
    builder.addNode(llm1);
    builder.addNode(llm2);
    builder.addNode(llm3);

    builder.setEntryPoint("llm1");
    builder.addConditional(
      "llm1",
      "generated_text",
      { a: "handler-a" },
      "handler-b",
    );
    builder.setFinishPoints(["handler-a", "handler-b"]);
    const flow = builder.build();

    // Should have at least one data flow edge for the branching input
    expect(flow.dataFlowConnections).toBeDefined();
    expect(flow.dataFlowConnections!.length).toBeGreaterThanOrEqual(1);

    const branchingEdge = flow.dataFlowConnections!.find(
      (e: Record<string, unknown>) =>
        e["destinationInput"] === DEFAULT_INPUT,
    );
    expect(branchingEdge).toBeDefined();
  });
});

/* ---------- Flow output inference with branching ---------- */

describe("Flow output inference with branching", () => {
  it("should infer outputs as intersection of all EndNode outputs", () => {
    const startNode = createStartNode({ name: "start" });
    const branchingNode = createBranchingNode({
      name: "branching",
      mapping: { "1": "branch_1", "2": "branch_2" },
    });

    const endNode1 = createEndNode({
      name: "end_1",
      outputs: [
        stringProperty({ title: "output_a" }),
        stringProperty({ title: "output_c" }),
      ],
    });
    const endNode2 = createEndNode({
      name: "end_2",
      outputs: [
        stringProperty({ title: "output_b" }),
        stringProperty({ title: "output_c" }),
      ],
    });
    const endNode3 = createEndNode({
      name: "end_3",
      outputs: [stringProperty({ title: "output_c" })],
    });

    const flow = createFlow({
      name: "inference-test",
      startNode,
      nodes: [startNode, branchingNode, endNode1, endNode2, endNode3],
      controlFlowConnections: [
        createControlFlowEdge({
          name: "e1",
          fromNode: startNode,
          toNode: branchingNode,
        }),
        createControlFlowEdge({
          name: "e2",
          fromNode: branchingNode,
          fromBranch: "branch_1",
          toNode: endNode1,
        }),
        createControlFlowEdge({
          name: "e3",
          fromNode: branchingNode,
          fromBranch: "branch_2",
          toNode: endNode2,
        }),
        createControlFlowEdge({
          name: "e4",
          fromNode: branchingNode,
          fromBranch: DEFAULT_BRANCH,
          toNode: endNode3,
        }),
      ],
    });

    // Intersection of all EndNode outputs: only output_c is in all three
    expect(flow.outputs).toBeDefined();
    expect(flow.outputs).toHaveLength(1);
    expect(flow.outputs![0]!.title).toBe("output_c");
  });

  it("should have empty inferred outputs when EndNodes share nothing", () => {
    const startNode = createStartNode({ name: "start" });
    const endA = createEndNode({
      name: "end-a",
      outputs: [stringProperty({ title: "x" })],
    });
    const endB = createEndNode({
      name: "end-b",
      outputs: [stringProperty({ title: "y" })],
    });

    const flow = createFlow({
      name: "no-common-outputs",
      startNode,
      nodes: [startNode, endA, endB],
      controlFlowConnections: [
        createControlFlowEdge({ name: "e1", fromNode: startNode, toNode: endA }),
        createControlFlowEdge({ name: "e2", fromNode: startNode, toNode: endB }),
      ],
    });

    expect(flow.outputs).toEqual([]);
  });
});

/* ---------- Agent executing in a flow with branching ---------- */

describe("Agent in flow with data flow edges", () => {
  it("should build a flow with agent node, LLM nodes, and data flow edges", () => {
    const llmConfig = makeLlmConfig();
    const agent = createAgent({
      name: "Great agent",
      llmConfig,
      systemPrompt: "Always be polite",
    });

    const startNode = createStartNode({ name: "start" });
    const agentNode = createAgentNode({ name: "agent-exec", agent });
    const llm1 = createLlmNode({
      name: "prompt-1",
      llmConfig,
      promptTemplate: "Do {{x}}:",
    });
    const llm2 = createLlmNode({
      name: "prompt-2",
      llmConfig,
      promptTemplate: "What do you think of the answer {{y}}?",
    });
    const endNode = createEndNode({ name: "end" });

    const flow = createFlow({
      name: "agent-flow",
      startNode,
      nodes: [startNode, agentNode, llm1, llm2, endNode],
      controlFlowConnections: [
        createControlFlowEdge({
          name: "s-a",
          fromNode: startNode,
          toNode: agentNode,
        }),
        createControlFlowEdge({
          name: "a-l1",
          fromNode: agentNode,
          toNode: llm1,
        }),
        createControlFlowEdge({
          name: "l1-l2",
          fromNode: llm1,
          toNode: llm2,
        }),
        createControlFlowEdge({
          name: "l2-e",
          fromNode: llm2,
          toNode: endNode,
        }),
      ],
      dataFlowConnections: [
        createDataFlowEdge({
          name: "prompt-output-to-y",
          sourceNode: llm1,
          sourceOutput: "generated_text",
          destinationNode: llm2,
          destinationInput: "y",
        }),
      ],
    });

    expect(flow.componentType).toBe("Flow");
    expect(flow.nodes).toHaveLength(5);
    expect(flow.controlFlowConnections).toHaveLength(4);
    expect(flow.dataFlowConnections).toHaveLength(1);

    // Round trip
    const serializer = new AgentSpecSerializer();
    const deserializer = new AgentSpecDeserializer();
    const yaml = serializer.toYaml(flow);
    const restored = deserializer.fromYaml(yaml) as Record<string, unknown>;
    expect(restored["componentType"]).toBe("Flow");
    expect((restored["nodes"] as unknown[]).length).toBe(5);
    expect(
      (restored["dataFlowConnections"] as unknown[]).length,
    ).toBe(1);
  });
});
