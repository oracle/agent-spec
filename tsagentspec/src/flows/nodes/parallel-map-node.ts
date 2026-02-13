/**
 * ParallelMapNode - same as MapNode but executed in parallel.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";
import { ReductionMethod } from "./map-node.js";
import {
  inferMapInputs,
  getDefaultReducers,
  inferMapOutputs,
} from "./map-helpers.js";

export const ParallelMapNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("ParallelMapNode"),
  subflow: z.lazy(() => z.record(z.unknown())),
  reducers: z
    .record(
      z.enum([
        ReductionMethod.APPEND,
        ReductionMethod.SUM,
        ReductionMethod.AVERAGE,
        ReductionMethod.MAX,
        ReductionMethod.MIN,
      ]),
    )
    .optional(),
});

export type ParallelMapNode = z.infer<typeof ParallelMapNodeSchema>;

export function createParallelMapNode(opts: {
  name: string;
  subflow: Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  reducers?: Record<string, ReductionMethod>;
  inputs?: Property[];
  outputs?: Property[];
}): ParallelMapNode {
  const reducers = opts.reducers ?? getDefaultReducers(opts.subflow);
  const inputs = opts.inputs ?? inferMapInputs(opts.subflow);
  const outputs = opts.outputs ?? inferMapOutputs(opts.subflow, reducers);

  return Object.freeze(
    ParallelMapNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      reducers,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "ParallelMapNode" as const,
    }),
  );
}
