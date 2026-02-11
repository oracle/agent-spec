/**
 * Agents barrel exports.
 */
import { z } from "zod";
import { AgentSchema } from "./agent.js";
import { SwarmSchema } from "./swarm.js";
import { ManagerWorkersSchema } from "./manager-workers.js";
import { A2AAgentSchema } from "./a2a-agent.js";
import { SpecializedAgentSchema } from "./specialized-agent.js";

/** Discriminated union of all agentic component types */
export const AgenticComponentUnion = z.discriminatedUnion("componentType", [
  AgentSchema,
  SwarmSchema,
  ManagerWorkersSchema,
  A2AAgentSchema,
  SpecializedAgentSchema,
]);

export type AgenticComponent = z.infer<typeof AgenticComponentUnion>;

export { AgentSchema, createAgent, type Agent } from "./agent.js";
export {
  SwarmSchema,
  createSwarm,
  HandoffMode,
  type Swarm,
} from "./swarm.js";
export {
  ManagerWorkersSchema,
  createManagerWorkers,
  type ManagerWorkers,
} from "./manager-workers.js";
export { RemoteAgentSchema, type RemoteAgent } from "./remote-agent.js";
export {
  A2AAgentSchema,
  A2AConnectionConfigSchema,
  createA2AAgent,
  type A2AAgent,
  type A2AConnectionConfig,
} from "./a2a-agent.js";
export {
  SpecializedAgentSchema,
  AgentSpecializationParametersSchema,
  createSpecializedAgent,
  createAgentSpecializationParameters,
  type SpecializedAgent,
  type AgentSpecializationParameters,
} from "./specialized-agent.js";
