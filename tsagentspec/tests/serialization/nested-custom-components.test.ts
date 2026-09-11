import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecDeserializer,
  camelToSnake,
  snakeToCamel,
  createAgent,
  createControlFlowEdge,
  createEndNode,
  createFlow,
  createOpenAiCompatibleConfig,
  createServerTool,
  createStartNode,
  createToolNode,
  stringProperty,
  type Agent,
  type ComponentBase,
  type ComponentDeserializationPlugin,
  type ComponentSerializationPlugin,
  type Flow,
  type ToolNode,
} from "../../src/index.js";
import type { SerializedDict, SerializedFields } from "../../src/serialization/types.js";
import type { SerializationContext } from "../../src/serialization/serialization-context.js";
import type { DeserializationContext } from "../../src/serialization/deserialization-context.js";

// Plugin-provided component types, as an integrator would define them
// (see oracle/agent-spec#219: FunctionTransform / ConnectorToolBox attached to an Agent).
interface FunctionTransform extends ComponentBase {
  componentType: "FunctionTransform";
  functionName: string;
}

interface ConnectorToolBox extends ComponentBase {
  componentType: "ConnectorToolBox";
  connectorId: string;
}

interface CalculatorTool extends ComponentBase {
  componentType: "CalculatorTool";
  precision: number;
  requiresConfirmation: boolean;
}

interface AuditNode extends ComponentBase {
  componentType: "AuditNode";
  branches: string[];
  inputs: never[];
  outputs: never[];
  auditLevel: string;
}

const CUSTOM_COMPONENT_TYPES = [
  "FunctionTransform",
  "ConnectorToolBox",
  "CalculatorTool",
  "AuditNode",
];

const PROTOCOL_FIELDS = new Set([
  "component_type",
  "component_plugin_name",
  "component_plugin_version",
  "agentspec_version",
  "$referenced_components",
]);

class AcmeSerializationPlugin implements ComponentSerializationPlugin {
  readonly pluginName = "AcmeComponentsPlugin";
  readonly pluginVersion = "1.0.0";

  supportedComponentTypes(): string[] {
    return CUSTOM_COMPONENT_TYPES;
  }

  serialize(component: ComponentBase, context: SerializationContext): SerializedFields {
    const fields: SerializedFields = {};
    for (const [key, value] of Object.entries(component)) {
      if (key === "componentType") continue;
      fields[camelToSnake(key)] = context.dumpField(value);
    }
    return fields;
  }
}

class AcmeDeserializationPlugin implements ComponentDeserializationPlugin {
  readonly pluginName = "AcmeComponentsPlugin";
  readonly pluginVersion = "1.0.0";

  supportedComponentTypes(): string[] {
    return CUSTOM_COMPONENT_TYPES;
  }

  deserialize(data: SerializedDict, context: DeserializationContext): ComponentBase {
    const component: Record<string, unknown> = {
      componentType: context.getComponentType(data),
    };
    for (const [key, value] of Object.entries(data)) {
      if (PROTOCOL_FIELDS.has(key)) continue;
      component[snakeToCamel(key)] = context.loadField(value);
    }
    return component as unknown as ComponentBase;
  }
}

const functionTransform: FunctionTransform = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "redact-pii",
  metadata: {},
  componentType: "FunctionTransform",
  functionName: "redactPii",
};

const connectorToolBox: ConnectorToolBox = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "crm-connector",
  description: "Tools exposed by the CRM connector",
  metadata: {},
  componentType: "ConnectorToolBox",
  connectorId: "crm-prod",
};

const calculatorTool: CalculatorTool = {
  id: "33333333-3333-4333-8333-333333333333",
  name: "calculator",
  metadata: {},
  componentType: "CalculatorTool",
  precision: 4,
  requiresConfirmation: false,
};

const auditNode: AuditNode = {
  id: "44444444-4444-4444-8444-444444444444",
  name: "audit",
  metadata: {},
  componentType: "AuditNode",
  branches: ["next"],
  inputs: [],
  outputs: [],
  auditLevel: "full",
};

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "test-model",
  });
}

function makeSerializer(): AgentSpecSerializer {
  return new AgentSpecSerializer([new AcmeSerializationPlugin()]);
}

function makeDeserializer(): AgentSpecDeserializer {
  return new AgentSpecDeserializer([new AcmeDeserializationPlugin()]);
}

