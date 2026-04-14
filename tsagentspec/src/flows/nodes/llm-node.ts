/**
 * LlmNode - invoke an LLM with a prompt template.
 */
import { z } from "zod";
import { stringProperty, type Property } from "../../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../../templating.js";
import { LlmConfigUnion, type LlmConfig } from "../../llms/index.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const DEFAULT_LLM_OUTPUT = "generated_text";

export const LlmNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("LlmNode"),
  llmConfig: LlmConfigUnion,
  promptTemplate: z.string(),
});

export type LlmNode = z.infer<typeof LlmNodeSchema>;

export function createLlmNode(opts: {
  name: string;
  llmConfig: LlmConfig;
  promptTemplate: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): LlmNode {
  const inputs =
    opts.inputs ??
    getPlaceholderPropertiesFromJsonObject(opts.promptTemplate);

  const outputs = opts.outputs ?? [
    stringProperty({ title: DEFAULT_LLM_OUTPUT }),
  ];

  return Object.freeze(
    LlmNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "LlmNode" as const,
    }),
  );
}
