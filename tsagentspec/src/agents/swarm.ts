/**
 * Swarm multi-agent component.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";
import type { Property } from "../property.js";

/** HandoffMode enum */
export const HandoffMode = {
  NEVER: "never",
  OPTIONAL: "optional",
  ALWAYS: "always",
} as const;

export type HandoffMode = (typeof HandoffMode)[keyof typeof HandoffMode];

// z.record(z.unknown()) is used instead of AgenticComponentUnion to break a circular
// dependency (Swarm -> AgenticComponentUnion -> Swarm). Validation of the nested agents
// is handled by the deserialization plugin at runtime.
const AgenticComponentRef = z.lazy(() => z.record(z.unknown()));

export const SwarmSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("Swarm"),
  firstAgent: AgenticComponentRef,
  relationships: z.array(z.tuple([AgenticComponentRef, AgenticComponentRef])),
  handoff: z
    .enum([HandoffMode.NEVER, HandoffMode.OPTIONAL, HandoffMode.ALWAYS])
    .default(HandoffMode.OPTIONAL),
});

export type Swarm = z.infer<typeof SwarmSchema>;

export function createSwarm(opts: {
  name: string;
  firstAgent: Record<string, unknown>;
  relationships: [Record<string, unknown>, Record<string, unknown>][];
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  handoff?: HandoffMode;
  inputs?: Property[];
  outputs?: Property[];
}): Swarm {
  return Object.freeze(
    SwarmSchema.parse({
      ...opts,
      componentType: "Swarm" as const,
    }),
  );
}
