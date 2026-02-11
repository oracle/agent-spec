/**
 * Base component schemas and types.
 *
 * All components extend ComponentBaseSchema.
 * Components with inputs/outputs extend ComponentWithIOSchema.
 */
import { z } from "zod";
import { PropertySchema } from "./property.js";

/** Base component schema - all components extend this */
export const ComponentBaseSchema = z.object({
  id: z.string().uuid().default(() => crypto.randomUUID()),
  name: z.string(),
  description: z.string().optional(),
  metadata: z.record(z.unknown()).default({}),
  componentType: z.string(),
});

export type ComponentBase = z.infer<typeof ComponentBaseSchema>;

/** ComponentWithIO adds inputs/outputs */
export const ComponentWithIOSchema = ComponentBaseSchema.extend({
  inputs: z.array(PropertySchema).optional(),
  outputs: z.array(PropertySchema).optional(),
});

export type ComponentWithIO = z.infer<typeof ComponentWithIOSchema>;

/** Abstract type markers for discriminated unions */
export type AbstractComponentType =
  | "Component"
  | "ComponentWithIO"
  | "AgenticComponent"
  | "Node"
  | "Tool"
  | "LlmConfig"
  | "ToolBox"
  | "OciClientConfig"
  | "ClientTransport"
  | "Datastore"
  | "MessageTransform";

/** All concrete component type string literals */
export type ComponentTypeName =
  | "Agent"
  | "Swarm"
  | "ManagerWorkers"
  | "RemoteAgent"
  | "A2AAgent"
  | "SpecializedAgent"
  | "Flow"
  | "StartNode"
  | "EndNode"
  | "LlmNode"
  | "ToolNode"
  | "AgentNode"
  | "FlowNode"
  | "BranchingNode"
  | "MapNode"
  | "ParallelMapNode"
  | "ParallelFlowNode"
  | "ApiNode"
  | "InputMessageNode"
  | "OutputMessageNode"
  | "CatchExceptionNode"
  | "ServerTool"
  | "ClientTool"
  | "RemoteTool"
  | "BuiltinTool"
  | "MCPTool"
  | "MCPToolSpec"
  | "OpenAiCompatibleConfig"
  | "OllamaConfig"
  | "VllmConfig"
  | "OpenAiConfig"
  | "OciGenAiConfig"
  | "ControlFlowEdge"
  | "DataFlowEdge"
  | "MCPToolBox"
  | "StdioTransport"
  | "SSETransport"
  | "SSEmTLSTransport"
  | "StreamableHTTPTransport"
  | "StreamableHTTPmTLSTransport"
  | "RemoteTransport"
  | "OciClientConfigWithApiKey"
  | "OciClientConfigWithInstancePrincipal"
  | "OciClientConfigWithResourcePrincipal"
  | "OciClientConfigWithSecurityToken"
  | "InMemoryCollectionDatastore"
  | "OracleDatabaseDatastore"
  | "PostgresDatabaseDatastore"
  | "TlsOracleDatabaseConnectionConfig"
  | "MTlsOracleDatabaseConnectionConfig"
  | "TlsPostgresDatabaseConnectionConfig"
  | "A2AConnectionConfig"
  | "AgentSpecializationParameters"
  | "MessageSummarizationTransform"
  | "ConversationSummarizationTransform";
