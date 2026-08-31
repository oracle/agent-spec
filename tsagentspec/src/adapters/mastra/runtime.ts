import { createRequire } from "node:module";

import { MissingMastraRuntimeDependencyError } from "./errors.js";
import type {
  MastraAgentRuntimeConfig,
  MastraDefaultRuntimeOptions,
  MastraDefaultWorkflowRuntimeOptions,
  MastraRuntimeAdapter,
  MastraRuntimeModule,
  MastraRuntimeModuleLoader,
  MastraToolRuntimeConfig,
  MastraWorkflowRuntimeAdapter,
  MastraWorkflowRuntimeConfig,
  MastraWorkflowStepRuntimeConfig,
} from "./types.js";

type MastraAgentConstructor = new (config: Record<string, unknown>) => unknown;

type MastraCreateTool = (config: Record<string, unknown>) => unknown;

type MastraCreateWorkflow = (config: Record<string, unknown>) => unknown;

type MastraCreateStep = (config: Record<string, unknown>) => unknown;

const DEFAULT_AGENT_PACKAGE = "@mastra/core/agent";
const DEFAULT_AGENT_EXPORT = "Agent";
const DEFAULT_TOOLS_PACKAGE = "@mastra/core/tools";
const DEFAULT_CREATE_TOOL_EXPORT = "createTool";
const DEFAULT_WORKFLOWS_PACKAGE = "@mastra/core/workflows";
const DEFAULT_CREATE_WORKFLOW_EXPORT = "createWorkflow";
const DEFAULT_CREATE_STEP_EXPORT = "createStep";

export const createDefaultMastraRuntime = <
  TAgent = unknown,
  TTool = unknown,
>(
  options: MastraDefaultRuntimeOptions = {},
): MastraRuntimeAdapter<TAgent, TTool> => {
  const agentPackageName = options.agentPackageName ?? DEFAULT_AGENT_PACKAGE;
  const agentExportName = options.agentExportName ?? DEFAULT_AGENT_EXPORT;
  const toolsPackageName = options.toolsPackageName ?? DEFAULT_TOOLS_PACKAGE;
  const createToolExportName =
    options.createToolExportName ?? DEFAULT_CREATE_TOOL_EXPORT;
  const moduleLoader = options.moduleLoader ?? loadMastraRuntimeModule;

  const Agent = loadMastraRuntimeExport<MastraAgentConstructor>(
    moduleLoader,
    agentPackageName,
    agentExportName,
  );
  const createTool = loadMastraRuntimeExport<MastraCreateTool>(
    moduleLoader,
    toolsPackageName,
    createToolExportName,
  );

  return {
    createAgent: (config) =>
      attachProvenance(
        new Agent(toMastraAgentConfig(config, options.agentOptions)),
        "sourceAgentSpecAgent",
        config.sourceAgentSpecAgent,
      ) as TAgent,
    createTool: (config) =>
      attachProvenance(
        createTool(toMastraToolConfig(config, options.toolOptions)),
        "sourceAgentSpecTool",
        config.sourceAgentSpecTool,
      ) as TTool,
  };
};

export const createDefaultMastraWorkflowRuntime = <
  TWorkflow = unknown,
  TStep = unknown,
>(
  options: MastraDefaultWorkflowRuntimeOptions = {},
): MastraWorkflowRuntimeAdapter<TWorkflow, TStep> => {
  const workflowsPackageName =
    options.workflowsPackageName ?? DEFAULT_WORKFLOWS_PACKAGE;
  const createWorkflowExportName =
    options.createWorkflowExportName ?? DEFAULT_CREATE_WORKFLOW_EXPORT;
  const createStepExportName =
    options.createStepExportName ?? DEFAULT_CREATE_STEP_EXPORT;
  const moduleLoader = options.moduleLoader ?? loadMastraRuntimeModule;

  const createWorkflow = loadMastraRuntimeExport<MastraCreateWorkflow>(
    moduleLoader,
    workflowsPackageName,
    createWorkflowExportName,
  );
  const createStep = loadMastraRuntimeExport<MastraCreateStep>(
    moduleLoader,
    workflowsPackageName,
    createStepExportName,
  );

  return {
    createWorkflow: (config) =>
      attachProvenance(
        createWorkflow(toMastraWorkflowConfig(config, options.workflowOptions)),
        "sourceAgentSpecFlow",
        config.sourceAgentSpecFlow,
      ) as TWorkflow,
    createStep: (config) =>
      attachProvenance(
        createStep(toMastraWorkflowStepConfig(config, options.stepOptions)),
        "sourceAgentSpecNode",
        config.sourceAgentSpecNode,
      ) as TStep,
    addStep: (workflow, step) =>
      callRuntimeMethod<TWorkflow>(workflow, "then", step),
    commitWorkflow: (workflow) =>
      callOptionalRuntimeMethod<TWorkflow>(workflow, "commit") ?? workflow,
  };
};

