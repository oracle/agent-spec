/**
 * OpenAI-compatible LLM config.
 */
import { z } from "zod";
import { LlmConfigBaseSchema, LlmGenerationConfigSchema, LocalInferenceFields, OpenAIAPIType } from "./llm-config.js";
import { RetryPolicySchema } from "./retry-policy.js";

export const OpenAiCompatibleConfigSchema = LlmConfigBaseSchema.extend({
  componentType: z.literal("OpenAiCompatibleConfig"),
  ...LocalInferenceFields,
});

export type OpenAiCompatibleConfig = z.infer<typeof OpenAiCompatibleConfigSchema>;

export function createOpenAiCompatibleConfig(opts: {
  name: string;
  url: string;
  modelId: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  apiType?: OpenAIAPIType;
  defaultGenerationParameters?: z.infer<typeof LlmGenerationConfigSchema>;
  apiKey?: string;
  apiProvider?: string;
  provider?: string;
  keyFile?: string;
  certFile?: string;
  caFile?: string;
  retryPolicy?: z.infer<typeof RetryPolicySchema>;
}): OpenAiCompatibleConfig {
  return Object.freeze(
    OpenAiCompatibleConfigSchema.parse({ ...opts, componentType: "OpenAiCompatibleConfig" }),
  );
}
