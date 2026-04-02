/**
 * Agent component.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";
import type { Property } from "../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../templating.js";
import { LlmConfigUnion, type LlmConfig } from "../llms/index.js";
import { ToolUnion, ToolBoxUnion, type Tool, type ToolBox } from "../tools/index.js";
import {
  MessageTransformUnion,
  type MessageTransform,
} from "../transforms/index.js";

export const AgentSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("Agent"),
  llmConfig: LlmConfigUnion,
  systemPrompt: z.string(),
  tools: z.array(ToolUnion).default([]),
  toolboxes: z.array(ToolBoxUnion).default([]),
  humanInTheLoop: z.boolean().default(true),
  transforms: z.array(MessageTransformUnion).default([]),
});

export type Agent = z.infer<typeof AgentSchema>;

export function createAgent(opts: {
  name: string;
  llmConfig: LlmConfig;
  systemPrompt: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  tools?: Tool[];
  toolboxes?: ToolBox[];
  humanInTheLoop?: boolean;
  transforms?: MessageTransform[];
  inputs?: Property[];
  outputs?: Property[];
}): Agent {
  const inputs =
    opts.inputs ?? getPlaceholderPropertiesFromJsonObject(opts.systemPrompt);
  const parsed = AgentSchema.parse({
    ...opts,
    inputs,
    outputs: opts.outputs ?? [],
    componentType: "Agent" as const,
  });
  return Object.freeze(parsed);
}
