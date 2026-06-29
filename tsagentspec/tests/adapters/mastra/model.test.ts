import { describe, expect, it } from "vitest";
import {
  createOciClientConfigWithApiKey,
  createOciGenAiConfig,
  createOllamaConfig,
  createOpenAiCompatibleConfig,
  createOpenAiConfig,
  createVllmConfig,
} from "../../../src/index.js";
import {
  defaultMastraModelResolver,
  UnsupportedMastraModelError,
} from "../../../src/adapters/mastra/index.js";

describe("Mastra model resolver", () => {
  it("maps OpenAiConfig to a Mastra provider model id", () => {
    const target = defaultMastraModelResolver(
      createOpenAiConfig({
        name: "openai",
        modelId: "gpt-4o-mini",
      }),
      {},
    );

    expect(target).toBe("openai/gpt-4o-mini");
  });

  it("preserves OpenAI API keys in model config targets", () => {
    const target = defaultMastraModelResolver(
      createOpenAiConfig({
        name: "openai",
        modelId: "gpt-4o",
        apiKey: "secret",
      }),
      {},
    );

    expect(target).toEqual({
      id: "openai/gpt-4o",
      apiKey: "secret",
    });
  });

  it("maps OpenAiCompatibleConfig to a URL-backed model target", () => {
    const target = defaultMastraModelResolver(
      createOpenAiCompatibleConfig({
        name: "compatible",
        modelId: "custom-model",
        url: "https://models.example.com/v1",
        apiKey: "secret",
      }),
      {},
    );

    expect(target).toEqual({
      id: "openai-compatible/custom-model",
      url: "https://models.example.com/v1",
      apiKey: "secret",
    });
  });

  it("preserves slash-containing OpenAI-compatible model ids", () => {
    const target = defaultMastraModelResolver(
      createOpenAiCompatibleConfig({
        name: "compatible",
        modelId: "oci/openai.gpt-5.4-mini",
        url: "https://models.example.com/v1",
        apiKey: "secret",
      }),
      {},
    );

    expect(target).toEqual({
      id: "openai-compatible/oci/openai.gpt-5.4-mini",
      url: "https://models.example.com/v1",
      apiKey: "secret",
    });
  });

  it("maps OllamaConfig to an ollama-prefixed model target", () => {
    const target = defaultMastraModelResolver(
      createOllamaConfig({
        name: "ollama",
        modelId: "llama3.1",
        url: "http://localhost:11434",
      }),
      {},
    );

    expect(target).toEqual({
      id: "ollama/llama3.1",
      url: "http://localhost:11434",
    });
  });

  it("maps VllmConfig to a vllm-prefixed model target", () => {
    const target = defaultMastraModelResolver(
      createVllmConfig({
        name: "vllm",
        modelId: "qwen2.5",
        url: "http://localhost:8000",
      }),
      {},
    );

    expect(target).toEqual({
      id: "vllm/qwen2.5",
      url: "http://localhost:8000",
    });
  });

  it("fails explicitly for unsupported OCI GenAI configs", () => {
    const ociConfig = createOciGenAiConfig({
      name: "oci",
      modelId: "cohere.command-r-plus",
      compartmentId: "ocid1.compartment.oc1..example",
      clientConfig: createOciClientConfigWithApiKey({
        name: "oci-client",
        serviceEndpoint: "https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com",
        authProfile: "DEFAULT",
        authFileLocation: "~/.oci/config",
      }),
    });

    expect(() => defaultMastraModelResolver(ociConfig, {})).toThrow(
      UnsupportedMastraModelError,
    );
  });
});
