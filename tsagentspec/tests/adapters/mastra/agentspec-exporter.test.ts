import { describe, expect, it } from "vitest";
import {
  AgentSpecDeserializer,
  AgentSpecSerializer,
  createAgent,
  createAgentNode,
  createBuiltinTool,
  createControlFlowEdge,
  createEndNode,
  createFlow,
  createLlmNode,
  createOpenAiConfig,
  createOpenAiCompatibleConfig,
  createServerTool,
  createStartNode,
  createToolNode,
  stringProperty,
  type Agent,
} from "../../../src/index.js";
import {
  AgentSpecExporter,
  convertAgentSpecFlowToMastraWorkflow,
  convertAgentSpecToMastraAgent,
  UnsupportedMastraExportError,
  type MastraAgentRuntimeConfig,
  type MastraRuntimeAdapter,
  type MastraToolRuntimeConfig,
  type MastraWorkflowRuntimeAdapter,
  type MastraWorkflowRuntimeConfig,
  type MastraWorkflowStepRuntimeConfig,
} from "../../../src/adapters/mastra/index.js";

type FakeTool = {
  config: MastraToolRuntimeConfig;
};

type FakeAgent = {
  config: MastraAgentRuntimeConfig<FakeTool>;
};

type FakeStep = {
  config: MastraWorkflowStepRuntimeConfig;
};

type FakeWorkflow = {
  config: MastraWorkflowRuntimeConfig<FakeStep>;
  steps: FakeStep[];
};

const fakeAgentRuntime: MastraRuntimeAdapter<FakeAgent, FakeTool> = {
  createAgent: (config) => ({ config }),
  createTool: (config) => ({ config }),
};

const fakeWorkflowRuntime: MastraWorkflowRuntimeAdapter<FakeWorkflow, FakeStep> = {
  createWorkflow: (config) => ({ config, steps: [] }),
  createStep: (config) => ({ config }),
  addStep: (workflow, step) => {
    workflow.steps.push(step);
    return workflow;
  },
  commitWorkflow: (workflow) => workflow,
};

