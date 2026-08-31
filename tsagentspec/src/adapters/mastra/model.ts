import type { LlmConfig } from "../../llms/index.js";
import { UnsupportedMastraModelError } from "./errors.js";
import type { MastraModelResolver, MastraModelTarget } from "./types.js";

export const defaultMastraModelResolver: MastraModelResolver = (
  llmConfig: LlmConfig,
  _context,
): MastraModelTarget => {
  switch (llmConfig.componentType) {
    case "OpenAiConfig":
      return llmConfig.apiKey
        ? { id: withProviderPrefix("openai", llmConfig.modelId), apiKey: llmConfig.apiKey }
        : withProviderPrefix("openai", llmConfig.modelId);

    case "OpenAiCompatibleConfig":
      return modelConfig(
        withOpenAiCompatiblePrefix(llmConfig.modelId),
        llmConfig.url,
        llmConfig.apiKey,
      );

    case "OllamaConfig":
      return modelConfig(
        withProviderPrefix("ollama", llmConfig.modelId),
        llmConfig.url,
        llmConfig.apiKey,
      );

    case "VllmConfig":
      return modelConfig(
        withProviderPrefix("vllm", llmConfig.modelId),
        llmConfig.url,
        llmConfig.apiKey,
      );

    case "OciGenAiConfig":
      throw new UnsupportedMastraModelError(llmConfig.componentType);
  }
};

const modelConfig = (
  id: string,
  url: string,
  apiKey?: string,
): MastraModelTarget => ({
  id,
  url,
  ...(apiKey ? { apiKey } : {}),
});

const withProviderPrefix = (provider: string, modelId: string): string => {
  if (modelId.includes("/")) {
    return modelId;
  }
  // Mastra commonly accepts provider-qualified model ids such as
  // `openai/gpt-4o-mini`; preserve ids that are already qualified.
  return `${provider}/${modelId}`;
};

const withOpenAiCompatiblePrefix = (modelId: string): string => {
  if (modelId.startsWith("openai-compatible/")) {
    return modelId;
  }

  // Mastra parses URL-backed model targets as provider/model. Prefixing with a
  // neutral provider keeps endpoint-specific ids like `oci/openai...` intact.
  return `openai-compatible/${modelId}`;
};
