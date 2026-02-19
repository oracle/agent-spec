import { describe, it, expect } from "vitest";
import {
  createStartNode,
  createEndNode,
  createLlmNode,
  createToolNode,
  createAgentNode,
  createFlowNode,
  createBranchingNode,
  createMapNode,
  createParallelMapNode,
  createParallelFlowNode,
  createApiNode,
  createInputMessageNode,
  createOutputMessageNode,
  createCatchExceptionNode,
  createOpenAiCompatibleConfig,
  createAgent,
  createServerTool,
  createFlow,
  createControlFlowEdge,
  stringProperty,
  integerProperty,
  DEFAULT_NEXT_BRANCH,
  DEFAULT_LLM_OUTPUT,
  DEFAULT_BRANCH,
  DEFAULT_INPUT,
  DEFAULT_API_OUTPUT,
  DEFAULT_INPUT_MESSAGE_OUTPUT,
  CAUGHT_EXCEPTION_BRANCH,
  DEFAULT_EXCEPTION_INFO_VALUE,
  ReductionMethod,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeSimpleFlow() {
  const start = createStartNode({
    name: "start",
    inputs: [stringProperty({ title: "query" })],
  });
  const end = createEndNode({
    name: "end",
    outputs: [stringProperty({ title: "result" })],
  });
  const edge = createControlFlowEdge({
    name: "edge",
    fromNode: start,
    toNode: end,
  });
  return createFlow({
    name: "simple-flow",
    startNode: start,
    nodes: [start, end],
    controlFlowConnections: [edge],
  });
}

describe("StartNode", () => {
  it("should create with componentType StartNode", () => {
    const node = createStartNode({ name: "start" });
    expect(node.componentType).toBe("StartNode");
  });

  it("should set branches to [next]", () => {
    const node = createStartNode({ name: "start" });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });

  it("should not mirror inputs from outputs", () => {
    const node = createStartNode({
      name: "start",
      outputs: [stringProperty({ title: "x" })],
    });
    expect(node.inputs).toEqual([]);
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("x");
  });

  it("should not mirror outputs from inputs", () => {
    const node = createStartNode({
      name: "start",
      inputs: [stringProperty({ title: "y" })],
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("y");
    expect(node.outputs).toEqual([]);
  });

  it("should default inputs and outputs to empty when neither provided", () => {
    const node = createStartNode({ name: "start" });
    expect(node.inputs).toEqual([]);
    expect(node.outputs).toEqual([]);
  });

  it("should be frozen", () => {
    const node = createStartNode({ name: "start" });
    expect(Object.isFrozen(node)).toBe(true);
  });
});

describe("EndNode", () => {
  it("should create with componentType EndNode", () => {
    const node = createEndNode({ name: "end" });
    expect(node.componentType).toBe("EndNode");
  });

  it("should set branches to empty array", () => {
    const node = createEndNode({ name: "end" });
    expect(node.branches).toEqual([]);
  });

  it("should default branchName to next", () => {
    const node = createEndNode({ name: "end" });
    expect(node.branchName).toBe(DEFAULT_NEXT_BRANCH);
  });

  it("should accept custom branchName", () => {
    const node = createEndNode({ name: "end", branchName: "success" });
    expect(node.branchName).toBe("success");
  });

  it("should not mirror inputs from outputs", () => {
    const node = createEndNode({
      name: "end",
      outputs: [stringProperty({ title: "result" })],
    });
    expect(node.inputs).toEqual([]);
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("result");
  });
});

describe("LlmNode", () => {
  it("should create with componentType LlmNode", () => {
    const node = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Generate a response",
    });
    expect(node.componentType).toBe("LlmNode");
  });

  it("should set branches to [next]", () => {
    const node = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Generate a response",
    });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });

  it("should infer inputs from promptTemplate placeholders", () => {
    const node = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Translate {{text}} to {{language}}",
    });
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("text");
    expect(titles).toContain("language");
    expect(node.inputs).toHaveLength(2);
  });

  it("should default output to StringProperty(generated_text)", () => {
    const node = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Generate something",
    });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe(DEFAULT_LLM_OUTPUT);
    expect(node.outputs![0]!.type).toBe("string");
  });

  it("should use custom outputs when provided", () => {
    const node = createLlmNode({
      name: "llm",
      llmConfig: makeLlmConfig(),
      promptTemplate: "Generate something",
      outputs: [integerProperty({ title: "custom_output" })],
    });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("custom_output");
  });
});