export const loadMastraRuntimeModule: MastraRuntimeModuleLoader = (packageName) => {
  const require = createRequire(import.meta.url);
  return require(packageName) as MastraRuntimeModule;
};

export const loadMastraRuntimeExport = <T>(
  moduleLoader: MastraRuntimeModuleLoader,
  packageName: string,
  exportName: string,
): T => {
  let runtimeModule: MastraRuntimeModule;
  try {
    runtimeModule = moduleLoader(packageName);
  } catch {
    throw new MissingMastraRuntimeDependencyError(packageName, exportName);
  }

  const exported =
    runtimeModule[exportName] ??
    (isRecord(runtimeModule["default"])
      ? runtimeModule["default"][exportName]
      : undefined);

  if (typeof exported !== "function") {
    throw new MissingMastraRuntimeDependencyError(packageName, exportName);
  }

  return exported as T;
};

const toMastraAgentConfig = <TTool>(
  config: MastraAgentRuntimeConfig<TTool>,
  agentOptions: Record<string, unknown> | undefined,
): Record<string, unknown> => ({
  ...agentOptions,
  id: config.id,
  name: config.name,
  description: config.description,
  metadata: config.metadata,
  instructions: config.instructions,
  model: config.model,
  tools: config.tools,
});

const toMastraToolConfig = (
  config: MastraToolRuntimeConfig,
  toolOptions: Record<string, unknown> | undefined,
): Record<string, unknown> => ({
  ...toolOptions,
  id: config.id,
  description: config.description,
  inputSchema: config.inputSchema,
  outputSchema: config.outputSchema,
  requireApproval: config.requireApproval,
  execute: config.execute,
});

const toMastraWorkflowConfig = <TStep>(
  config: MastraWorkflowRuntimeConfig<TStep>,
  workflowOptions: Record<string, unknown> | undefined,
): Record<string, unknown> => ({
  ...workflowOptions,
  id: config.id,
  name: config.name,
  description: config.description,
  metadata: config.metadata,
  inputSchema: config.inputSchema,
  outputSchema: config.outputSchema,
});

const toMastraWorkflowStepConfig = (
  config: MastraWorkflowStepRuntimeConfig,
  stepOptions: Record<string, unknown> | undefined,
): Record<string, unknown> => ({
  ...stepOptions,
  id: config.id,
  name: config.name,
  description: config.description,
  inputSchema: config.inputSchema,
  outputSchema: config.outputSchema,
  execute: async (params: unknown) =>
    config.execute(resolveStepInput(params), params),
  metadata: {
    ...config.metadata,
    kind: config.kind,
    ...(config.model ? { model: config.model } : {}),
    ...(config.promptTemplate
      ? { promptTemplate: config.promptTemplate }
      : {}),
  },
});

const resolveStepInput = (params: unknown): unknown =>
  isRecord(params) && "inputData" in params ? params["inputData"] : params;

const callRuntimeMethod = <T>(
  target: T,
  methodName: string,
  ...args: unknown[]
): T => {
  if (!isRecord(target) && typeof target !== "function") {
    throw new MissingMastraRuntimeDependencyError("runtime object", methodName);
  }

  const method = (target as Record<string, unknown>)[methodName];
  if (typeof method !== "function") {
    throw new MissingMastraRuntimeDependencyError("runtime object", methodName);
  }

  return method.apply(target, args) as T;
};

const callOptionalRuntimeMethod = <T>(
  target: T,
  methodName: string,
): T | undefined => {
  if (!isRecord(target) && typeof target !== "function") {
    return undefined;
  }

  const method = (target as Record<string, unknown>)[methodName];
  if (typeof method !== "function") {
    return undefined;
  }

  return method.call(target) as T;
};

const attachProvenance = (
  target: unknown,
  key: string,
  value: unknown,
): unknown => {
  if (!isObjectLike(target)) {
    return target;
  }

  try {
    Object.defineProperty(target, key, {
      value,
      configurable: true,
    });
  } catch {
    return target;
  }

  return target;
};

const isObjectLike = (value: unknown): value is object =>
  (typeof value === "object" && value !== null) || typeof value === "function";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
