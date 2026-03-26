/**
 * ControlFlowEdge - defines control flow between nodes.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../../component.js";
import { LazyNodeRef } from "../lazy-schemas.js";

export const ControlFlowEdgeSchema = ComponentBaseSchema.extend({
  componentType: z.literal("ControlFlowEdge"),
  fromNode: LazyNodeRef,
  fromBranch: z.string().optional(),
  toNode: LazyNodeRef,
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
