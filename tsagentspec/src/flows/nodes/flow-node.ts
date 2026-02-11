/**
 * FlowNode - execute a subflow as part of a flow.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema, DEFAULT_NEXT_BRANCH } from "../node.js";

export const FlowNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("FlowNode"),
  subflow: z.lazy(() => z.record(z.unknown())),
});

export type FlowNode = z.infer<typeof FlowNodeSchema>;

function getEndNodeBranches(subflow: Record<string, unknown>): string[] {
  const nodes = subflow["nodes"] as Record<string, unknown>[] | undefined;
  if (!nodes) return [DEFAULT_NEXT_BRANCH];
  const branches = new Set<string>();
  for (const node of nodes) {
    if (node["componentType"] === "EndNode") {
      const branchName =
        (node["branchName"] as string) ?? DEFAULT_NEXT_BRANCH;
      branches.add(branchName);
    }
  }
  return branches.size > 0 ? [...branches].sort() : [DEFAULT_NEXT_BRANCH];
}

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
