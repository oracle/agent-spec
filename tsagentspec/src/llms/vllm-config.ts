/**
 * vLLM config.
 */
import { z } from "zod";
import { LlmConfigBaseSchema, LlmGenerationConfigSchema, LocalInferenceFields, OpenAIAPIType } from "./llm-config.js";
import { RetryPolicySchema } from "./retry-policy.js";

// apiProvider is fixed to "vllm" and excluded from serialization, so omitted here.
export const VllmConfigSchema = LlmConfigBaseSchema
  .omit({ apiProvider: true })
  .extend({
    componentType: z.literal("VllmConfig"),
    ...LocalInferenceFields,
  });

export type VllmConfig = z.infer<typeof VllmConfigSchema>;

export function createVllmConfig(opts: {
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
}): VllmConfig {
  return Object.freeze(
    VllmConfigSchema.parse({ ...opts, componentType: "VllmConfig" }),
  );
}
