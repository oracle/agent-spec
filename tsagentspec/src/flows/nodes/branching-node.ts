/**
 * BranchingNode - select next node based on a mapping.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema } from "../node.js";

export const DEFAULT_BRANCH = "default";
export const DEFAULT_INPUT = "branching_mapping_key";

export const BranchingNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("BranchingNode"),
  mapping: z.record(z.string()),
});

export type BranchingNode = z.infer<typeof BranchingNodeSchema>;

export function createBranchingNode(opts: {
  name: string;
  mapping: Record<string, string>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
}): BranchingNode {
  const mappingValues = new Set(Object.values(opts.mapping));
  const branches = [...new Set([DEFAULT_BRANCH, ...mappingValues])].sort();

  const inputTitle =
    opts.inputs && opts.inputs.length > 0
      ? opts.inputs[0]!.title
      : DEFAULT_INPUT;

  const inputs: Property[] = opts.inputs ?? [
    {
      jsonSchema: {
        title: inputTitle,
        type: "string",
        description: "Next branch name in the flow",
      },
      title: inputTitle,
      description: "Next branch name in the flow",
      default: undefined,
      type: "string",
    },
  ];

  return Object.freeze(
    BranchingNodeSchema.parse({
      ...opts,
      inputs,
      outputs: [],
      branches,
      componentType: "BranchingNode" as const,
    }),
  );
}
