/**
 * RemoteAgent - represents a remotely-defined agent.
 */
import { z } from "zod";
import { ComponentWithIOSchema } from "../component.js";

export const RemoteAgentSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("RemoteAgent"),
});

export type RemoteAgent = z.infer<typeof RemoteAgentSchema>;
