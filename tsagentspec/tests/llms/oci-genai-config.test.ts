import { describe, it, expect } from "vitest";
import {
  createOciGenAiConfig,
  createOciClientConfigWithApiKey,
  ServingMode,
  ModelProvider,
  OciAPIType,
} from "../../src/index.js";

function makeClientConfig() {
  return createOciClientConfigWithApiKey({
    name: "oci-client",
    serviceEndpoint: "https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com",
    authProfile: "DEFAULT",
    authFileLocation: "~/.oci/config",
  });
}

describe("OciGenAiConfig", () => {
  it("should create with required fields", () => {
    const config = createOciGenAiConfig({
      name: "oci-llm",
      modelId: "cohere.command-r-plus",
      compartmentId: "ocid1.compartment.oc1..aaa",
      clientConfig: makeClientConfig(),
    });
    expect(config.componentType).toBe("OciGenAiConfig");
    expect(config.name).toBe("oci-llm");
    expect(config.modelId).toBe("cohere.command-r-plus");
    expect(config.compartmentId).toBe("ocid1.compartment.oc1..aaa");
  });

  it("should default servingMode to ON_DEMAND", () => {
    const config = createOciGenAiConfig({
      name: "test",
      modelId: "model1",
      compartmentId: "compartment1",
      clientConfig: makeClientConfig(),
    });
    expect(config.servingMode).toBe(ServingMode.ON_DEMAND);
  });

  it("should accept DEDICATED servingMode", () => {
    const config = createOciGenAiConfig({
      name: "test",
      modelId: "model1",
      compartmentId: "compartment1",
      clientConfig: makeClientConfig(),
      servingMode: ServingMode.DEDICATED,
    });
    expect(config.servingMode).toBe("DEDICATED");
  });

  it("should default apiType to OCI", () => {
    const config = createOciGenAiConfig({
      name: "test",
      modelId: "model1",
      compartmentId: "compartment1",
      clientConfig: makeClientConfig(),
    });
    expect(config.apiType).toBe(OciAPIType.OCI);
  });

  it("should accept custom apiType", () => {
    const config = createOciGenAiConfig({
      name: "test",
      modelId: "model1",
      compartmentId: "compartment1",
      clientConfig: makeClientConfig(),
      apiType: OciAPIType.OPENAI_CHAT_COMPLETIONS,
    });
    expect(config.apiType).toBe("openai_chat_completions");
  });

  it("should accept a provider", () => {
    const config = createOciGenAiConfig({
      name: "test",
      modelId: "model1",
      compartmentId: "compartment1",
      clientConfig: makeClientConfig(),
      provider: ModelProvider.COHERE,
    });
    expect(config.provider).toBe("COHERE");
  });

  it("should be frozen", () => {
    const config = createOciGenAiConfig({
      name: "test",
      modelId: "model1",
      compartmentId: "compartment1",
      clientConfig: makeClientConfig(),
    });
    expect(Object.isFrozen(config)).toBe(true);
  });
});

describe("Enums", () => {
  it("should define ServingMode values", () => {
    expect(ServingMode.ON_DEMAND).toBe("ON_DEMAND");
    expect(ServingMode.DEDICATED).toBe("DEDICATED");
  });

  it("should define ModelProvider values", () => {
    expect(ModelProvider.META).toBe("META");
    expect(ModelProvider.GROK).toBe("GROK");
    expect(ModelProvider.COHERE).toBe("COHERE");
    expect(ModelProvider.OTHER).toBe("OTHER");
  });

  it("should define OciAPIType values", () => {
    expect(OciAPIType.OPENAI_CHAT_COMPLETIONS).toBe("openai_chat_completions");
    expect(OciAPIType.OPENAI_RESPONSES).toBe("openai_responses");
    expect(OciAPIType.OCI).toBe("oci");
  });
});
