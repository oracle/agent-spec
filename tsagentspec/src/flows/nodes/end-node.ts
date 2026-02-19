/**
 * EndNode - exit point of a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const EndNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("EndNode"),
  branchName: z.string().default(DEFAULT_NEXT_BRANCH),
});

export type EndNode = z.infer<typeof EndNodeSchema>;

export function createEndNode(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  branchName?: string;
  inputs?: Property[];
  outputs?: Property[];
}): EndNode {
  const inputs = opts.inputs ?? [];
  const outputs = opts.outputs ?? [];
  return Object.freeze(
    EndNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches: [],
      componentType: "EndNode" as const,
    }),
  );
}