describe("Mastra Agent Spec exporter", () => {
  it("round-trips adapter-created Mastra agents losslessly through Agent Spec JSON", () => {
    const exporter = new AgentSpecExporter();
    const agent = createAgent({
      id: "agent-1",
      name: "Support Agent",
      description: "Answers support questions",
      metadata: { team: "support" },
      llmConfig: createOpenAiConfig({
        name: "llm",
        modelId: "gpt-4o-mini",
      }),
      systemPrompt: "You answer support questions.",
      tools: [
        createServerTool({
          name: "lookup",
          description: "Look up account data",
          inputs: [stringProperty({ title: "accountId" })],
        }),
      ],
    });
    const mastraAgent = convertAgentSpecToMastraAgent(agent, {
      runtime: fakeAgentRuntime,
      toolRegistry: {
        lookup: () => ({ ok: true }),
      },
    });

    const exported = exporter.toAgent(mastraAgent);
    const serializer = new AgentSpecSerializer();
    const json = serializer.toJson(exported);
    const reloaded = new AgentSpecDeserializer().fromJson(json) as Agent;

    expect(exported).toEqual(agent);
    expect(reloaded).toEqual(agent);
  });

  it("exports adapter-created Mastra workflows from flow provenance", () => {
    const exporter = new AgentSpecExporter();
    const llmConfig = createOpenAiConfig({
      name: "llm",
      modelId: "gpt-4o-mini",
    });
    const start = createStartNode({ name: "start" });
    const draft = createLlmNode({
      name: "draft",
      llmConfig,
      promptTemplate: "Draft.",
    });
    const tool = createServerTool({ name: "lookup" });
    const lookup = createToolNode({ name: "lookup-step", tool });
    const review = createAgentNode({
      name: "review",
      agent: createAgent({
        name: "reviewer",
        llmConfig,
        systemPrompt: "Review.",
      }),
    });
    const end = createEndNode({ name: "end" });
    const flow = createFlow({
      name: "linear-flow",
      startNode: start,
      nodes: [start, draft, lookup, review, end],
      controlFlowConnections: [
        createControlFlowEdge({ name: "start_to_draft", fromNode: start, toNode: draft }),
        createControlFlowEdge({ name: "draft_to_lookup", fromNode: draft, toNode: lookup }),
        createControlFlowEdge({ name: "lookup_to_review", fromNode: lookup, toNode: review }),
        createControlFlowEdge({ name: "review_to_end", fromNode: review, toNode: end }),
      ],
    });
    const workflow = convertAgentSpecFlowToMastraWorkflow(flow, {
      runtime: fakeWorkflowRuntime,
      llmNodeRegistry: { draft: () => ({}) },
      toolRegistry: { lookup: () => ({}) },
      agentNodeRegistry: { review: () => ({}) },
    });

    expect(exporter.toFlow(workflow)).toEqual(flow);
    expect(exporter.toComponent(workflow)).toEqual(flow);
  });

  it("exports a simple native Mastra-like agent config", () => {
    const exported = new AgentSpecExporter().toAgent({
      id: "weather-agent",
      name: "Weather Agent",
      description: "Answers weather questions",
      metadata: { domain: "weather" },
      instructions: "Use tools for weather.",
      model: "openai/gpt-4o-mini",
      tools: {
        get_weather: {
          id: "get_weather",
          description: "Return weather for a city",
          inputSchema: {
            type: "object",
            properties: {
              city: { type: "string", description: "City name" },
            },
          },
          outputSchema: {
            type: "object",
            properties: {
              condition: { type: "string" },
            },
          },
          execute: () => ({ condition: "foggy" }),
        },
      },
    });

    expect(exported).toMatchObject({
      id: "weather-agent",
      name: "Weather Agent",
      description: "Answers weather questions",
      metadata: { domain: "weather" },
      systemPrompt: "Use tools for weather.",
      llmConfig: {
        componentType: "OpenAiConfig",
        modelId: "gpt-4o-mini",
      },
    });
    expect(exported.tools).toHaveLength(1);
    expect(exported.tools[0]).toMatchObject({
      componentType: "ServerTool",
      name: "get_weather",
      description: "Return weather for a city",
      inputs: [
        {
          title: "city",
          jsonSchema: {
            title: "city",
            type: "string",
            description: "City name",
          },
        },
      ],
      outputs: [
        {
          title: "condition",
          jsonSchema: {
            title: "condition",
            type: "string",
          },
        },
      ],
    });
  });

  it("exports simple native runtime tool descriptors as BuiltinTool", () => {
    const exported = new AgentSpecExporter().toAgent({
      name: "Runtime Tool Agent",
      instructions: "Use runtime tools.",
      model: {
        provider: "openai",
        name: "gpt-4o-mini",
      },
      tools: {
        runtime_search: {
          id: "runtime_search",
          description: "Search using a runtime-provided tool",
          toolType: "runtime_search",
          configuration: {
            source: "framework-runtime",
            limit: 3,
          },
        },
      },
    });

    expect(exported.tools).toEqual([
      createBuiltinTool({
        id: "runtime_search",
        name: "runtime_search",
        description: "Search using a runtime-provided tool",
        toolType: "runtime_search",
        configuration: {
          source: "framework-runtime",
          limit: 3,
        },
      }),
    ]);
  });

  it("uses native model exporters for non-portable model shapes", () => {
    const exported = new AgentSpecExporter({
      nativeModelExporter: () =>
        createOpenAiCompatibleConfig({
          name: "custom",
          modelId: "custom-model",
          url: "http://localhost:8000/v1",
        }),
    }).toAgent({
      name: "Custom Agent",
      instructions: "Use custom model.",
      model: { runtimeOnly: true },
    });

    expect(exported.llmConfig).toMatchObject({
      componentType: "OpenAiCompatibleConfig",
      modelId: "custom-model",
      url: "http://localhost:8000/v1",
    });
  });

  it("serializes exported Mastra configs through the docs-style exporter API", () => {
    const yaml = new AgentSpecExporter().toYaml({
      name: "Weather Agent",
      instructions: "Use weather tools.",
      model: "openai/gpt-4o-mini",
    }) as string;

    expect(yaml).toContain("component_type: Agent");
    expect(yaml).toContain("name: Weather Agent");
  });

  it("refuses to export dynamic runtime functions as agent fields", () => {
    expect(() =>
      new AgentSpecExporter().toAgent({
        name: "Dynamic Agent",
        instructions: () => "dynamic",
        model: "openai/gpt-4o-mini",
      }),
    ).toThrow(UnsupportedMastraExportError);
  });

  it("refuses to export opaque workflows without Agent Spec provenance", () => {
    expect(() =>
      new AgentSpecExporter().toFlow({
        id: "native-workflow",
        steps: [],
      }),
    ).toThrow(UnsupportedMastraExportError);
  });
});
