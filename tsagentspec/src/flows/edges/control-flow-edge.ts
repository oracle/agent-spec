/**
 * ControlFlowEdge - defines control flow between nodes.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../../component.js";

const NodeRef = z.record(z.unknown());

export const ControlFlowEdgeSchema = ComponentBaseSchema.extend({
  componentType: z.literal("ControlFlowEdge"),
  fromNode: NodeRef,
  fromBranch: z.string().optional(),
  toNode: NodeRef,
});

export type ControlFlowEdge = z.infer<typeof ControlFlowEdgeSchema>;

export function createControlFlowEdge(opts: {
  name: string;
  fromNode: Record<string, unknown>;
  toNode: Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  fromBranch?: string;
}): ControlFlowEdge {
  return Object.freeze(
    ControlFlowEdgeSchema.parse({
      ...opts,
      componentType: "ControlFlowEdge" as const,
    }),
  );
}
