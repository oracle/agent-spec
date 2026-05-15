/**
 * Gemini auth config components.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";

export const GeminiAIStudioAuthConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("GeminiAIStudioAuthConfig"),
  apiKey: z.string().optional(),
});
export type GeminiAIStudioAuthConfig = z.infer<
  typeof GeminiAIStudioAuthConfigSchema
>;

export const GeminiVertexAIAuthConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("GeminiVertexAIAuthConfig"),
  projectId: z.string().optional(),
  location: z.string().default("global"),
  credentials: z.union([z.string(), z.record(z.unknown())]).optional(),
});
export type GeminiVertexAIAuthConfig = z.infer<
  typeof GeminiVertexAIAuthConfigSchema
>;

export const GeminiAuthConfigUnion = z.discriminatedUnion("componentType", [
  GeminiAIStudioAuthConfigSchema,
  GeminiVertexAIAuthConfigSchema,
]);
export type GeminiAuthConfig = z.infer<typeof GeminiAuthConfigUnion>;

export function createGeminiAIStudioAuthConfig(opts: {
  name: string;
  apiKey?: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): GeminiAIStudioAuthConfig {
  return Object.freeze(
    GeminiAIStudioAuthConfigSchema.parse({
      ...opts,
      componentType: "GeminiAIStudioAuthConfig",
    }),
  );
}

export function createGeminiVertexAIAuthConfig(opts: {
  name: string;
  projectId?: string;
  location?: string;
  credentials?: string | Record<string, unknown>;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}): GeminiVertexAIAuthConfig {
  return Object.freeze(
    GeminiVertexAIAuthConfigSchema.parse({
      ...opts,
      componentType: "GeminiVertexAIAuthConfig",
    }),
  );
}
