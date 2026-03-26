/**
 * Component registry: maps componentType strings to Zod schemas and factory functions.
 */
import type { z } from "zod";
import type { ComponentBase } from "./component.js";

import { AgentSchema, createAgent } from "./agents/agent.js";
import { SwarmSchema, createSwarm } from "./agents/swarm.js";
import {
  ManagerWorkersSchema,
  createManagerWorkers,
} from "./agents/manager-workers.js";
import { RemoteAgentSchema, createRemoteAgent } from "./agents/remote-agent.js";
import { A2AAgentSchema, A2AConnectionConfigSchema, createA2AAgent, createA2AConnectionConfig } from "./agents/a2a-agent.js";
import {
  SpecializedAgentSchema,
  createSpecializedAgent,
  AgentSpecializationParametersSchema,
  createAgentSpecializationParameters,
} from "./agents/specialized-agent.js";

import { OpenAiCompatibleConfigSchema, createOpenAiCompatibleConfig } from "./llms/openai-compatible-config.js";
import { OllamaConfigSchema, createOllamaConfig } from "./llms/ollama-config.js";
import { VllmConfigSchema, createVllmConfig } from "./llms/vllm-config.js";
import { OpenAiConfigSchema, createOpenAiConfig } from "./llms/openai-config.js";
import { OciGenAiConfigSchema, createOciGenAiConfig } from "./llms/oci-genai-config.js";
import {
  OciClientConfigWithApiKeySchema,
  OciClientConfigWithInstancePrincipalSchema,
  OciClientConfigWithResourcePrincipalSchema,
  OciClientConfigWithSecurityTokenSchema,
  createOciClientConfigWithApiKey,
  createOciClientConfigWithInstancePrincipal,
  createOciClientConfigWithResourcePrincipal,
  createOciClientConfigWithSecurityToken,
} from "./llms/oci-client-config.js";

import { ServerToolSchema, createServerTool } from "./tools/server-tool.js";
import { ClientToolSchema, createClientTool } from "./tools/client-tool.js";
import { RemoteToolSchema, createRemoteTool } from "./tools/remote-tool.js";
import { BuiltinToolSchema, createBuiltinTool } from "./tools/builtin-tool.js";
import { MCPToolBoxSchema, createMCPToolBox } from "./tools/toolbox.js";

import { MCPToolSchema, createMCPTool } from "./mcp/mcp-tool.js";
import { MCPToolSpecSchema, createMCPToolSpec } from "./mcp/mcp-tool.js";

import {
  StdioTransportSchema,
  SSETransportSchema,
  SSEmTLSTransportSchema,
  StreamableHTTPTransportSchema,
  StreamableHTTPmTLSTransportSchema,
  RemoteTransportSchema,
  createStdioTransport,
  createSSETransport,
  createSSEmTLSTransport,
  createStreamableHTTPTransport,
  createStreamableHTTPmTLSTransport,
  createRemoteTransport,
} from "./mcp/client-transport.js";

import { FlowSchema, createFlow } from "./flows/flow.js";

import { StartNodeSchema, createStartNode } from "./flows/nodes/start-node.js";
import { EndNodeSchema, createEndNode } from "./flows/nodes/end-node.js";
import { LlmNodeSchema, createLlmNode } from "./flows/nodes/llm-node.js";
import { ToolNodeSchema, createToolNode } from "./flows/nodes/tool-node.js";
import { AgentNodeSchema, createAgentNode } from "./flows/nodes/agent-node.js";
import { FlowNodeSchema, createFlowNode } from "./flows/nodes/flow-node.js";
import {
  BranchingNodeSchema,
  createBranchingNode,
} from "./flows/nodes/branching-node.js";
import { MapNodeSchema, createMapNode } from "./flows/nodes/map-node.js";
import {
  ParallelMapNodeSchema,
  createParallelMapNode,
} from "./flows/nodes/parallel-map-node.js";
import {
  ParallelFlowNodeSchema,
  createParallelFlowNode,
} from "./flows/nodes/parallel-flow-node.js";
import { ApiNodeSchema, createApiNode } from "./flows/nodes/api-node.js";
import {
  InputMessageNodeSchema,
  createInputMessageNode,
} from "./flows/nodes/input-message-node.js";
import {
  OutputMessageNodeSchema,
  createOutputMessageNode,
} from "./flows/nodes/output-message-node.js";
import {
  CatchExceptionNodeSchema,
  createCatchExceptionNode,
} from "./flows/nodes/catch-exception-node.js";

