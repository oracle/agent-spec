/**
 * OutputMessageNode - append an agent message to the conversation.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { getPlaceholderPropertiesFromJsonObject } from "../../templating.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const OutputMessageNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("OutputMessageNode"),
  message: z.string(),
});

export type OutputMessageNode = z.infer<typeof OutputMessageNodeSchema>;

export function createOutputMessageNode(opts: {
  name: string;
  message: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
}): OutputMessageNode {
  const inputs =
    opts.inputs ?? getPlaceholderPropertiesFromJsonObject(opts.message);

  return Object.freeze(
    OutputMessageNodeSchema.parse({
      ...opts,
      inputs,
      outputs: [],
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "OutputMessageNode" as const,
    }),
  );
}
