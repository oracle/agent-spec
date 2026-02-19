/**
 * FlowNode - execute a subflow as part of a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema } from "../node.js";
import { getEndNodeBranches } from "./node-helpers.js";
import { LazyFlowRef } from "../lazy-schemas.js";

export const FlowNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("FlowNode"),
  subflow: LazyFlowRef,
});

export type FlowNode = z.infer<typeof FlowNodeSchema>;

export function createFlowNode(opts: {
  name: string;
  subflow: Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): FlowNode {
  const subflow = opts.subflow;
  const inputs =
    opts.inputs ?? (subflow["inputs"] as Property[] | undefined) ?? [];
  const outputs =
    opts.outputs ?? (subflow["outputs"] as Property[] | undefined) ?? [];
  const branches = getEndNodeBranches(subflow);

  return Object.freeze(
    FlowNodeSchema.parse({
      ...opts,
      inputs,
      outputs,
      branches,
      componentType: "FlowNode" as const,
    }),
  );
}
