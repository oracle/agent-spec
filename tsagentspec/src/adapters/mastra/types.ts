import type { Agent } from "../../agents/index.js";
import type { Flow, Node } from "../../flows/index.js";
import type { LlmConfig } from "../../llms/index.js";
import type { JsonSchemaValue } from "../../property.js";
import type { ServerTool, Tool } from "../../tools/index.js";
import type {
  InMemoryCollectionDatastore,
  PostgresDatabaseDatastore,
} from "../../datastores/index.js";

export type AgentSpecMastraDatastore =
  | InMemoryCollectionDatastore
  | PostgresDatabaseDatastore;

export type DatastoreSchema = Record<string, Record<string, unknown>>;

export type MastraDatastoreProvider = "in-memory" | "postgres";

export type MastraDatastoreTargetOptions = {
  id?: string;
  schemaName?: string;
  disableInit?: boolean;
};

export type MastraInMemoryStoreConfig = {
  id: string;
};

export type MastraPostgresSslTarget =
  | false
  | {
      mode: "allow" | "prefer" | "require" | "verify-ca" | "verify-full";
      certPath?: string;
      keyPath?: string;
      rootCertPath?: string;
      crlPath?: string;
    };

export type MastraPostgresStoreConfig = {
  id: string;
  connectionString: string;
  user: string;
  password: string;
  ssl: MastraPostgresSslTarget;
  schemaName?: string;
  disableInit?: boolean;
};

type MastraDatastoreTargetBase<
  TProvider extends MastraDatastoreProvider,
  TPackageName extends string,
  TExportName extends string,
  TConfig,
> = {
  provider: TProvider;
  packageName: TPackageName;
  exportName: TExportName;
  id: string;
  datastoreSchema: DatastoreSchema;
  config: TConfig;
};

export type MastraInMemoryDatastoreTarget = MastraDatastoreTargetBase<
  "in-memory",
  "@mastra/core/storage",
  "InMemoryStore",
  MastraInMemoryStoreConfig
>;

export type MastraPostgresDatastoreTarget = MastraDatastoreTargetBase<
  "postgres",
  "@mastra/pg",
  "PostgresStore",
  MastraPostgresStoreConfig
>;

export type MastraDatastoreTarget =
  | MastraInMemoryDatastoreTarget
  | MastraPostgresDatastoreTarget;

export type MastraRuntimeModule = Record<string, unknown>;

export type MastraRuntimeModuleLoader = (
  packageName: string,
) => MastraRuntimeModule;

export type MastraDefaultRuntimeOptions = {
  agentPackageName?: string;
  agentExportName?: string;
  toolsPackageName?: string;
  createToolExportName?: string;
  moduleLoader?: MastraRuntimeModuleLoader;
  agentOptions?: Record<string, unknown>;
  toolOptions?: Record<string, unknown>;
};

export type MastraDefaultWorkflowRuntimeOptions = {
  workflowsPackageName?: string;
  createWorkflowExportName?: string;
  createStepExportName?: string;
  moduleLoader?: MastraRuntimeModuleLoader;
  workflowOptions?: Record<string, unknown>;
  stepOptions?: Record<string, unknown>;
};

export type MastraModelTargetConfig = {
  id: string;
  url?: string;
  apiKey?: string;
  headers?: Record<string, string>;
};

export type MastraModelTarget = string | MastraModelTargetConfig;

export type MastraToolExecutorContext = {
  agentSpecTool: ServerTool;
  agentSpecAgent?: Agent;
  mastraContext?: unknown;
};

export type MastraServerToolExecutor = (
  input: unknown,
  context: MastraToolExecutorContext,
) => unknown | Promise<unknown>;

// Agent Spec carries the tool contract; the Mastra runtime still needs the
// actual executable function. The registry is that handoff point.
export type MastraToolRegistry = Record<string, MastraServerToolExecutor>;

export type MastraToolRuntimeConfig = {
  id: string;
  description: string;
  inputSchema?: JsonSchemaValue;
  outputSchema?: JsonSchemaValue;
  execute?: (input: unknown, mastraContext?: unknown) => unknown | Promise<unknown>;
  requireApproval?: boolean;
  sourceAgentSpecTool: Tool;
};

