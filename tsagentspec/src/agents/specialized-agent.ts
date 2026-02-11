/**
 * SpecializedAgent and AgentSpecializationParameters.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";
import type { Property } from "../property.js";
import { deduplicatePropertiesByTitleAndType } from "../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../templating.js";
import { ToolUnion, type Tool } from "../tools/index.js";
import { AgentSchema, type Agent } from "./agent.js";

export const AgentSpecializationParametersSchema =
  ComponentWithIOSchema.extend({
    componentType: z.literal("AgentSpecializationParameters"),
    additionalInstructions: z.string().optional(),
    additionalTools: z.array(ToolUnion).optional(),
    humanInTheLoop: z.boolean().optional(),
  });

export type AgentSpecializationParameters = z.infer<
  typeof AgentSpecializationParametersSchema
>;

export const SpecializedAgentSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("SpecializedAgent"),
  agent: AgentSchema,
  agentSpecializationParameters: AgentSpecializationParametersSchema,
});

export type SpecializedAgent = z.infer<typeof SpecializedAgentSchema>;

export function createAgentSpecializationParameters(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  additionalInstructions?: string;
  additionalTools?: Tool[];
  humanInTheLoop?: boolean;
  inputs?: Property[];
  outputs?: Property[];
}): AgentSpecializationParameters {
  const inputs =
    opts.inputs ??
    getPlaceholderPropertiesFromJsonObject(
      opts.additionalInstructions ?? "",
    );
  return Object.freeze(
    AgentSpecializationParametersSchema.parse({
      ...opts,
      inputs,
      outputs: opts.outputs ?? [],
      componentType: "AgentSpecializationParameters" as const,
    }),
  );
}

export function createSpecializedAgent(opts: {
  name: string;
  agent: Agent;
  agentSpecializationParameters: AgentSpecializationParameters;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): SpecializedAgent {
  const agentInputs = opts.agent.inputs ?? [];
  const specInputs = opts.agentSpecializationParameters.inputs ?? [];
  const inputs =
    opts.inputs ??
    deduplicatePropertiesByTitleAndType([...agentInputs, ...specInputs]);

  const agentOutputs = opts.agent.outputs ?? [];
  const specOutputs = opts.agentSpecializationParameters.outputs ?? [];
  const outputs =
    opts.outputs ??
    deduplicatePropertiesByTitleAndType([...agentOutputs, ...specOutputs]);

  return Object.freeze(
    SpecializedAgentSchema.parse({
      ...opts,
      inputs,
      outputs,
      componentType: "SpecializedAgent" as const,
    }),
  );
}
