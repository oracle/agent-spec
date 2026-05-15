/**
 * Gemini LLM config.
 */
import { z } from "zod";
import { LlmConfigBaseSchema, LlmGenerationConfigSchema } from "./llm-config.js";
import {
  GeminiAuthConfigUnion,
  type GeminiAuthConfig,
} from "./gemini-auth-config.js";
import { RetryPolicySchema } from "./retry-policy.js";

// provider is fixed to "google", url/apiKey/apiProvider/apiType are not applicable to Gemini.
export const GeminiConfigSchema = LlmConfigBaseSchema
  .omit({ url: true, apiKey: true, apiProvider: true, provider: true, apiType: true })
  .extend({
    componentType: z.literal("GeminiConfig"),
    auth: GeminiAuthConfigUnion,
  });

export type GeminiConfig = z.infer<typeof GeminiConfigSchema>;

export function createGeminiConfig(opts: {
  name: string;
  modelId: string;
  auth: GeminiAuthConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  defaultGenerationParameters?: z.infer<typeof LlmGenerationConfigSchema>;
  retryPolicy?: z.infer<typeof RetryPolicySchema>;
}): GeminiConfig {
  return Object.freeze(
    GeminiConfigSchema.parse({ ...opts, componentType: "GeminiConfig" }),
  );
}
