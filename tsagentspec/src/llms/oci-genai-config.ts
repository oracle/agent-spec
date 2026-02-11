/**
 * OCI GenAI LLM config.
 */
import { z } from "zod";
import { ComponentBaseSchema } from "../component.js";
import { LlmGenerationConfigSchema } from "./llm-config.js";
import { OciClientConfigUnion, type OciClientConfig } from "./oci-client-config.js";

/** Serving mode enum */
export const ServingMode = {
  ON_DEMAND: "ON_DEMAND",
  DEDICATED: "DEDICATED",
} as const;

export type ServingMode = (typeof ServingMode)[keyof typeof ServingMode];

/** Model provider enum */
export const ModelProvider = {
  META: "META",
  GROK: "GROK",
  COHERE: "COHERE",
  OTHER: "OTHER",
} as const;

export type ModelProvider = (typeof ModelProvider)[keyof typeof ModelProvider];

/** OCI API type enum */
export const OciAPIType = {
  OPENAI_CHAT_COMPLETIONS: "openai_chat_completions",
  OPENAI_RESPONSES: "openai_responses",
  OCI: "oci",
} as const;

export type OciAPIType = (typeof OciAPIType)[keyof typeof OciAPIType];

export const OciGenAiConfigSchema = ComponentBaseSchema.extend({
  componentType: z.literal("OciGenAiConfig"),
  modelId: z.string(),
  compartmentId: z.string(),
  servingMode: z
    .enum([ServingMode.ON_DEMAND, ServingMode.DEDICATED])
    .default(ServingMode.ON_DEMAND),
  provider: z
    .enum([
      ModelProvider.META,
      ModelProvider.GROK,
      ModelProvider.COHERE,
      ModelProvider.OTHER,
    ])
    .optional(),
  clientConfig: OciClientConfigUnion,
  apiType: z
    .enum([
      OciAPIType.OPENAI_CHAT_COMPLETIONS,
      OciAPIType.OPENAI_RESPONSES,
      OciAPIType.OCI,
    ])
    .default(OciAPIType.OCI),
  conversationStoreId: z.string().optional(),
  defaultGenerationParameters: LlmGenerationConfigSchema.optional(),
});

export type OciGenAiConfig = z.infer<typeof OciGenAiConfigSchema>;

export function createOciGenAiConfig(opts: {
  name: string;
  modelId: string;
  compartmentId: string;
  clientConfig: OciClientConfig;
  id?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  servingMode?: ServingMode;
  provider?: ModelProvider;
  apiType?: OciAPIType;
  conversationStoreId?: string;
  defaultGenerationParameters?: z.infer<typeof LlmGenerationConfigSchema>;
}): OciGenAiConfig {
  return Object.freeze(
    OciGenAiConfigSchema.parse({
      ...opts,
      componentType: "OciGenAiConfig" as const,
    }),
  );
}
