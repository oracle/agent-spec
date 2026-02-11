/**
 * OpenAI-compatible LLM config.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { LlmGenerationConfigSchema, OpenAIAPIType } from "./llm-config.js";

export const OpenAiCompatibleConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("OpenAiCompatibleConfig"),
  url: z.string(),
  modelId: z.string(),
  apiType: z
    .enum([OpenAIAPIType.CHAT_COMPLETIONS, OpenAIAPIType.RESPONSES])
    .default(OpenAIAPIType.CHAT_COMPLETIONS),
  defaultGenerationParameters: LlmGenerationConfigSchema.optional(),
  apiKey: z.string().optional(),
});

export type OpenAiCompatibleConfig = z.infer<
  typeof OpenAiCompatibleConfigSchema
>;

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
}): OpenAiCompatibleConfig {
  const raw = {
    ...opts,
    componentType: "OpenAiCompatibleConfig" as const,
  };
  const parsed = OpenAiCompatibleConfigSchema.parse(raw);
  return Object.freeze(parsed);
}