export type MastraAgentRuntimeConfig<TTool = unknown> = {
  id: string;
  name: string;
  description?: string;
  metadata?: Record<string, unknown>;
  instructions: string;
  model: MastraModelTarget;
  tools: Record<string, TTool>;
  sourceAgentSpecAgent: Agent;
};

// Keep Mastra as an optional runtime dependency. The default binder loads
// Mastra only when Agent Spec is converted through the Mastra adapter.
export type MastraRuntimeAdapter<TAgent = unknown, TTool = unknown> = {
  createAgent: (config: MastraAgentRuntimeConfig<TTool>) => TAgent;
  createTool: (config: MastraToolRuntimeConfig) => TTool;
};

export type MastraModelResolverContext = {
  agent?: Agent;
};

export type MastraModelResolver = (
  llmConfig: LlmConfig,
  context: MastraModelResolverContext,
) => MastraModelTarget;

export type MastraToolResolverContext = {
  agent?: Agent;
  toolRegistry?: MastraToolRegistry;
};

export type MastraToolResolver = (
  tool: Tool,
  context: MastraToolResolverContext,
) => MastraToolRuntimeConfig;

export type AgentSpecToMastraConversionOptions<
  TAgent = unknown,
  TTool = unknown,
> = {
  runtime?: MastraRuntimeAdapter<TAgent, TTool>;
  defaultRuntime?: MastraDefaultRuntimeOptions;
  modelResolver?: MastraModelResolver;
  toolResolver?: MastraToolResolver;
  toolRegistry?: MastraToolRegistry;
};

export type MastraWorkflowStepKind = "llm" | "tool" | "agent";

export type MastraFlowNodeExecutorContext = {
  flow: Flow;
  node: Node;
  mastraContext?: unknown;
};

export type MastraFlowNodeExecutor = (
  input: unknown,
  context: MastraFlowNodeExecutorContext,
) => unknown | Promise<unknown>;

export type MastraFlowNodeExecutorRegistry = Record<
  string,
  MastraFlowNodeExecutor
>;

export type MastraWorkflowStepRuntimeConfig = {
  id: string;
  name: string;
  kind: MastraWorkflowStepKind;
  description?: string;
  inputSchema?: JsonSchemaValue;
  outputSchema?: JsonSchemaValue;
  execute: (input: unknown, mastraContext?: unknown) => unknown | Promise<unknown>;
  sourceAgentSpecNode: Node;
  model?: MastraModelTarget;
  promptTemplate?: string;
  metadata?: Record<string, unknown>;
};

export type MastraWorkflowRuntimeConfig<TStep = unknown> = {
  id: string;
  name: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputSchema?: JsonSchemaValue;
  outputSchema?: JsonSchemaValue;
  steps: TStep[];
  sourceAgentSpecFlow: Flow;
  plan: unknown;
};

// Workflow APIs are still runtime-specific in Mastra, so the converter exposes
// a small port instead of importing workflow classes directly.
export type MastraWorkflowRuntimeAdapter<
  TWorkflow = unknown,
  TStep = unknown,
> = {
  createWorkflow: (config: MastraWorkflowRuntimeConfig<TStep>) => TWorkflow;
  createStep: (config: MastraWorkflowStepRuntimeConfig) => TStep;
  addStep: (workflow: TWorkflow, step: TStep) => TWorkflow;
  commitWorkflow: (workflow: TWorkflow) => TWorkflow;
};

export type AgentSpecFlowToMastraWorkflowConversionOptions<
  TWorkflow = unknown,
  TStep = unknown,
> = {
  runtime?: MastraWorkflowRuntimeAdapter<TWorkflow, TStep>;
  defaultRuntime?: MastraDefaultWorkflowRuntimeOptions;
  modelResolver?: MastraModelResolver;
  toolResolver?: MastraToolResolver;
  toolRegistry?: MastraToolRegistry;
  llmNodeRegistry?: MastraFlowNodeExecutorRegistry;
  agentNodeRegistry?: MastraFlowNodeExecutorRegistry;
};
