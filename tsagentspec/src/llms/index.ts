/**
 * LLM config types barrel export.
 */
import { z } from "zod";
import { LlmConfigSchema } from "./llm-config.js";
import { OpenAiCompatibleConfigSchema } from "./openai-compatible-config.js";
import { OllamaConfigSchema } from "./ollama-config.js";
import { VllmConfigSchema } from "./vllm-config.js";
import { OpenAiConfigSchema } from "./openai-config.js";
import { OciGenAiConfigSchema } from "./oci-genai-config.js";
import { GeminiConfigSchema } from "./gemini-config.js";

/** Discriminated union of all LLM config types */
export const LlmConfigUnion = z.discriminatedUnion("componentType", [
  LlmConfigSchema,
  OpenAiCompatibleConfigSchema,
  OllamaConfigSchema,
  VllmConfigSchema,
  OpenAiConfigSchema,
  OciGenAiConfigSchema,
  GeminiConfigSchema,
]);

export type LlmConfig = z.infer<typeof LlmConfigUnion>;

export {
  LlmConfigBaseSchema,
  LlmConfigSchema,
  LlmGenerationConfigSchema,
  OpenAIAPIType,
  createLlmConfig,
  type LlmConfigBase,
  type LlmGenerationConfig,
} from "./llm-config.js";

export {
  RetryPolicySchema,
  JitterType,
  type RetryPolicy,
} from "./retry-policy.js";

export {
  GeminiAuthConfigUnion,
  GeminiAIStudioAuthConfigSchema,
  GeminiVertexAIAuthConfigSchema,
  createGeminiAIStudioAuthConfig,
  createGeminiVertexAIAuthConfig,
  type GeminiAuthConfig,
  type GeminiAIStudioAuthConfig,
  type GeminiVertexAIAuthConfig,
} from "./gemini-auth-config.js";

export {
  GeminiConfigSchema,
  createGeminiConfig,
  type GeminiConfig,
} from "./gemini-config.js";

export {
  OpenAiCompatibleConfigSchema,
  createOpenAiCompatibleConfig,
  type OpenAiCompatibleConfig,
} from "./openai-compatible-config.js";

export {
  OllamaConfigSchema,
  createOllamaConfig,
  type OllamaConfig,
} from "./ollama-config.js";

export {
  VllmConfigSchema,
  createVllmConfig,
  type VllmConfig,
} from "./vllm-config.js";

export {
  OpenAiConfigSchema,
  createOpenAiConfig,
  type OpenAiConfig,
} from "./openai-config.js";

export {
  OciGenAiConfigSchema,
  createOciGenAiConfig,
  ServingMode,
  ModelProvider,
  OciAPIType,
  type OciGenAiConfig,
} from "./oci-genai-config.js";

export {
  OciClientConfigUnion,
  OciClientConfigWithApiKeySchema,
  OciClientConfigWithInstancePrincipalSchema,
  OciClientConfigWithResourcePrincipalSchema,
  OciClientConfigWithSecurityTokenSchema,
  createOciClientConfigWithApiKey,
  createOciClientConfigWithInstancePrincipal,
  createOciClientConfigWithResourcePrincipal,
  createOciClientConfigWithSecurityToken,
  type OciClientConfig,
  type OciClientConfigWithApiKey,
  type OciClientConfigWithInstancePrincipal,
  type OciClientConfigWithResourcePrincipal,
  type OciClientConfigWithSecurityToken,
} from "./oci-client-config.js";
