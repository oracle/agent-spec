/**
 * A2A Agent component.
 */
import { z } from "zod";
import { ComponentBaseSchema, ComponentWithIOSchema } from "../component.js";
import type { Property } from "../property.js";

const A2ASessionParametersSchema = z.object({
  timeout: z.number().default(60.0),
  pollInterval: z.number().default(2.0),
  maxRetries: z.number().int().default(5),
});

export const A2AConnectionConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("A2AConnectionConfig"),
  timeout: z.number().default(600.0),
  headers: z.record(z.string()).optional(),
  verify: z.boolean().default(true),
  keyFile: z.string().optional(),
  certFile: z.string().optional(),
  sslCaCert: z.string().optional(),
});

export type A2AConnectionConfig = z.infer<typeof A2AConnectionConfigSchema>;

export const A2AAgentSchema = ComponentWithIOSchema.extend({
  componentType: z.literal("A2AAgent"),
  agentUrl: z.string(),
  connectionConfig: A2AConnectionConfigSchema,
  sessionParameters: A2ASessionParametersSchema.default({}),
});

export type A2AAgent = z.infer<typeof A2AAgentSchema>;

export function createA2AAgent(opts: {
  name: string;
  agentUrl: string;
  connectionConfig: A2AConnectionConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  sessionParameters?: z.infer<typeof A2ASessionParametersSchema>;
  inputs?: Property[];
  outputs?: Property[];
}): A2AAgent {
  return Object.freeze(
    A2AAgentSchema.parse({
      ...opts,
      componentType: "A2AAgent" as const,
    }),
  );
}
