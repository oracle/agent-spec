/**
 * AgentNode - execute an agentic component in a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { AgenticComponentUnion } from "../../agents/index.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const AgentNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("AgentNode"),
  agent: AgenticComponentUnion,
});

export type AgentNode = z.infer<typeof AgentNodeSchema>;

export function createAgentNode(opts: {
  name: string;
  agent: z.infer<typeof AgenticComponentUnion>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
  branches?: string[];
}): AgentNode {
  const inputs = opts.inputs ?? (opts.agent as Record<string, unknown>)["inputs"] as Property[] ?? [];
  const outputs = opts.outputs ?? (opts.agent as Record<string, unknown>)["outputs"] as Property[] ?? [];
  const branches = opts.branches ?? [DEFAULT_NEXT_BRANCH];
  return Object.freeze(
    AgentNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches,
      componentType: "AgentNode" as const,
    }),
  );
}
