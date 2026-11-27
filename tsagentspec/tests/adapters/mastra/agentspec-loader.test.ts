import { describe, expect, it } from "vitest";
import {
  AgentSpecSerializer,
  createAgent,
  createOpenAiConfig,
  createOpenAiCompatibleConfig,
  createServerTool,
} from "../../../src/index.js";
import {
  InvalidMastraAgentSpecError,
  AgentSpecLoader,
  MissingMastraRuntimeDependencyError,
  type MastraAgentRuntimeConfig,
  type MastraRuntimeAdapter,
  type MastraToolRuntimeConfig,
} from "../../../src/adapters/mastra/index.js";

type FakeTool = {
  kind: "tool";
  config: MastraToolRuntimeConfig;
};

type FakeAgent = {
  kind: "agent";
  config: MastraAgentRuntimeConfig<FakeTool>;
};

const fakeRuntime: MastraRuntimeAdapter<FakeAgent, FakeTool> = {
  createAgent: (config) => ({ kind: "agent", config }),
  createTool: (config) => ({ kind: "tool", config }),
};

class DefaultRuntimeAgent {
  readonly config: Record<string, unknown>;

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }
}

describe("AgentSpecLoader", () => {
  it("loads with the default Mastra runtime binder when no runtime is supplied", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "Default Runtime Agent",
      llmConfig: createOpenAiCompatibleConfig({
        name: "llm",
        modelId: "custom-model",
        url: "http://localhost:8000/v1",
      }),
      systemPrompt: "Use the lookup tool.",
      tools: [
        createServerTool({
          id: "lookup-tool",
          name: "lookup",
          description: "Look up a value",
        }),
      ],
    });
    const yaml = serializer.toYaml(agent) as string;
    const createdTools: Array<Record<string, unknown>> = [];
    const loader = new AgentSpecLoader({
      defaultRuntime: {
        moduleLoader: (packageName) => {
          if (packageName === "@mastra/core/agent") {
            return { Agent: DefaultRuntimeAgent };
          }
          if (packageName === "@mastra/core/tools") {
            return {
              createTool: (config: Record<string, unknown>) => {
                createdTools.push(config);
                return { config };
              },
            };
          }
          return {};
        },
        agentOptions: {
          memory: "memory-instance",
        },
      },
      toolRegistry: {
        lookup: () => "value",
      },
    });

    const converted = loader.loadYaml(yaml) as DefaultRuntimeAgent & {
      sourceAgentSpecAgent?: unknown;
    };

    expect(converted).toBeInstanceOf(DefaultRuntimeAgent);
    expect(converted.config).toMatchObject({
      name: "Default Runtime Agent",
      instructions: "Use the lookup tool.",
      memory: "memory-instance",
      model: {
        id: "openai-compatible/custom-model",
        url: "http://localhost:8000/v1",
      },
    });
    expect(converted.config["tools"]).toHaveProperty("lookup");
    expect(converted.sourceAgentSpecAgent).toEqual(agent);
    expect(createdTools[0]).toMatchObject({
      id: "lookup",
      description: "Look up a value",
    });
    expect(createdTools[0]?.["execute"]).toBeTypeOf("function");
  });

  it("fails clearly when the default Mastra runtime dependency is unavailable", () => {
    const agent = createAgent({
      name: "Missing Runtime Agent",
      llmConfig: createOpenAiCompatibleConfig({
        name: "llm",
        modelId: "custom-model",
        url: "http://localhost:8000/v1",
      }),
      systemPrompt: "You answer.",
    });

    expect(
      () =>
        new AgentSpecLoader({
          defaultRuntime: {
            moduleLoader: () => {
              throw new Error("missing module");
            },
          },
        }).loadComponent(agent),
    ).toThrow(MissingMastraRuntimeDependencyError);
  });

  it("loads a JSON Agent Spec into a Mastra runtime agent", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      id: "agent-1",
      name: "JSON Agent",
      llmConfig: createOpenAiCompatibleConfig({
        name: "llm",
        modelId: "custom-model",
        url: "http://localhost:8000/v1",
      }),
      systemPrompt: "You answer from JSON.",
    });
    const json = serializer.toJson(agent) as string;
    const loader = new AgentSpecLoader({ runtime: fakeRuntime });

    const converted = loader.loadJson(json);

    expect(converted.config).toMatchObject({
      id: "agent-1",
      name: "JSON Agent",
      instructions: "You answer from JSON.",
      model: {
        id: "openai-compatible/custom-model",
        url: "http://localhost:8000/v1",
      },
      tools: {},
    });
  });

  it("loads a YAML Agent Spec into a Mastra runtime agent", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "YAML Agent",
      llmConfig: createOpenAiCompatibleConfig({
        name: "llm",
        modelId: "custom-model",
        url: "http://localhost:8000/v1",
      }),
      systemPrompt: "You answer from YAML.",
    });
    const yaml = serializer.toYaml(agent) as string;
    const loader = new AgentSpecLoader({ runtime: fakeRuntime });

    const converted = loader.loadYaml(yaml);

    expect(converted.config.name).toBe("YAML Agent");
    expect(converted.config.instructions).toBe("You answer from YAML.");
  });

  it("loads disaggregated referenced components for a later main load", () => {
    const serializer = new AgentSpecSerializer();
    const llmConfig = createOpenAiConfig({
      id: "shared-llm",
      name: "llm",
      modelId: "gpt-4o-mini",
    });
    const agent = createAgent({
      name: "Disaggregated Agent",
      llmConfig,
      systemPrompt: "Use the shared model.",
    });
    const [mainYaml, referencedYaml] = serializer.toYaml(agent, {
      disaggregatedComponents: [llmConfig],
      exportDisaggregatedComponents: true,
    }) as [string, string];
    const loader = new AgentSpecLoader({ runtime: fakeRuntime });

    const registry = loader.loadYaml(referencedYaml, {
      importOnlyReferencedComponents: true,
    });
    const converted = loader.loadYaml(mainYaml, {
      componentsRegistry: registry,
    });

    expect(registry.get("shared-llm")).toEqual(llmConfig);
    expect(converted.config).toMatchObject({
      name: "Disaggregated Agent",
      model: "openai/gpt-4o-mini",
    });
  });

  it("loads from an already-created Agent component", () => {
    const agent = createAgent({
      name: "Component Agent",
      llmConfig: createOpenAiCompatibleConfig({
        name: "llm",
        modelId: "custom-model",
        url: "http://localhost:8000/v1",
      }),
      systemPrompt: "You answer from a component.",
    });
    const loader = new AgentSpecLoader({ runtime: fakeRuntime });

    const converted = loader.loadComponent(agent);

    expect(converted.config.sourceAgentSpecAgent).toEqual(agent);
  });

  it("fails when the loaded root component is not an Agent", () => {
    const serializer = new AgentSpecSerializer();
    const json = serializer.toJson(createServerTool({ name: "lookup" })) as string;
    const loader = new AgentSpecLoader({ runtime: fakeRuntime });

    expect(() => loader.loadJson(json)).toThrow(InvalidMastraAgentSpecError);
  });
});
