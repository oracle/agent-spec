/**
 * OpenAI config (no url field).
 */
import { z } from "zod";
import { LlmConfigBaseSchema, LlmGenerationConfigSchema, OpenAIAPIType } from "./llm-config.js";
import { RetryPolicySchema } from "./retry-policy.js";

// provider and apiProvider are fixed to "openai" and excluded from serialization,
// so they are omitted from the schema. url is not applicable to OpenAI's hosted API.
export const OpenAiConfigSchema = LlmConfigBaseSchema
  .omit({ url: true, provider: true, apiProvider: true })
  .extend({
    componentType: z.literal("OpenAiConfig"),
    apiType: z
      .enum([OpenAIAPIType.CHAT_COMPLETIONS, OpenAIAPIType.RESPONSES])
      .default(OpenAIAPIType.CHAT_COMPLETIONS),
  });

export type OpenAiConfig = z.infer<typeof OpenAiConfigSchema>;

export function createOpenAiConfig(opts: {
  name: string;
  modelId: string;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  apiType?: OpenAIAPIType;
  defaultGenerationParameters?: z.infer<typeof LlmGenerationConfigSchema>;
  apiKey?: string;
  retryPolicy?: z.infer<typeof RetryPolicySchema>;
}): OpenAiConfig {
  return Object.freeze(
    OpenAiConfigSchema.parse({ ...opts, componentType: "OpenAiConfig" }),
  );
}
