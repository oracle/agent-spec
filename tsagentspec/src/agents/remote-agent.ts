/**
 * RemoteAgent - represents a remotely-defined agent.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";
import type { Property } from "../property.js";

export const RemoteAgentSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("RemoteAgent"),
});

export type RemoteAgent = z.infer<typeof RemoteAgentSchema>;

export function createRemoteAgent(opts: {
  name: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  inputs?: Property[];
  outputs?: Property[];
}): RemoteAgent {
  return Object.freeze(
    RemoteAgentSchema.parse({
      ...opts,
      componentType: "RemoteAgent" as const,
    }),
  );
}