import {
  ControlFlowEdgeSchema,
  createControlFlowEdge,
} from "./flows/edges/control-flow-edge.js";
import {
  DataFlowEdgeSchema,
  createDataFlowEdge,
} from "./flows/edges/data-flow-edge.js";

import {
  InMemoryCollectionDatastoreSchema,
  createInMemoryCollectionDatastore,
} from "./datastores/datastore.js";
import {
  OracleDatabaseDatastoreSchema,
  TlsOracleDatabaseConnectionConfigSchema,
  MTlsOracleDatabaseConnectionConfigSchema,
  createOracleDatabaseDatastore,
  createTlsOracleDatabaseConnectionConfig,
  createMTlsOracleDatabaseConnectionConfig,
} from "./datastores/oracle-datastore.js";
import {
  PostgresDatabaseDatastoreSchema,
  TlsPostgresDatabaseConnectionConfigSchema,
  createPostgresDatabaseDatastore,
  createTlsPostgresDatabaseConnectionConfig,
} from "./datastores/postgres-datastore.js";

import {
  MessageSummarizationTransformSchema,
  ConversationSummarizationTransformSchema,
  createMessageSummarizationTransform,
  createConversationSummarizationTransform,
} from "./transforms/message-transform.js";

/** Maps componentType string -> Zod schema for that type */
export const BUILTIN_SCHEMA_MAP: Record<string, z.ZodType> = {
  Agent: AgentSchema,
  Swarm: SwarmSchema,
  ManagerWorkers: ManagerWorkersSchema,
  RemoteAgent: RemoteAgentSchema,
  A2AAgent: A2AAgentSchema,
  A2AConnectionConfig: A2AConnectionConfigSchema,
  SpecializedAgent: SpecializedAgentSchema,
  AgentSpecializationParameters: AgentSpecializationParametersSchema,

  OpenAiCompatibleConfig: OpenAiCompatibleConfigSchema,
  OllamaConfig: OllamaConfigSchema,
  VllmConfig: VllmConfigSchema,
  OpenAiConfig: OpenAiConfigSchema,
  OciGenAiConfig: OciGenAiConfigSchema,
  OciClientConfigWithApiKey: OciClientConfigWithApiKeySchema,
  OciClientConfigWithInstancePrincipal: OciClientConfigWithInstancePrincipalSchema,
  OciClientConfigWithResourcePrincipal: OciClientConfigWithResourcePrincipalSchema,
  OciClientConfigWithSecurityToken: OciClientConfigWithSecurityTokenSchema,

  ServerTool: ServerToolSchema,
  ClientTool: ClientToolSchema,
  RemoteTool: RemoteToolSchema,
  BuiltinTool: BuiltinToolSchema,
  MCPTool: MCPToolSchema,
  MCPToolSpec: MCPToolSpecSchema,
  MCPToolBox: MCPToolBoxSchema,

  StdioTransport: StdioTransportSchema,
  SSETransport: SSETransportSchema,
  SSEmTLSTransport: SSEmTLSTransportSchema,
  StreamableHTTPTransport: StreamableHTTPTransportSchema,
  StreamableHTTPmTLSTransport: StreamableHTTPmTLSTransportSchema,
  RemoteTransport: RemoteTransportSchema,

  Flow: FlowSchema,
  StartNode: StartNodeSchema,
  EndNode: EndNodeSchema,
  LlmNode: LlmNodeSchema,
  ToolNode: ToolNodeSchema,
  AgentNode: AgentNodeSchema,
  FlowNode: FlowNodeSchema,
  BranchingNode: BranchingNodeSchema,
  MapNode: MapNodeSchema,
  ParallelMapNode: ParallelMapNodeSchema,
  ParallelFlowNode: ParallelFlowNodeSchema,
  ApiNode: ApiNodeSchema,
  InputMessageNode: InputMessageNodeSchema,
  OutputMessageNode: OutputMessageNodeSchema,
  CatchExceptionNode: CatchExceptionNodeSchema,

  ControlFlowEdge: ControlFlowEdgeSchema,
  DataFlowEdge: DataFlowEdgeSchema,

  InMemoryCollectionDatastore: InMemoryCollectionDatastoreSchema,
  OracleDatabaseDatastore: OracleDatabaseDatastoreSchema,
  TlsOracleDatabaseConnectionConfig: TlsOracleDatabaseConnectionConfigSchema,
  MTlsOracleDatabaseConnectionConfig: MTlsOracleDatabaseConnectionConfigSchema,
  PostgresDatabaseDatastore: PostgresDatabaseDatastoreSchema,
  TlsPostgresDatabaseConnectionConfig: TlsPostgresDatabaseConnectionConfigSchema,

  MessageSummarizationTransform: MessageSummarizationTransformSchema,
  ConversationSummarizationTransform: ConversationSummarizationTransformSchema,
};

