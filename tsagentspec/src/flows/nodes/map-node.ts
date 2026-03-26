/**
 * MapNode - execute a subflow on each element of a given input.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";
import {
  inferMapInputs,
  getDefaultReducers,
  inferMapOutputs,
} from "./map-helpers.js";
import { LazyFlowRef } from "../lazy-schemas.js";

/** Reduction method enum */
export const ReductionMethod = {
  APPEND: "append",
  SUM: "sum",
  AVERAGE: "average",
  MAX: "max",
  MIN: "min",
} as const;

export type ReductionMethod =
  (typeof ReductionMethod)[keyof typeof ReductionMethod];

export const MapNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("MapNode"),
  subflow: LazyFlowRef,
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

export type MapNode = z.infer<typeof MapNodeSchema>;

export function createMapNode(opts: {
  name: string;
  subflow: Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  reducers?: Record<string, ReductionMethod>;
  inputs?: Property[];
  outputs?: Property[];
}): MapNode {
  const reducers = opts.reducers ?? getDefaultReducers(opts.subflow);
  const inputs = opts.inputs ?? inferMapInputs(opts.subflow);
  const outputs = opts.outputs ?? inferMapOutputs(opts.subflow, reducers);

  return Object.freeze(
    MapNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      reducers,
      branches: [DEFAULT_NEXT_BRANCH],
      componentType: "MapNode" as const,
    }),
  );
}
