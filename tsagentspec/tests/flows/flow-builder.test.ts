import { describe, it, expect } from "vitest";
import {
  FlowBuilder,
  createLlmNode,
  createToolNode,
  createOutputMessageNode,
  createOpenAiCompatibleConfig,
  createServerTool,
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

describe("FlowBuilder", () => {
  describe("addNode", () => {
    it("should add a node to the flow", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      // verify by building (will need entry/exit points)
    });

    it("should throw on duplicate node names", () => {
      const llm1 = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello",
      });
      const llm2 = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "World",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm1);
      expect(() => builder.addNode(llm2)).toThrow(
        "Node with name 'llm' already exists",
      );
    });
  });

  describe("addSequence", () => {
    it("should add multiple nodes and connect them in sequence", () => {
      const llm1 = createLlmNode({
        name: "llm1",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Step 1",
      });
      const llm2 = createLlmNode({
        name: "llm2",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Step 2",
      });
      const builder = new FlowBuilder();
      builder.addSequence([llm1, llm2]);
      builder.setEntryPoint("llm1");
      builder.setFinishPoints("llm2");
      const flow = builder.build("seq-flow");
      expect(flow.nodes.length).toBeGreaterThanOrEqual(4); // start + llm1 + llm2 + end
    });
  });

  describe("setEntryPoint", () => {
    it("should create a StartNode and connect it", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm");
      builder.setFinishPoints("llm");
      const flow = builder.build();
      const startNodes = flow.nodes.filter(
        (n: Record<string, unknown>) => n["componentType"] === "StartNode",
      );
      expect(startNodes).toHaveLength(1);
    });

    it("should accept input properties", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello {{name}}",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm", [stringProperty({ title: "name" })]);
      builder.setFinishPoints("llm");
      const flow = builder.build();
      expect(flow.inputs).toHaveLength(1);
      expect(flow.inputs![0]!.title).toBe("name");
    });

    it("should throw if called twice", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm");
      expect(() => builder.setEntryPoint("llm")).toThrow(
        "Entry point already set",
      );
    });
  });

  describe("setFinishPoints", () => {
    it("should create EndNodes and connect them", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm");
      builder.setFinishPoints("llm", [
        stringProperty({ title: "output" }),
      ]);
      const flow = builder.build();
      const endNodes = flow.nodes.filter(
        (n: Record<string, unknown>) => n["componentType"] === "EndNode",
      );
      expect(endNodes).toHaveLength(1);
    });
  });

  describe("build", () => {
    it("should throw if no start node exists", () => {
      const builder = new FlowBuilder();
      expect(() => builder.build()).toThrow();
    });

    it("should throw if no end node exists", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello",
      });
      const builder = new FlowBuilder();
      builder.addNode(llm);
      builder.setEntryPoint("llm");
      expect(() => builder.build()).toThrow("Missing finish node");
    });

    it("should build a complete flow", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello {{name}}",
      });
      const output = createOutputMessageNode({
        name: "output",
        message: "Result: {{generated_text}}",
      });
      const builder = new FlowBuilder();
      builder.addSequence([llm, output]);
      builder.setEntryPoint("llm", [stringProperty({ title: "name" })]);
      builder.setFinishPoints("output");
      const flow = builder.build("my-flow");
      expect(flow.name).toBe("my-flow");
      expect(flow.componentType).toBe("Flow");
    });
  });

  describe("buildLinearFlow", () => {
    it("should build a linear flow from a list of nodes", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Hello {{name}}",
      });
      const flow = FlowBuilder.buildLinearFlow({
        nodes: [llm],
        name: "linear-flow",
      });
      expect(flow.componentType).toBe("Flow");
      expect(flow.name).toBe("linear-flow");
    });

    it("should throw if nodes is empty", () => {
      expect(() => FlowBuilder.buildLinearFlow({ nodes: [] })).toThrow(
        "nodes list must not be empty",
      );
    });

    it("should infer inputs from first node and outputs from last node", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Translate: {{text}}",
      });
      const flow = FlowBuilder.buildLinearFlow({ nodes: [llm] });
      expect(flow.inputs!.map((i) => i.title)).toContain("text");
      expect(flow.outputs!.map((o) => o.title)).toContain("generated_text");
    });

    it("should accept custom inputs and outputs", () => {
      const llm = createLlmNode({
        name: "llm",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Do something",
      });
      const flow = FlowBuilder.buildLinearFlow({
        nodes: [llm],
        inputs: [stringProperty({ title: "custom_in" })],
        outputs: [stringProperty({ title: "custom_out" })],
      });
      expect(flow.inputs).toHaveLength(1);
      expect(flow.inputs![0]!.title).toBe("custom_in");
      expect(flow.outputs).toHaveLength(1);
      expect(flow.outputs![0]!.title).toBe("custom_out");
    });

    it("should create multiple nodes in sequence", () => {
      const llm1 = createLlmNode({
        name: "llm1",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Step 1: {{input}}",
      });
      const llm2 = createLlmNode({
        name: "llm2",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Step 2: {{generated_text}}",
      });
      const flow = FlowBuilder.buildLinearFlow({
        nodes: [llm1, llm2],
        name: "two-step",
      });
      // start + llm1 + llm2 + end = 4 nodes
      expect(flow.nodes.length).toBe(4);
      // start->llm1, llm1->llm2, llm2->end = 3 edges
      expect(flow.controlFlowConnections.length).toBe(3);
    });

    it("should support data flow edges", () => {
      const llm1 = createLlmNode({
        name: "llm1",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Step 1",
      });
      const llm2 = createLlmNode({
        name: "llm2",
        llmConfig: makeLlmConfig(),
        promptTemplate: "Step 2: {{generated_text}}",
      });
      const flow = FlowBuilder.buildLinearFlow({
        nodes: [llm1, llm2],
        dataFlowEdges: [["llm1", "llm2", "generated_text"]],
      });
      expect(flow.dataFlowConnections).toBeDefined();
      expect(flow.dataFlowConnections!.length).toBe(1);
    });
  });

  describe("addEdge", () => {
    it("should add a control flow edge between two nodes", () => {
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
      builder.addEdge("llm1", "llm2");
      builder.setEntryPoint("llm1");
      builder.setFinishPoints("llm2");
      const flow = builder.build();
      expect(flow.controlFlowConnections.length).toBeGreaterThanOrEqual(3);
    });

    it("should accept node objects instead of names", () => {
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
      builder.addEdge(llm1, llm2);
      builder.setEntryPoint(llm1);
      builder.setFinishPoints(llm2);
      const flow = builder.build();
      expect(flow.componentType).toBe("Flow");
    });
  });

  describe("addDataEdge", () => {
    it("should add a data flow edge", () => {
      const llm1 = createLlmNode({
        name: "llm1",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const llm2 = createLlmNode({
        name: "llm2",
        llmConfig: makeLlmConfig(),
        promptTemplate: "B: {{generated_text}}",
      });
      const builder = new FlowBuilder();
      builder.addSequence([llm1, llm2]);
      builder.addDataEdge("llm1", "llm2", "generated_text");
      builder.setEntryPoint("llm1");
      builder.setFinishPoints("llm2");
      const flow = builder.build();
      expect(flow.dataFlowConnections).toBeDefined();
      expect(flow.dataFlowConnections!.length).toBe(1);
    });

    it("should accept [sourceOutput, destInput] tuple", () => {
      const llm1 = createLlmNode({
        name: "llm1",
        llmConfig: makeLlmConfig(),
        promptTemplate: "A",
      });
      const llm2 = createLlmNode({
        name: "llm2",
        llmConfig: makeLlmConfig(),
        promptTemplate: "B: {{input_text}}",
      });
      const builder = new FlowBuilder();
      builder.addSequence([llm1, llm2]);
      builder.addDataEdge("llm1", "llm2", [
        "generated_text",
        "input_text",
      ]);
      builder.setEntryPoint("llm1");
      builder.setFinishPoints("llm2");
      const flow = builder.build();
      const de = flow.dataFlowConnections![0]!;
      expect(de.sourceOutput).toBe("generated_text");
      expect(de.destinationInput).toBe("input_text");
    });
  });
});