// `any` is required here: factory functions have heterogeneous signatures (each expects
// different required fields) so no single concrete type can represent all of them.
// The registry is only called from deserialization plugins which pass pre-validated dicts.
type FactoryFn = (opts: any) => ComponentBase;

/** Maps componentType string -> factory function */
export const BUILTIN_FACTORY_MAP: Record<string, FactoryFn> = {
  Agent: createAgent,
  Swarm: createSwarm,
  ManagerWorkers: createManagerWorkers,
  RemoteAgent: createRemoteAgent,
  A2AAgent: createA2AAgent,
  A2AConnectionConfig: createA2AConnectionConfig,
  SpecializedAgent: createSpecializedAgent,
  AgentSpecializationParameters: createAgentSpecializationParameters,

  OpenAiCompatibleConfig: createOpenAiCompatibleConfig,
  OllamaConfig: createOllamaConfig,
  VllmConfig: createVllmConfig,
  OpenAiConfig: createOpenAiConfig,
  OciGenAiConfig: createOciGenAiConfig,
  OciClientConfigWithApiKey: createOciClientConfigWithApiKey,
  OciClientConfigWithInstancePrincipal: createOciClientConfigWithInstancePrincipal,
  OciClientConfigWithResourcePrincipal: createOciClientConfigWithResourcePrincipal,
  OciClientConfigWithSecurityToken: createOciClientConfigWithSecurityToken,

  ServerTool: createServerTool,
  ClientTool: createClientTool,
  RemoteTool: createRemoteTool,
  BuiltinTool: createBuiltinTool,
  MCPTool: createMCPTool,
  MCPToolSpec: createMCPToolSpec,
  MCPToolBox: createMCPToolBox,

  StdioTransport: createStdioTransport,
  SSETransport: createSSETransport,
  SSEmTLSTransport: createSSEmTLSTransport,
  StreamableHTTPTransport: createStreamableHTTPTransport,
  StreamableHTTPmTLSTransport: createStreamableHTTPmTLSTransport,
  RemoteTransport: createRemoteTransport,

  Flow: createFlow,
  StartNode: createStartNode,
  EndNode: createEndNode,
  LlmNode: createLlmNode,
  ToolNode: createToolNode,
  AgentNode: createAgentNode,
  FlowNode: createFlowNode,
  BranchingNode: createBranchingNode,
  MapNode: createMapNode,
  ParallelMapNode: createParallelMapNode,
  ParallelFlowNode: createParallelFlowNode,
  ApiNode: createApiNode,
  InputMessageNode: createInputMessageNode,
  OutputMessageNode: createOutputMessageNode,
  CatchExceptionNode: createCatchExceptionNode,

  ControlFlowEdge: createControlFlowEdge,
  DataFlowEdge: createDataFlowEdge,

  InMemoryCollectionDatastore: createInMemoryCollectionDatastore,
  OracleDatabaseDatastore: createOracleDatabaseDatastore,
  TlsOracleDatabaseConnectionConfig: createTlsOracleDatabaseConnectionConfig,
  MTlsOracleDatabaseConnectionConfig: createMTlsOracleDatabaseConnectionConfig,
  PostgresDatabaseDatastore: createPostgresDatabaseDatastore,
  TlsPostgresDatabaseConnectionConfig: createTlsPostgresDatabaseConnectionConfig,

  MessageSummarizationTransform: createMessageSummarizationTransform,
  ConversationSummarizationTransform: createConversationSummarizationTransform,
};

/** Get the Zod schema for a built-in component type */
export function getSchemaForComponentType(
  componentType: string,
): z.ZodType | undefined {
  return BUILTIN_SCHEMA_MAP[componentType];
}

/** Check if a component type is a built-in type */
export function isBuiltinComponentType(componentType: string): boolean {
  return componentType in BUILTIN_SCHEMA_MAP;
}

/** Get the factory function for a built-in component type */
export function getComponentFactory(
  componentType: string,
): FactoryFn | undefined {
  return BUILTIN_FACTORY_MAP[componentType];
}