describe("ToolNode", () => {
  it("should create with componentType ToolNode", () => {
    const tool = createServerTool({ name: "my-tool" });
    const node = createToolNode({ name: "tool-node", tool });
    expect(node.componentType).toBe("ToolNode");
  });

  it("should infer inputs/outputs from tool", () => {
    const tool = createServerTool({
      name: "calc",
      inputs: [stringProperty({ title: "expression" })],
      outputs: [integerProperty({ title: "result" })],
    });
    const node = createToolNode({ name: "tool-node", tool });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe("expression");
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe("result");
  });

  it("should set branches to [next]", () => {
    const tool = createServerTool({ name: "my-tool" });
    const node = createToolNode({ name: "tool-node", tool });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("AgentNode", () => {
  it("should create with componentType AgentNode", () => {
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    const node = createAgentNode({ name: "agent-node", agent });
    expect(node.componentType).toBe("AgentNode");
  });

  it("should infer inputs/outputs from agent", () => {
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Help with {{topic}}.",
      outputs: [stringProperty({ title: "answer" })],
    });
    const node = createAgentNode({ name: "agent-node", agent });
    expect(node.inputs!.map((i) => i.title)).toContain("topic");
    expect(node.outputs!.map((o) => o.title)).toContain("answer");
  });

  it("should default branches to [next]", () => {
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "You are helpful.",
    });
    const node = createAgentNode({ name: "agent-node", agent });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("FlowNode", () => {
  it("should create with componentType FlowNode", () => {
    const flow = makeSimpleFlow();
    const node = createFlowNode({ name: "flow-node", subflow: flow });
    expect(node.componentType).toBe("FlowNode");
  });

  it("should infer inputs/outputs from subflow", () => {
    const flow = makeSimpleFlow();
    const node = createFlowNode({ name: "flow-node", subflow: flow });
    expect(node.inputs!.map((i) => i.title)).toContain("query");
    expect(node.outputs!.map((o) => o.title)).toContain("result");
  });

  it("should infer branches from subflow EndNode branchNames", () => {
    const start = createStartNode({ name: "start" });
    const end1 = createEndNode({ name: "end-success", branchName: "success" });
    const end2 = createEndNode({ name: "end-failure", branchName: "failure" });
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
      name: "branching-flow",
      startNode: start,
      nodes: [start, end1, end2],
      controlFlowConnections: [e1, e2],
    });
    const node = createFlowNode({ name: "flow-node", subflow: flow });
    expect(node.branches).toContain("success");
    expect(node.branches).toContain("failure");
  });
});

describe("BranchingNode", () => {
  it("should create with componentType BranchingNode", () => {
    const node = createBranchingNode({
      name: "branch",
      mapping: { yes: "approve", no: "reject" },
    });
    expect(node.componentType).toBe("BranchingNode");
  });

  it("should infer branches from mapping values plus default", () => {
    const node = createBranchingNode({
      name: "branch",
      mapping: { positive: "approve", negative: "reject" },
    });
    expect(node.branches).toContain(DEFAULT_BRANCH);
    expect(node.branches).toContain("approve");
    expect(node.branches).toContain("reject");
  });

  it("should default input to StringProperty(branching_mapping_key)", () => {
    const node = createBranchingNode({
      name: "branch",
      mapping: { a: "b" },
    });
    expect(node.inputs).toHaveLength(1);
    expect(node.inputs![0]!.title).toBe(DEFAULT_INPUT);
    expect(node.inputs![0]!.type).toBe("string");
  });

  it("should set outputs to empty array", () => {
    const node = createBranchingNode({
      name: "branch",
      mapping: { a: "b" },
    });
    expect(node.outputs).toEqual([]);
  });
});

describe("MapNode", () => {
  it("should create with componentType MapNode", () => {
    const flow = makeSimpleFlow();
    const node = createMapNode({ name: "map", subflow: flow });
    expect(node.componentType).toBe("MapNode");
  });

  it("should infer inputs with iterated_ prefix", () => {
    const flow = makeSimpleFlow();
    const node = createMapNode({ name: "map", subflow: flow });
    const inputTitles = node.inputs!.map((i) => i.title);
    expect(inputTitles).toContain("iterated_query");
  });

  it("should infer outputs with collected_ prefix", () => {
    const flow = makeSimpleFlow();
    const node = createMapNode({ name: "map", subflow: flow });
    const outputTitles = node.outputs!.map((o) => o.title);
    expect(outputTitles).toContain("collected_result");
  });

  it("should default reducers to APPEND for all outputs", () => {
    const flow = makeSimpleFlow();
    const node = createMapNode({ name: "map", subflow: flow });
    expect(node.reducers).toEqual({ result: ReductionMethod.APPEND });
  });

  it("should set branches to [next]", () => {
    const flow = makeSimpleFlow();
    const node = createMapNode({ name: "map", subflow: flow });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("ParallelMapNode", () => {
  it("should create with componentType ParallelMapNode", () => {
    const flow = makeSimpleFlow();
    const node = createParallelMapNode({ name: "pmap", subflow: flow });
    expect(node.componentType).toBe("ParallelMapNode");
  });

  it("should infer inputs with iterated_ prefix", () => {
    const flow = makeSimpleFlow();
    const node = createParallelMapNode({ name: "pmap", subflow: flow });
    const inputTitles = node.inputs!.map((i) => i.title);
    expect(inputTitles).toContain("iterated_query");
  });

  it("should infer outputs with collected_ prefix", () => {
    const flow = makeSimpleFlow();
    const node = createParallelMapNode({ name: "pmap", subflow: flow });
    const outputTitles = node.outputs!.map((o) => o.title);
    expect(outputTitles).toContain("collected_result");
  });
});

describe("ParallelFlowNode", () => {
  it("should create with componentType ParallelFlowNode", () => {
    const node = createParallelFlowNode({ name: "parallel" });
    expect(node.componentType).toBe("ParallelFlowNode");
  });

  it("should union inputs from multiple subflows", () => {
    const flow1 = makeSimpleFlow();
    const start2 = createStartNode({
      name: "start",
      inputs: [stringProperty({ title: "input_b" })],
    });
    const end2 = createEndNode({
      name: "end",
      outputs: [stringProperty({ title: "output_b" })],
    });
    const edge2 = createControlFlowEdge({
      name: "edge",
      fromNode: start2,
      toNode: end2,
    });
    const flow2 = createFlow({
      name: "flow2",
      startNode: start2,
      nodes: [start2, end2],
      controlFlowConnections: [edge2],
    });

    const node = createParallelFlowNode({
      name: "parallel",
      subflows: [flow1, flow2],
    });
    const inputTitles = node.inputs!.map((i) => i.title);
    expect(inputTitles).toContain("query");
    expect(inputTitles).toContain("input_b");
  });

  it("should union outputs from multiple subflows", () => {
    const flow1 = makeSimpleFlow();
    const start2 = createStartNode({ name: "start" });
    const end2 = createEndNode({
      name: "end",
      outputs: [stringProperty({ title: "output_b" })],
    });
    const edge2 = createControlFlowEdge({
      name: "edge",
      fromNode: start2,
      toNode: end2,
    });
    const flow2 = createFlow({
      name: "flow2",
      startNode: start2,
      nodes: [start2, end2],
      controlFlowConnections: [edge2],
    });

    const node = createParallelFlowNode({
      name: "parallel",
      subflows: [flow1, flow2],
    });
    const outputTitles = node.outputs!.map((o) => o.title);
    expect(outputTitles).toContain("result");
    expect(outputTitles).toContain("output_b");
  });

  it("should default subflows to empty", () => {
    const node = createParallelFlowNode({ name: "parallel" });
    expect(node.subflows).toEqual([]);
    expect(node.inputs).toEqual([]);
    expect(node.outputs).toEqual([]);
  });

  it("should set branches to [next]", () => {
    const node = createParallelFlowNode({ name: "parallel" });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("ApiNode", () => {
  it("should create with componentType ApiNode", () => {
    const node = createApiNode({
      name: "api",
      url: "https://api.example.com",
      httpMethod: "GET",
    });
    expect(node.componentType).toBe("ApiNode");
  });

  it("should infer inputs from URL placeholders", () => {
    const node = createApiNode({
      name: "api",
      url: "https://api.example.com/{{resource}}",
      httpMethod: "GET",
    });
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("resource");
  });

  it("should infer inputs from data/params/headers", () => {
    const node = createApiNode({
      name: "api",
      url: "https://api.example.com",
      httpMethod: "POST",
      data: { query: "{{search_term}}" },
      headers: { Authorization: "Bearer {{token}}" },
    });
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("search_term");
    expect(titles).toContain("token");
  });

  it("should default output to Property(response)", () => {
    const node = createApiNode({
      name: "api",
      url: "https://api.example.com",
      httpMethod: "GET",
    });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe(DEFAULT_API_OUTPUT);
  });

  it("should set branches to [next]", () => {
    const node = createApiNode({
      name: "api",
      url: "https://api.example.com",
      httpMethod: "GET",
    });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("InputMessageNode", () => {
  it("should create with componentType InputMessageNode", () => {
    const node = createInputMessageNode({ name: "input" });
    expect(node.componentType).toBe("InputMessageNode");
  });

  it("should infer inputs from message placeholders", () => {
    const node = createInputMessageNode({
      name: "input",
      message: "Please enter {{field_name}}:",
    });
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("field_name");
  });

  it("should have empty inputs when no message", () => {
    const node = createInputMessageNode({ name: "input" });
    expect(node.inputs).toEqual([]);
  });

  it("should default output to StringProperty(user_input)", () => {
    const node = createInputMessageNode({ name: "input" });
    expect(node.outputs).toHaveLength(1);
    expect(node.outputs![0]!.title).toBe(DEFAULT_INPUT_MESSAGE_OUTPUT);
    expect(node.outputs![0]!.type).toBe("string");
  });

  it("should set branches to [next]", () => {
    const node = createInputMessageNode({ name: "input" });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("OutputMessageNode", () => {
  it("should create with componentType OutputMessageNode", () => {
    const node = createOutputMessageNode({
      name: "output",
      message: "Hello!",
    });
    expect(node.componentType).toBe("OutputMessageNode");
  });

  it("should infer inputs from message placeholders", () => {
    const node = createOutputMessageNode({
      name: "output",
      message: "Hello {{user}}, your score is {{score}}",
    });
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("user");
    expect(titles).toContain("score");
  });

  it("should have empty outputs", () => {
    const node = createOutputMessageNode({
      name: "output",
      message: "Hello!",
    });
    expect(node.outputs).toEqual([]);
  });

  it("should set branches to [next]", () => {
    const node = createOutputMessageNode({
      name: "output",
      message: "Hello!",
    });
    expect(node.branches).toEqual([DEFAULT_NEXT_BRANCH]);
  });
});

describe("CatchExceptionNode", () => {
  it("should create with componentType CatchExceptionNode", () => {
    const flow = makeSimpleFlow();
    const node = createCatchExceptionNode({
      name: "catch",
      subflow: flow,
    });
    expect(node.componentType).toBe("CatchExceptionNode");
  });

  it("should infer inputs from subflow", () => {
    const flow = makeSimpleFlow();
    const node = createCatchExceptionNode({
      name: "catch",
      subflow: flow,
    });
    const titles = node.inputs!.map((i) => i.title);
    expect(titles).toContain("query");
  });

  it("should infer outputs from subflow plus caught_exception_info", () => {
    const flow = makeSimpleFlow();
    const node = createCatchExceptionNode({
      name: "catch",
      subflow: flow,
    });
    const titles = node.outputs!.map((o) => o.title);
    expect(titles).toContain("result");
    expect(titles).toContain(DEFAULT_EXCEPTION_INFO_VALUE);
  });

  it("should include caught_exception_branch in branches", () => {
    const flow = makeSimpleFlow();
    const node = createCatchExceptionNode({
      name: "catch",
      subflow: flow,
    });
    expect(node.branches).toContain(CAUGHT_EXCEPTION_BRANCH);
  });

  it("should include subflow EndNode branches", () => {
    const flow = makeSimpleFlow();
    const node = createCatchExceptionNode({
      name: "catch",
      subflow: flow,
    });
    expect(node.branches).toContain(CAUGHT_EXCEPTION_BRANCH);
    expect(node.branches).toContain(DEFAULT_NEXT_BRANCH);
  });

  it("should set caught_exception_info with string|null type and default null", () => {
    const flow = makeSimpleFlow();
    const node = createCatchExceptionNode({
      name: "catch",
      subflow: flow,
    });
    const exProp = node.outputs!.find(
      (o) => o.title === DEFAULT_EXCEPTION_INFO_VALUE,
    );
    expect(exProp).toBeDefined();
    expect(exProp!.jsonSchema["anyOf"]).toEqual([
      { type: "string" },
      { type: "null" },
    ]);
    expect(exProp!.default).toBeNull();
  });
});

describe("ReductionMethod", () => {
  it("should define all methods", () => {
    expect(ReductionMethod.APPEND).toBe("append");
    expect(ReductionMethod.SUM).toBe("sum");
    expect(ReductionMethod.AVERAGE).toBe("average");
    expect(ReductionMethod.MAX).toBe("max");
    expect(ReductionMethod.MIN).toBe("min");
  });
});
