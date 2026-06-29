import { describe, expect, it } from "vitest";
import {
  createAgent,
  createAgentNode,
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
} from "../../../src/index.js";
import {
  convertAgentSpecFlowToMastraWorkflow,
  MissingMastraFlowNodeExecutorError,
  type MastraWorkflowRuntimeAdapter,
  type MastraWorkflowRuntimeConfig,
  type MastraWorkflowStepRuntimeConfig,
} from "../../../src/adapters/mastra/index.js";

type FakeStep = {
  config: MastraWorkflowStepRuntimeConfig;
};

type FakeWorkflow = {
  config: MastraWorkflowRuntimeConfig<FakeStep>;
  steps: FakeStep[];
  committed: boolean;
};

const fakeRuntime: MastraWorkflowRuntimeAdapter<FakeWorkflow, FakeStep> = {
  createWorkflow: (config) => ({ config, steps: [], committed: false }),
  createStep: (config) => ({ config }),
  addStep: (workflow, step) => {
    workflow.steps.push(step);
    return workflow;
  },
  commitWorkflow: (workflow) => {
    workflow.committed = true;
    return workflow;
  },
};

const llmConfig = createOpenAiConfig({
  name: "llm",
  modelId: "gpt-4o-mini",
});

const makeFlow = () => {
  const start = createStartNode({
    name: "start",
    inputs: [stringProperty({ title: "topic" })],
  });
  const draft = createLlmNode({
    name: "draft",
    llmConfig,
    promptTemplate: "Draft about {{topic}}.",
  });
  const tool = createServerTool({
    name: "lookup",
    inputs: [stringProperty({ title: "topic" })],
    outputs: [stringProperty({ title: "facts" })],
  });
  const lookup = createToolNode({
    name: "lookup-step",
    tool,
  });
  const agent = createAgent({
    name: "reviewer",
    llmConfig: createOpenAiCompatibleConfig({
      name: "review-llm",
      url: "http://localhost:8000/v1",
      modelId: "review-model",
    }),
    systemPrompt: "Review the draft.",
  });
  const review = createAgentNode({
    name: "review",
    agent,
  });
  const end = createEndNode({
    name: "end",
    outputs: [stringProperty({ title: "answer" })],
  });

  return createFlow({
    name: "support-flow",
    startNode: start,
    nodes: [start, draft, lookup, review, end],
    controlFlowConnections: [
      createControlFlowEdge({ name: "start_to_draft", fromNode: start, toNode: draft }),
      createControlFlowEdge({ name: "draft_to_lookup", fromNode: draft, toNode: lookup }),
      createControlFlowEdge({ name: "lookup_to_review", fromNode: lookup, toNode: review }),
      createControlFlowEdge({ name: "review_to_end", fromNode: review, toNode: end }),
    ],
  });
};

describe("Agent Spec flow to Mastra workflow converter", () => {
  it("uses the default Mastra workflow runtime binder when no runtime is supplied", async () => {
    const flow = makeFlow();
    const createdSteps: Array<Record<string, unknown>> = [];

    const workflow = convertAgentSpecFlowToMastraWorkflow(flow, {
      defaultRuntime: {
        moduleLoader: (packageName) => {
          expect(packageName).toBe("@mastra/core/workflows");
          return {
            createWorkflow: (config: Record<string, unknown>) => ({
              config,
              steps: [] as Array<Record<string, unknown>>,
              committed: false,
              then(step: Record<string, unknown>) {
                this.steps.push(step);
                return this;
              },
              commit() {
                this.committed = true;
                return this;
              },
            }),
            createStep: (config: Record<string, unknown>) => {
              createdSteps.push(config);
              return { config };
            },
          };
        },
      },
      llmNodeRegistry: {
        draft: (input) => ({ draft: input }),
      },
      toolRegistry: {
        lookup: (input) => ({ facts: input }),
      },
      agentNodeRegistry: {
        review: (input) => ({ answer: input }),
      },
    }) as FakeWorkflow;

    expect(workflow.config.name).toBe("support-flow");
    expect(workflow.committed).toBe(true);
    expect(workflow.steps).toHaveLength(3);
    expect(createdSteps.map((step) => step["id"])).toEqual([
      "draft",
      "lookup-step",
      "review",
    ]);
    await expect(
      Promise.resolve(
        (createdSteps[0]?.["execute"] as (input: unknown) => unknown)({
          inputData: { topic: "pricing" },
        }),
      ),
    ).resolves.toEqual({ draft: { topic: "pricing" } });
  });

  it("converts a linear flow into an ordered workflow", async () => {
    const flow = makeFlow();

    const workflow = convertAgentSpecFlowToMastraWorkflow(flow, {
      runtime: fakeRuntime,
      llmNodeRegistry: {
        draft: (input) => ({ draft: input }),
      },
      toolRegistry: {
        lookup: (input) => ({ facts: input }),
      },
      agentNodeRegistry: {
        review: (input) => ({ answer: input }),
      },
    });

    expect(workflow.committed).toBe(true);
    expect(workflow.config.name).toBe("support-flow");
    expect(workflow.config.inputSchema).toMatchObject({
      properties: { topic: { title: "topic", type: "string" } },
    });
    expect(workflow.steps.map((step) => step.config.id)).toEqual([
      "draft",
      "lookup-step",
      "review",
    ]);
    expect(workflow.steps.map((step) => step.config.kind)).toEqual([
      "llm",
      "tool",
      "agent",
    ]);
    expect(workflow.steps[0]?.config.model).toBe("openai/gpt-4o-mini");
    expect(workflow.steps[0]?.config.promptTemplate).toBe("Draft about {{topic}}.");

    await expect(
      Promise.resolve(workflow.steps[0]?.config.execute({ topic: "pricing" })),
    ).resolves.toEqual({ draft: { topic: "pricing" } });
    await expect(
      Promise.resolve(workflow.steps[1]?.config.execute({ topic: "pricing" })),
    ).resolves.toEqual({ facts: { topic: "pricing" } });
    await expect(
      Promise.resolve(workflow.steps[2]?.config.execute({ facts: "ok" })),
    ).resolves.toEqual({ answer: { facts: "ok" } });
  });

  it("requires explicit LLM node executors for deterministic conversion", () => {
    const flow = makeFlow();

    expect(() =>
      convertAgentSpecFlowToMastraWorkflow(flow, {
        runtime: fakeRuntime,
        toolRegistry: { lookup: () => ({}) },
        agentNodeRegistry: { review: () => ({}) },
      }),
    ).toThrow(MissingMastraFlowNodeExecutorError);
  });
});
