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
  MCPToolBox: {
    _self: AgentSpecVersion.V25_4_2,
  },
} satisfies Partial<Record<ComponentTypeName, Record<string, AgentSpecVersion>>>;
