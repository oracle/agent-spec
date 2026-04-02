/**
 * StartNode - entry point of a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const StartNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("StartNode"),
});

export type StartNode = z.infer<typeof StartNodeSchema>;

export function createStartNode(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): StartNode {
  const inputs = opts.inputs ?? [];
  const outputs = opts.outputs ?? [];
  return Object.freeze(
    StartNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "StartNode" as const,
    }),
  );
}
