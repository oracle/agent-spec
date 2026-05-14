/**
 * Ollama LLM config.
 */
import { z } from "zod";
import { LlmConfigBaseSchema, LlmGenerationConfigSchema, LocalInferenceFields, OpenAIAPIType } from "./llm-config.js";
import { RetryPolicySchema } from "./retry-policy.js";

// apiProvider is fixed to "ollama" and excluded from serialization, so omitted here.
export const OllamaConfigSchema = LlmConfigBaseSchema
  .omit({ apiProvider: true })
  .extend({
    componentType: z.literal("OllamaConfig"),
    ...LocalInferenceFields,
  });

export type OllamaConfig = z.infer<typeof OllamaConfigSchema>;

export function createOllamaConfig(opts: {
  name: string;
  url: string;
  modelId: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  apiType?: OpenAIAPIType;
  defaultGenerationParameters?: z.infer<typeof LlmGenerationConfigSchema>;
  apiKey?: string;
  provider?: string;
  keyFile?: string;
  certFile?: string;
  caFile?: string;
  retryPolicy?: z.infer<typeof RetryPolicySchema>;
}): OllamaConfig {
  return Object.freeze(
    OllamaConfigSchema.parse({ ...opts, componentType: "OllamaConfig" }),
  );
}
