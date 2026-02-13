/**
 * ManagerWorkers multi-agent component.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";
import type { Property } from "../property.js";

// z.record(z.unknown()) is used instead of AgenticComponentUnion to break a circular
// dependency (ManagerWorkers -> AgenticComponentUnion -> ManagerWorkers). Validation of
// the nested agents is handled by the deserialization plugin at runtime.
const AgenticComponentRef = z.lazy(() => z.record(z.unknown()));

export const ManagerWorkersSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("ManagerWorkers"),
  groupManager: AgenticComponentRef,
  workers: z.array(AgenticComponentRef),
});

export type ManagerWorkers = z.infer<typeof ManagerWorkersSchema>;

export function createManagerWorkers(opts: {
  name: string;
  groupManager: Record<string, unknown>;
  workers: Record<string, unknown>[];
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): ManagerWorkers {
  return Object.freeze(
    ManagerWorkersSchema.parse({
      ...opts,
      componentType: "ManagerWorkers" as const,
    }),
  );
}
