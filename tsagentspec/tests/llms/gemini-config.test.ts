import { describe, it, expect } from "vitest";
import {
  createGeminiConfig,
  createGeminiAIStudioAuthConfig,
  createGeminiVertexAIAuthConfig,
  AgentSpecSerializer,
  AgentSpecDeserializer,
  AgentSpecVersion,
} from "../../src/index.js";

const serializer = new AgentSpecSerializer();
const deserializer = new AgentSpecDeserializer();

function makeAIStudioAuth() {
  return createGeminiAIStudioAuthConfig({ name: "auth", apiKey: "gk-test" });
}

function makeVertexAuth() {
  return createGeminiVertexAIAuthConfig({
    name: "vertex-auth",
    projectId: "my-project",
    location: "us-central1",
  });
}

describe("GeminiAIStudioAuthConfig", () => {
  it("should create with required fields only", () => {
    const auth = createGeminiAIStudioAuthConfig({ name: "auth" });
    expect(auth.componentType).toBe("GeminiAIStudioAuthConfig");
    expect(auth.apiKey).toBeUndefined();
    expect(auth.id).toBeDefined();
    expect(Object.isFrozen(auth)).toBe(true);
  });

  it("should accept optional apiKey", () => {
    const auth = createGeminiAIStudioAuthConfig({ name: "auth", apiKey: "gk-abc" });
    expect(auth.apiKey).toBe("gk-abc");
  });
});

describe("GeminiVertexAIAuthConfig", () => {
  it("should create with required fields only", () => {
    const auth = createGeminiVertexAIAuthConfig({ name: "va" });
    expect(auth.componentType).toBe("GeminiVertexAIAuthConfig");
    expect(auth.location).toBe("global");
    expect(auth.projectId).toBeUndefined();
    expect(Object.isFrozen(auth)).toBe(true);
  });

  it("should accept projectId, location, and credentials", () => {
    const auth = createGeminiVertexAIAuthConfig({
      name: "va",
      projectId: "proj-1",
      location: "europe-west1",
      credentials: { key: "value" },
    });
    expect(auth.projectId).toBe("proj-1");
    expect(auth.location).toBe("europe-west1");
    expect(auth.credentials).toEqual({ key: "value" });
  });
});

describe("GeminiConfig", () => {
  it("should create with AIStudio auth", () => {
    const config = createGeminiConfig({
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth: makeAIStudioAuth(),
    });
    expect(config.componentType).toBe("GeminiConfig");
    expect(config.modelId).toBe("gemini-1.5-pro");
    expect(config.auth.componentType).toBe("GeminiAIStudioAuthConfig");
    expect(Object.isFrozen(config)).toBe(true);
  });

  it("should create with VertexAI auth", () => {
    const config = createGeminiConfig({
      name: "gemini",
      modelId: "gemini-1.5-flash",
      auth: makeVertexAuth(),
    });
    expect(config.auth.componentType).toBe("GeminiVertexAIAuthConfig");
  });

  it("should serialise to snake_case YAML", () => {
    const config = createGeminiConfig({
      id: "test-id",
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth: createGeminiAIStudioAuthConfig({ id: "auth-id", name: "auth" }),
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).toContain("component_type: GeminiConfig");
    expect(yaml).toContain("model_id: gemini-1.5-pro");
    expect(yaml).toContain("component_type: GeminiAIStudioAuthConfig");
  });

  it("should exclude apiKey from serialised auth", () => {
    const config = createGeminiConfig({
      id: "test-id",
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth: createGeminiAIStudioAuthConfig({ id: "auth-id", name: "auth", apiKey: "gk-secret" }),
    });
    const yaml = serializer.toYaml(config);
    expect(yaml).not.toContain("gk-secret");
  });

  it("should round-trip without sensitive fields", () => {
    const config = createGeminiConfig({
      id: "test-id",
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth: createGeminiAIStudioAuthConfig({ id: "auth-id", name: "auth" }),
    });
    const yaml = serializer.toYaml(config);
    const restored = deserializer.fromYaml(yaml);
    expect(restored).toEqual(config);
  });

  it("should throw when serialising at version before 26.2.0", () => {
    const config = createGeminiConfig({
      name: "gemini",
      modelId: "gemini-1.5-pro",
      auth: makeAIStudioAuth(),
    });
    expect(() =>
      serializer.toYaml(config, { agentspecVersion: AgentSpecVersion.V25_4_2 }),
    ).toThrow(/26\.2\.0/);
  });
});
