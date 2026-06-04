/**
 * Version-gated fields configuration.
 *
 * Maps component types to fields that require a minimum agentspec version.
 * When serializing for an older version, these fields are excluded.
 */
import { AgentSpecVersion } from "../versioning.js";
import type { ComponentTypeName } from "../component.js";

/**
 * Maps componentType -> { fieldName -> minimum AgentSpecVersion }
 * Special key "_self" means the entire component requires that version.
 */
export const VERSION_GATED_FIELDS = {
  Agent: {
    toolboxes: AgentSpecVersion.V25_4_2,
    humanInTheLoop: AgentSpecVersion.V25_4_2,
    transforms: AgentSpecVersion.V26_2_0,
  },
  ServerTool: {
    requiresConfirmation: AgentSpecVersion.V25_4_2,
  },
  ClientTool: {
    requiresConfirmation: AgentSpecVersion.V25_4_2,
  },
  RemoteTool: {
    requiresConfirmation: AgentSpecVersion.V25_4_2,
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  MCPTool: {
    requiresConfirmation: AgentSpecVersion.V25_4_2,
  },
  BuiltinTool: {
    _self: AgentSpecVersion.V25_4_2,
  },
  CatchExceptionNode: {
    _self: AgentSpecVersion.V26_2_0,
  },
  ParallelMapNode: {
    _self: AgentSpecVersion.V25_4_2,
  },
  ParallelFlowNode: {
    _self: AgentSpecVersion.V25_4_2,
  },
  Swarm: {
    _self: AgentSpecVersion.V25_4_2,
  },
  ManagerWorkers: {
    _self: AgentSpecVersion.V25_4_2,
  },
  LlmConfig: {
    _self: AgentSpecVersion.V26_2_0,
  },
  GeminiConfig: {
    _self: AgentSpecVersion.V26_2_0,
  },
  OpenAiConfig: {
    apiType: AgentSpecVersion.V25_4_2,
    apiKey: AgentSpecVersion.V25_4_2,
    retryPolicy: AgentSpecVersion.V26_2_0,
  },
  OpenAiCompatibleConfig: {
    apiType: AgentSpecVersion.V25_4_2,
    apiKey: AgentSpecVersion.V25_4_2,
    apiProvider: AgentSpecVersion.V26_2_0,
    keyFile: AgentSpecVersion.V26_2_0,
    certFile: AgentSpecVersion.V26_2_0,
    caFile: AgentSpecVersion.V26_2_0,
    provider: AgentSpecVersion.V26_2_0,
    retryPolicy: AgentSpecVersion.V26_2_0,
  },
  OllamaConfig: {
    keyFile: AgentSpecVersion.V26_2_0,
    certFile: AgentSpecVersion.V26_2_0,
    caFile: AgentSpecVersion.V26_2_0,
    provider: AgentSpecVersion.V26_2_0,
    retryPolicy: AgentSpecVersion.V26_2_0,
  },
  VllmConfig: {
    keyFile: AgentSpecVersion.V26_2_0,
    certFile: AgentSpecVersion.V26_2_0,
    caFile: AgentSpecVersion.V26_2_0,
    provider: AgentSpecVersion.V26_2_0,
    retryPolicy: AgentSpecVersion.V26_2_0,
  },
  OciGenAiConfig: {
    apiType: AgentSpecVersion.V25_4_2,
    conversationStoreId: AgentSpecVersion.V25_4_2,
    retryPolicy: AgentSpecVersion.V26_2_0,
  },
  ApiNode: {
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  SSETransport: {
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  SSEmTLSTransport: {
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  StreamableHTTPTransport: {
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  StreamableHTTPmTLSTransport: {
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  RemoteTransport: {
    sensitiveHeaders: AgentSpecVersion.V25_4_2,
  },
  MCPToolBox: {
    _self: AgentSpecVersion.V25_4_2,
    requiresConfirmation: AgentSpecVersion.V26_2_0,
  },
} satisfies Partial<Record<ComponentTypeName, Record<string, AgentSpecVersion>>>;
