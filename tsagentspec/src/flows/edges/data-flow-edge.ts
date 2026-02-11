/**
 * DataFlowEdge - defines data flow between node outputs and inputs.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../../component.js";

const NodeRef = z.record(z.unknown());

export const DataFlowEdgeSchema = ComponentBaseSchema.extend({
  componentType: z.literal("DataFlowEdge"),
  sourceNode: NodeRef,
  sourceOutput: z.string(),
  destinationNode: NodeRef,
  destinationInput: z.string(),
});

export type DataFlowEdge = z.infer<typeof DataFlowEdgeSchema>;

export function createDataFlowEdge(opts: {
  name: string;
  sourceNode: Record<string, unknown>;
  sourceOutput: string;
  destinationNode: Record<string, unknown>;
  destinationInput: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): DataFlowEdge {
  return Object.freeze(
    DataFlowEdgeSchema.parse({
      ...opts,
      componentType: "DataFlowEdge" as const,
    }),
  );
}
