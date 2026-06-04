/**
 * LLM generation config and shared enums.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { RetryPolicySchema } from "./retry-policy.js";

/** LlmGenerationConfig - NOT a Component, just a config object */
export const LlmGenerationConfigSchema = z
  .object({
    maxTokens: z.number().int().optional(),
    temperature: z.number().optional(),
    topP: z.number().optional(),
  })
  .passthrough();

export type LlmGenerationConfig = z.infer<typeof LlmGenerationConfigSchema>;

/** OpenAI API type enum */
export const OpenAIAPIType = {
  CHAT_COMPLETIONS: "chat_completions",
  RESPONSES: "responses",
} as const;

export type OpenAIAPIType = (typeof OpenAIAPIType)[keyof typeof OpenAIAPIType];

/**
 * Shared base for all LLM config components.
 * componentType is inherited as z.string() from ComponentBaseSchema;
 * each concrete schema narrows it to its own literal.
 */
export const LlmConfigBaseSchema = ComponentBaseSchema.extend({
  modelId: z.string(),
  provider: z.string().optional(),
  apiProvider: z.string().optional(),
  apiType: z.string().optional(),
  url: z.string().optional(),
  apiKey: z.string().optional(),
  defaultGenerationParameters: LlmGenerationConfigSchema.optional(),
  retryPolicy: RetryPolicySchema.optional(),
});

export type LlmConfigBase = z.infer<typeof LlmConfigBaseSchema>;

/** Shared fields for OpenAI-compatible runtimes that add TLS and require a URL */
export const LocalInferenceFields = {
  url: z.string(),
  apiType: z
    .enum([OpenAIAPIType.CHAT_COMPLETIONS, OpenAIAPIType.RESPONSES])
    .default(OpenAIAPIType.CHAT_COMPLETIONS),
  keyFile: z.string().optional(),
  certFile: z.string().optional(),
  caFile: z.string().optional(),
} as const;

/** Bare LlmConfig component - generic LLM configuration */
export const LlmConfigSchema = LlmConfigBaseSchema.extend({
  componentType: z.literal("LlmConfig"),
});

export type LlmConfig = z.infer<typeof LlmConfigSchema>;

export function createLlmConfig(opts: {
  name: string;
  modelId: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  provider?: string;
  apiProvider?: string;
  apiType?: string;
  url?: string;
  apiKey?: string;
  defaultGenerationParameters?: z.infer<typeof LlmGenerationConfigSchema>;
  retryPolicy?: z.infer<typeof RetryPolicySchema>;
}): LlmConfig {
  return Object.freeze(
    LlmConfigSchema.parse({ ...opts, componentType: "LlmConfig" }),
  );
}