describe("Custom components nested inside builtin components", () => {
  it("round-trips an Agent whose transforms, toolboxes and tools hold plugin components", () => {
    const agent = createAgent({
      name: "assistant",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Help the user.",
      tools: [calculatorTool],
      toolboxes: [connectorToolBox],
      transforms: [functionTransform],
    });

    const json = makeSerializer().toJson(agent) as string;
    const doc = JSON.parse(json) as Record<string, unknown[]>;
    const serializedTransform = doc["transforms"]![0] as Record<string, unknown>;
    expect(serializedTransform["component_type"]).toBe("FunctionTransform");
    expect(serializedTransform["component_plugin_name"]).toBe("AcmeComponentsPlugin");
    expect(serializedTransform["function_name"]).toBe("redactPii");

    const loaded = makeDeserializer().fromJson(json) as Agent;
    expect(loaded.componentType).toBe("Agent");
    expect(loaded.transforms).toEqual([functionTransform]);
    expect(loaded.toolboxes).toEqual([connectorToolBox]);
    expect(loaded.tools).toEqual([calculatorTool]);
  });

  it("round-trips the same document through YAML", () => {
    const agent = createAgent({
      name: "assistant",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Help the user.",
      transforms: [functionTransform],
    });

    const yaml = makeSerializer().toYaml(agent) as string;
    const loaded = makeDeserializer().fromYaml(yaml) as Agent;
    expect(loaded.transforms).toEqual([functionTransform]);
  });

  it("accepts plugin components next to builtin ones at construction time", () => {
    const serverTool = createServerTool({
      name: "lookup",
      description: "Looks something up",
      inputs: [stringProperty({ title: "query" })],
    });

    const agent = createAgent({
      name: "assistant",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Help the user.",
      tools: [serverTool, calculatorTool],
    });

    // Builtin defaults are still applied, custom components are kept as provided
    expect(agent.tools[0]).toMatchObject({
      componentType: "ServerTool",
      requiresConfirmation: false,
    });
    expect(agent.tools[1]).toEqual(calculatorTool);
  });

  it("still rejects builtin components of the wrong kind", () => {
    const llmConfig = makeLlmConfig();
    const serverTool = createServerTool({ name: "lookup", description: "Looks up" });

    expect(() =>
      createAgent({
        name: "assistant",
        llmConfig,
        systemPrompt: "x",
        tools: [llmConfig],
      }),
    ).toThrow(/Invalid discriminator value/);

    expect(() =>
      createAgent({
        name: "assistant",
        llmConfig,
        systemPrompt: "x",
        transforms: [serverTool],
      }),
    ).toThrow(/Invalid discriminator value/);
  });

  it("still validates the base component fields of plugin components", () => {
    const incomplete = { componentType: "FunctionTransform", functionName: "redactPii" };

    expect(() =>
      createAgent({
        name: "assistant",
        llmConfig: makeLlmConfig(),
        systemPrompt: "x",
        transforms: [incomplete as unknown as ComponentBase],
      }),
    ).toThrow(/name/);
  });

  it("fails clearly when no plugin handles the nested component type", () => {
    const agent = createAgent({
      name: "assistant",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Help the user.",
      transforms: [functionTransform],
    });
    const json = makeSerializer().toJson(agent) as string;

    expect(() => new AgentSpecDeserializer().fromJson(json)).toThrow(
      'No plugin to deserialize component type "FunctionTransform"',
    );
  });

  it("round-trips a Flow with a plugin node and a ToolNode holding a plugin tool", () => {
    const start = createStartNode({ name: "start" });
    const toolNode = createToolNode({ name: "calculate", tool: calculatorTool });
    const end = createEndNode({ name: "end" });
    const flow = createFlow({
      name: "audited-flow",
      startNode: start,
      nodes: [start, auditNode, toolNode, end],
      controlFlowConnections: [
        createControlFlowEdge({ name: "start_to_audit", fromNode: start, toNode: auditNode }),
        createControlFlowEdge({ name: "audit_to_tool", fromNode: auditNode, toNode: toolNode }),
        createControlFlowEdge({ name: "tool_to_end", fromNode: toolNode, toNode: end }),
      ],
    });
    expect(toolNode.tool).toEqual(calculatorTool);

    const json = makeSerializer().toJson(flow) as string;
    const loaded = makeDeserializer().fromJson(json) as Flow;

    expect(loaded.nodes.map((node) => node["componentType"])).toEqual([
      "StartNode",
      "AuditNode",
      "ToolNode",
      "EndNode",
    ]);
    expect(loaded.nodes[1]).toEqual(auditNode);
    expect((loaded.nodes[2] as ToolNode).tool).toEqual(calculatorTool);
  });
});
