/**
 * ParallelFlowNode - execute multiple subflows in parallel.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { deduplicatePropertiesByTitleAndType } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";
import { LazyFlowRef } from "../lazy-schemas.js";

export const ParallelFlowNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("ParallelFlowNode"),
  subflows: z.array(LazyFlowRef).default([]),
});

export type ParallelFlowNode = z.infer<typeof ParallelFlowNodeSchema>;

export function createParallelFlowNode(opts: {
  name: string;
  subflows?: Record<string, unknown>[];
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): ParallelFlowNode {
  const subflows = opts.subflows ?? [];

  let inputs: Property[];
  if (opts.inputs !== undefined) {
    inputs = opts.inputs;
  } else {
    const allInputs: Property[] = [];
    for (const subflow of subflows) {
      const sfInputs =
        (subflow["inputs"] as Property[] | undefined) ?? [];
      allInputs.push(...sfInputs);
    }
    inputs = deduplicatePropertiesByTitleAndType(allInputs);
  }

  let outputs: Property[];
  if (opts.outputs !== undefined) {
    outputs = opts.outputs;
  } else {
    const allOutputs: Property[] = [];
    for (const subflow of subflows) {
      const sfOutputs =
        (subflow["outputs"] as Property[] | undefined) ?? [];
      allOutputs.push(...sfOutputs);
    }
    outputs = allOutputs;
  }

  return Object.freeze(
    ParallelFlowNodeSchema.parse({
      ...opts,
      subflows,
      inputs,
      outputs,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "ParallelFlowNode" as const,
    }),
  );
}
