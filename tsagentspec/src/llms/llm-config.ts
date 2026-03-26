/**
 * LLM generation config and shared enums.
 */
import { z } from "zod";

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
