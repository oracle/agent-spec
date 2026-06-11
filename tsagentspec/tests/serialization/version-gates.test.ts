import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecVersion,
  createAgent,
  createOpenAiCompatibleConfig,
  createServerTool,
  createBuiltinTool,
  createMCPToolBox,
  createStdioTransport,
  createControlFlowEdge,
  createEndNode,
  createFlow,
  createFlowNode,
  createStartNode,
  stringProperty,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeFlow() {
  const start = createStartNode({ name: "start" });
  const end = createEndNode({ name: "end" });
  return createFlow({
    name: "flow",
    startNode: start,
    nodes: [start, end],
    controlFlowConnections: [
      createControlFlowEdge({ name: "start-end", fromNode: start, toNode: end }),
    ],
  });
}

describe("version-gated field serialization", () => {
  it("should exclude humanInTheLoop for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      humanInTheLoop: false,
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as string;
    const dict = JSON.parse(json);
    expect("human_in_the_loop" in dict).toBe(false);
  });

  it("should include humanInTheLoop for version 25.4.2+", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      humanInTheLoop: false,
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_2,
    }) as string;
    const dict = JSON.parse(json);
    expect("human_in_the_loop" in dict).toBe(true);
  });

  it("should throw when serializing MCPToolBox at version before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const toolbox = createMCPToolBox({
      name: "toolbox",
      clientTransport: createStdioTransport({
        name: "stdio",
        command: "node",
      }),
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      toolboxes: [toolbox],
    });
    expect(() =>
      serializer.toJson(agent, {
        agentspecVersion: AgentSpecVersion.V25_4_1,
      }),
    ).toThrow(/Invalid agentspec_version.*25\.4\.1.*25\.4\.2.*toolbox/);
  });

  it("should exclude requiresConfirmation on tools for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createServerTool({
      name: "tool",
      inputs: [stringProperty({ title: "q" })],
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as string;
    const dict = JSON.parse(json);
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("requires_confirmation" in tools[0]!).toBe(false);
  });

  it("should version-gate BuiltinTool _self fields for versions before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      configuration: { language: "python" },
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
    });

    // For current version, BuiltinTool should appear with all fields
    const json = serializer.toJson(agent) as string;
    const dictCurrent = JSON.parse(json);
    const toolsCurrent = dictCurrent["tools"] as Record<string, unknown>[];
    const btCurrent = toolsCurrent.find(
      (t) => t["component_type"] === "BuiltinTool",
    );
    expect(btCurrent).toBeDefined();
    expect(btCurrent!["tool_type"]).toBe("code_execution");
  });

  it("should exclude MCPToolBox requiresConfirmation for versions before 26.2.0", () => {
    const serializer = new AgentSpecSerializer();
    const toolbox = createMCPToolBox({
      name: "toolbox",
      clientTransport: createStdioTransport({
        name: "stdio",
        command: "node",
      }),
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      toolboxes: [toolbox],
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_2,
    }) as string;
    const dict = JSON.parse(json);
    const toolboxes = dict["toolboxes"] as Record<string, unknown>[];
    expect("requires_confirmation" in toolboxes[0]!).toBe(false);
  });

  it("should include MCPToolBox requiresConfirmation for version 26.2.0+", () => {
    const serializer = new AgentSpecSerializer();
    const toolbox = createMCPToolBox({
      name: "toolbox",
      clientTransport: createStdioTransport({
        name: "stdio",
        command: "node",
      }),
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      toolboxes: [toolbox],
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V26_2_0,
    }) as string;
    const dict = JSON.parse(json);
    const toolboxes = dict["toolboxes"] as Record<string, unknown>[];
    expect("requires_confirmation" in toolboxes[0]!).toBe(true);
  });

  it("should version-gate FlowNode propagatePendingInput before 26.2.0", () => {
    const serializer = new AgentSpecSerializer();
    const node = createFlowNode({
      name: "flow-node",
      subflow: makeFlow(),
      propagatePendingInput: false,
    });

    const oldJson = serializer.toJson(node, {
      agentspecVersion: AgentSpecVersion.V26_1_0,
    }) as string;
    expect("propagate_pending_input" in JSON.parse(oldJson)).toBe(false);

    const newJson = serializer.toJson(node, {
      agentspecVersion: AgentSpecVersion.V26_2_0,
    }) as string;
    const newDict = JSON.parse(newJson);
    expect(newDict["propagate_pending_input"]).toBe(false);
  });

  it("should include everything for current version", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createServerTool({
      name: "tool",
      inputs: [stringProperty({ title: "q" })],
      requiresConfirmation: true,
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
      humanInTheLoop: false,
    });
    const json = serializer.toJson(agent) as string;
    const dict = JSON.parse(json);
    expect("human_in_the_loop" in dict).toBe(true);
    const tools = dict["tools"] as Record<string, unknown>[];
    expect("requires_confirmation" in tools[0]!).toBe(true);
  });

  it("should throw when serializing BuiltinTool at version before 25.4.2", () => {
    const serializer = new AgentSpecSerializer();
    const tool = createBuiltinTool({
      name: "code-exec",
      toolType: "code_execution",
      configuration: { language: "python" },
    });
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [tool],
    });
    expect(() =>
      serializer.toJson(agent, {
        agentspecVersion: AgentSpecVersion.V25_4_1,
      }),
    ).toThrow(/Invalid agentspec_version.*25\.4\.1.*25\.4\.2.*code-exec/);
  });
});
