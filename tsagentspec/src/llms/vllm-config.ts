/**
 * vLLM config.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { LlmGenerationConfigSchema, OpenAIAPIType } from "./llm-config.js";

export const VllmConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("VllmConfig"),
  url: z.string(),
  modelId: z.string(),
  apiType: z
    .enum([OpenAIAPIType.CHAT_COMPLETIONS, OpenAIAPIType.RESPONSES])
    .default(OpenAIAPIType.CHAT_COMPLETIONS),
  defaultGenerationParameters: LlmGenerationConfigSchema.optional(),
  apiKey: z.string().optional(),
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
}): VllmConfig {
  const parsed = VllmConfigSchema.parse({
    ...opts,
    componentType: "VllmConfig" as const,
  });
  return Object.freeze(parsed);
}
