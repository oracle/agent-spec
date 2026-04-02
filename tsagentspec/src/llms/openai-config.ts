/**
 * OpenAI config (no url field).
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { LlmGenerationConfigSchema, OpenAIAPIType } from "./llm-config.js";

export const OpenAiConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("OpenAiConfig"),
  modelId: z.string(),
  apiType: z
    .enum([OpenAIAPIType.CHAT_COMPLETIONS, OpenAIAPIType.RESPONSES])
    .default(OpenAIAPIType.CHAT_COMPLETIONS),
  defaultGenerationParameters: LlmGenerationConfigSchema.optional(),
  apiKey: z.string().optional(),
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
}): OpenAiConfig {
  const parsed = OpenAiConfigSchema.parse({
    ...opts,
    componentType: "OpenAiConfig" as const,
  });
  return Object.freeze(parsed);
}
