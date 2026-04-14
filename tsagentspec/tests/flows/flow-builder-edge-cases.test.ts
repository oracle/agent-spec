import { describe, it, expect } from "vitest";
import {
  FlowBuilder,
  createLlmNode,
  createToolNode,
  createStartNode,
  createEndNode,
  createServerTool,
  createOpenAiCompatibleConfig,
  createDataFlowEdge,
  stringProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeTool() {
  return createServerTool({
    name: "test-tool",
    inputs: [stringProperty({ title: "query" })],
    outputs: [stringProperty({ title: "result" })],
  });
}

function makeLlmNode(name: string) {
  return createLlmNode({
    name,
    llmConfig: makeLlmConfig(),
    promptTemplate: "Hello {{input}}",
  });
}

describe("FlowBuilder edge cases", () => {
  it("should throw when addEdge receives list for fromBranch but single sourceNode", () => {
    const llmNode = makeLlmNode("llm-node");
    const toolNode = createToolNode({ name: "tool-node", tool: makeTool() });
    const builder = new FlowBuilder();
    builder.addNode(llmNode).addNode(toolNode);

    expect(() =>
      builder.addEdge(llmNode, toolNode, ["branch1", "branch2"]),
    ).toThrow(
      "A list was given for `fromBranch` but `sourceNode` is not a list of nodes",
    );
  });

  it("should throw when sourceNode and fromBranch lists have different lengths", () => {
    const llm1 = makeLlmNode("llm-1");
    const llm2 = makeLlmNode("llm-2");
    const toolNode = createToolNode({ name: "tool-node", tool: makeTool() });
    const builder = new FlowBuilder();
    builder.addNode(llm1).addNode(llm2).addNode(toolNode);

    expect(() =>
      builder.addEdge([llm1, llm2], toolNode, ["branch1"]),
    ).toThrow("sourceNode and fromBranch must have the same length");
  });

  it("should throw when setting entry point twice", () => {
    const llmNode = makeLlmNode("llm-node");
    const builder = new FlowBuilder();
    builder.addNode(llmNode);
    builder.setEntryPoint(llmNode);

    expect(() => builder.setEntryPoint(llmNode)).toThrow(
      "Entry point already set",
    );
  });

  it("should throw when building without a start node", () => {
    const llmNode = makeLlmNode("llm-node");
    const endNode = createEndNode({ name: "end" });
    const builder = new FlowBuilder();
    builder.addNode(llmNode).addNode(endNode);

    expect(() => builder.build()).toThrow("Missing start node");
  });

  it("should throw when building without an end node", () => {
    const llmNode = makeLlmNode("llm-node");
    const builder = new FlowBuilder();
    builder.addNode(llmNode);
    builder.setEntryPoint(llmNode);

    expect(() => builder.build()).toThrow("Missing finish node");
  });

  it("should throw when building with multiple start nodes and no setEntryPoint", () => {
    const start1 = createStartNode({ name: "start1" });
    const start2 = createStartNode({ name: "start2" });
    const endNode = createEndNode({ name: "end" });
    const builder = new FlowBuilder();
    builder.addNode(start1).addNode(start2).addNode(endNode);

    expect(() => builder.build()).toThrow(
      "There cannot be more than one start node",
    );
  });

  it("should detect a single StartNode without setEntryPoint", () => {
    const start = createStartNode({ name: "start" });
    const llmNode = makeLlmNode("llm-node");
    const endNode = createEndNode({ name: "end" });
    const builder = new FlowBuilder();
    builder
      .addNode(start)
      .addNode(llmNode)
      .addNode(endNode)
      .addEdge(start, llmNode)
      .addEdge(llmNode, endNode);

    const flow = builder.build();
    expect(flow.componentType).toBe("Flow");
    expect(flow.startNode.name).toBe("start");
  });

  it("should throw when referencing a non-existent node by name", () => {
    const llmNode = makeLlmNode("llm-node");
    const builder = new FlowBuilder();
    builder.addNode(llmNode);

    expect(() => builder.addEdge(llmNode, "non-existent")).toThrow(
      "Node with name 'non-existent' not found",
    );
  });

  it("should throw when adding a duplicate node name", () => {
    const node1 = makeLlmNode("same-name");
    const node2 = makeLlmNode("same-name");
    const builder = new FlowBuilder();
    builder.addNode(node1);

    expect(() => builder.addNode(node2)).toThrow(
      "Node with name 'same-name' already exists",
    );
  });

  it("should support multiple source nodes with matching branch list", () => {
    const llm1 = makeLlmNode("llm-1");
    const llm2 = makeLlmNode("llm-2");
    const endNode = createEndNode({ name: "end" });
    const builder = new FlowBuilder();
    builder.addNode(llm1).addNode(llm2).addNode(endNode);
    builder.setEntryPoint(llm1);
    builder.addEdge(llm1, llm2);
    builder.addEdge([llm1, llm2], endNode, [null, null]);

    const flow = builder.build();
    expect(flow.controlFlowConnections.length).toBeGreaterThanOrEqual(3);
  });
});

describe("FlowBuilder.buildLinearFlow edge cases", () => {
  it("should throw when nodes list is empty", () => {
    expect(() => FlowBuilder.buildLinearFlow({ nodes: [] })).toThrow(
      "nodes list must not be empty",
    );
  });

  it("should throw when nodes list starts with StartNode", () => {
    const start = createStartNode({ name: "start" });
    expect(() =>
      FlowBuilder.buildLinearFlow({ nodes: [start] }),
    ).toThrow("It is not necessary to add a StartNode");
  });

  it("should throw when nodes list ends with EndNode", () => {
    const llm = makeLlmNode("llm-node");
    const end = createEndNode({ name: "end" });
    expect(() =>
      FlowBuilder.buildLinearFlow({ nodes: [llm, end] }),
    ).toThrow("It is not necessary to add an EndNode");
  });

  it("should accept DataFlowEdge objects in dataFlowEdges", () => {
    const tool1 = createToolNode({ name: "tool-1", tool: makeTool() });
    const tool2 = createToolNode({ name: "tool-2", tool: makeTool() });
    const edge = createDataFlowEdge({
      name: "data-edge",
      sourceNode: tool1,
      sourceOutput: "result",
      destinationNode: tool2,
      destinationInput: "query",
    });
    const flow = FlowBuilder.buildLinearFlow({
      nodes: [tool1, tool2],
      dataFlowEdges: [edge],
    });
    expect(flow.dataFlowConnections).toBeDefined();
    expect(flow.dataFlowConnections!.length).toBe(1);
  });

  it("should accept 4-element tuples in dataFlowEdges", () => {
    const tool1 = createToolNode({ name: "tool-1", tool: makeTool() });
    const tool2 = createToolNode({ name: "tool-2", tool: makeTool() });
    const flow = FlowBuilder.buildLinearFlow({
      nodes: [tool1, tool2],
      dataFlowEdges: [["tool-1", "tool-2", "result", "query"]],
    });
    expect(flow.dataFlowConnections).toBeDefined();
    expect(flow.dataFlowConnections!.length).toBe(1);
  });

  it("should accept explicit inputs and outputs", () => {
    const llm = makeLlmNode("llm-node");
    const inputs = [stringProperty({ title: "my_input" })];
    const outputs = [stringProperty({ title: "my_output" })];
    const flow = FlowBuilder.buildLinearFlow({
      nodes: [llm],
      inputs,
      outputs,
    });
    expect(flow.startNode.inputs).toHaveLength(1);
    expect(flow.startNode.inputs![0]!.title).toBe("my_input");
  });
});

describe("FlowBuilder setFinishPoints edge cases", () => {
  it("should accept a flat list of properties (not nested array)", () => {
    const llm = makeLlmNode("llm-node");
    const builder = new FlowBuilder();
    builder.addNode(llm);
    builder.setEntryPoint(llm);
    builder.setFinishPoints(llm, [stringProperty({ title: "output" })]);
    const flow = builder.build();
    expect(
      flow.nodes.some(
        (n) =>
          (n as Record<string, unknown>)["componentType"] === "EndNode",
      ),
    ).toBe(true);
  });

  it("should throw when number of sources and outputs don't match", () => {
    const llm1 = makeLlmNode("llm-1");
    const llm2 = makeLlmNode("llm-2");
    const builder = new FlowBuilder();
    builder.addNode(llm1).addNode(llm2);

    expect(() =>
      builder.setFinishPoints(
        [llm1, llm2],
        [[stringProperty({ title: "out" })]],
      ),
    ).toThrow("Number of finish sources and outputs must match");
  });
});
