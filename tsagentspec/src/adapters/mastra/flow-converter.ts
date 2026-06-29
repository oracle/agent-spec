import type { Flow, Node } from "../../flows/index.js";
import {
  MissingMastraFlowNodeExecutorError,
  UnsupportedMastraFlowNodeError,
} from "./errors.js";
import { createDefaultMastraWorkflowRuntime } from "./runtime.js";
import { defaultMastraModelResolver } from "./model.js";
import type {
  AgentSpecFlowToMastraWorkflowConversionOptions,
  MastraFlowNodeExecutor,
  MastraFlowNodeExecutorRegistry,
  MastraModelResolver,
  MastraToolResolver,
  MastraWorkflowRuntimeAdapter,
  MastraWorkflowStepRuntimeConfig,
} from "./types.js";
import { defaultMastraToolResolver } from "./tool.js";
import { propertiesToMastraJsonSchema } from "./tool.js";
import { planLinearMastraFlow } from "./flow-planner.js";

export class AgentSpecFlowToMastraWorkflowConverter<
  TWorkflow = unknown,
  TStep = unknown,
> {
  private readonly runtime: MastraWorkflowRuntimeAdapter<TWorkflow, TStep>;
  private readonly modelResolver: MastraModelResolver;
  private readonly toolResolver: MastraToolResolver;
  private readonly options: AgentSpecFlowToMastraWorkflowConversionOptions<
    TWorkflow,
    TStep
  >;

  constructor(
    options: AgentSpecFlowToMastraWorkflowConversionOptions<TWorkflow, TStep>,
  ) {
    this.runtime =
      options.runtime ??
      createDefaultMastraWorkflowRuntime<TWorkflow, TStep>(
        options.defaultRuntime,
      );
    this.modelResolver = options.modelResolver ?? defaultMastraModelResolver;
    this.toolResolver = options.toolResolver ?? defaultMastraToolResolver;
    this.options = options;
  }

  convert(flow: Flow): TWorkflow {
    const plan = planLinearMastraFlow(flow);
    let workflow = this.runtime.createWorkflow({
      id: flow.id,
      name: flow.name,
      ...(flow.description ? { description: flow.description } : {}),
      metadata: flow.metadata,
      inputSchema: propertiesToMastraJsonSchema(flow.inputs),
      outputSchema: propertiesToMastraJsonSchema(flow.outputs),
      steps: [],
      sourceAgentSpecFlow: flow,
      plan,
    });

    for (const node of plan.executableNodes) {
      const step = this.runtime.createStep(this.resolveStep(flow, node));
      workflow = this.runtime.addStep(workflow, step);
    }

    return this.runtime.commitWorkflow(workflow);
  }

  private resolveStep(
    flow: Flow,
    node: (ReturnType<typeof planLinearMastraFlow>)["executableNodes"][number],
  ): MastraWorkflowStepRuntimeConfig {
    if (node.componentType === "LlmNode") {
      // Prompt execution is runtime behavior, not static Agent Spec data. The
      // registry lets callers bind their own Mastra step implementation.
      const executor = resolveNodeExecutor(this.options.llmNodeRegistry, node);
      const model = this.modelResolver(node.llmConfig, {});
      return {
        id: node.name,
        name: node.name,
        kind: "llm",
        ...(node.description ? { description: node.description } : {}),
        inputSchema: propertiesToMastraJsonSchema(node.inputs),
        outputSchema: propertiesToMastraJsonSchema(node.outputs),
        execute: wrapNodeExecutor(flow, node, executor),
        sourceAgentSpecNode: node,
        model,
        promptTemplate: node.promptTemplate,
        metadata: node.metadata,
      };
    }

    if (node.componentType === "ToolNode") {
      // ToolNode reuses the same tool resolver as agents so server-tool behavior
      // stays consistent across agent and workflow conversion.
      const tool = this.toolResolver(node.tool, {
        toolRegistry: this.options.toolRegistry,
      });
      return {
        id: node.name,
        name: node.name,
        kind: "tool",
        ...(node.description ? { description: node.description } : {}),
        inputSchema: propertiesToMastraJsonSchema(node.inputs),
        outputSchema: propertiesToMastraJsonSchema(node.outputs),
        execute: (input, mastraContext) => tool.execute?.(input, mastraContext),
        sourceAgentSpecNode: node,
        metadata: node.metadata,
      };
    }

    if (node.componentType === "AgentNode") {
      // Agent handoff can mean different things in different Mastra apps, so the
      // caller supplies the executable behavior explicitly.
      const executor = resolveNodeExecutor(this.options.agentNodeRegistry, node);
      return {
        id: node.name,
        name: node.name,
        kind: "agent",
        ...(node.description ? { description: node.description } : {}),
        inputSchema: propertiesToMastraJsonSchema(node.inputs),
        outputSchema: propertiesToMastraJsonSchema(node.outputs),
        execute: wrapNodeExecutor(flow, node, executor),
        sourceAgentSpecNode: node,
        metadata: node.metadata,
      };
    }

    throw new UnsupportedMastraFlowNodeError("unknown");
  }
}

export const convertAgentSpecFlowToMastraWorkflow = <
  TWorkflow = unknown,
  TStep = unknown,
>(
  flow: Flow,
  options: AgentSpecFlowToMastraWorkflowConversionOptions<TWorkflow, TStep>,
): TWorkflow => new AgentSpecFlowToMastraWorkflowConverter(options).convert(flow);

const resolveNodeExecutor = (
  registry: MastraFlowNodeExecutorRegistry | undefined,
  node: Node,
): MastraFlowNodeExecutor => {
  const executor = registry?.[node.name] ?? registry?.[node.id];
  if (!executor) {
    throw new MissingMastraFlowNodeExecutorError(node.name);
  }
  return executor;
};

const wrapNodeExecutor = (
  flow: Flow,
  node: Node,
  executor: MastraFlowNodeExecutor,
): MastraWorkflowStepRuntimeConfig["execute"] =>
  (input, mastraContext) =>
    executor(input, {
      flow,
      node,
      mastraContext,
    });
