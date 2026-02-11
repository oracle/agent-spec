/**
 * CatchExceptionNode - execute a subflow and catch exceptions.
 */
import { z } from "zod";
import type { Property } from "../../property.js";
import { NodeBaseSchema } from "../node.js";

export const CAUGHT_EXCEPTION_BRANCH = "caught_exception_branch";
export const DEFAULT_EXCEPTION_INFO_VALUE = "caught_exception_info";

export const CatchExceptionNodeSchema = NodeBaseSchema.extend({
  componentType: z.literal("CatchExceptionNode"),
  subflow: z.lazy(() => z.record(z.unknown())),
});

export type CatchExceptionNode = z.infer<typeof CatchExceptionNodeSchema>;

/** Build the caught_exception_info output property (string | null, default null) */
function makeCaughtExceptionInfoProperty(): Property {
  return {
    jsonSchema: {
      title: DEFAULT_EXCEPTION_INFO_VALUE,
      anyOf: [{ type: "string" }, { type: "null" }],
      default: null,
    },
    title: DEFAULT_EXCEPTION_INFO_VALUE,
    description: undefined,
    default: null,
    type: undefined,
  };
}

function getEndNodeBranches(subflow: Record<string, unknown>): string[] {
  const nodes = subflow["nodes"] as Record<string, unknown>[] | undefined;
  if (!nodes) return [];
  const branches = new Set<string>();
  for (const node of nodes) {
    if (node["componentType"] === "EndNode") {
      const branchName = (node["branchName"] as string) ?? "next";
      branches.add(branchName);
    }
  }
  return [...branches].sort();
}

export function createCatchExceptionNode(opts: {
  name: string;
  subflow: Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): CatchExceptionNode {
  const subflow = opts.subflow;
  const inputs =
    opts.inputs ?? (subflow["inputs"] as Property[] | undefined) ?? [];

  let outputs: Property[];
  if (opts.outputs !== undefined) {
    outputs = opts.outputs;
  } else {
    const subflowOutputs =
      (subflow["outputs"] as Property[] | undefined) ?? [];
    outputs = [...subflowOutputs, makeCaughtExceptionInfoProperty()];
  }

  const endNodeBranches = getEndNodeBranches(subflow);
  const branches = [CAUGHT_EXCEPTION_BRANCH, ...endNodeBranches];

  return Object.freeze(
    CatchExceptionNodeSchema.parse({
      ...opts,
      subflow,
      inputs,
      outputs,
      branches,
      componentType: "CatchExceptionNode" as const,
    }),
  );
}
