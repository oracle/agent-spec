import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  AgentSpecDeserializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createServerTool,
  createVllmConfig,
  stringProperty,
  CURRENT_VERSION,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("AgentSpecDeserializer", () => {
  describe("fromDict", () => {
    it("should deserialize a serialized Agent dict", () => {
      const serializer = new AgentSpecSerializer();
      const deserializer = new AgentSpecDeserializer();

      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "You are helpful.",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      const result = deserializer.fromDict(dict) as Record<string, unknown>;
      expect(result["componentType"]).toBe("Agent");
      expect(result["name"]).toBe("test-agent");
      expect(result["systemPrompt"]).toBe("You are helpful.");
    });

    it("should convert snake_case to camelCase", () => {
      const deserializer = new AgentSpecDeserializer();
      const dict = {
        agentspec_version: CURRENT_VERSION,
        component_type: "Agent",
        name: "test-agent",
        system_prompt: "Hello",
        human_in_the_loop: true,
        llm_config: {
          component_type: "OpenAiCompatibleConfig",
          name: "llm",
          url: "http://localhost",
          model_id: "gpt-4",
          api_type: "chat_completions",
        },
        tools: [],
        toolboxes: [],
        transforms: [],
        inputs: [],
        outputs: [],
      };
      const result = deserializer.fromDict(dict) as Record<string, unknown>;
      expect(result["systemPrompt"]).toBe("Hello");
      expect(result["humanInTheLoop"]).toBe(true);
    });

    it("should dispatch based on component_type", () => {
      const serializer = new AgentSpecSerializer();
      const deserializer = new AgentSpecDeserializer();
      const tool = createServerTool({
        name: "my-tool",
        inputs: [stringProperty({ title: "query" })],
      });
      const dict = serializer.toDict(tool) as Record<string, unknown>;
      const result = deserializer.fromDict(dict) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
      expect(result["name"]).toBe("my-tool");
    });

    it("should throw on missing component_type", () => {
      const deserializer = new AgentSpecDeserializer();
      expect(() =>
        deserializer.fromDict({
          name: "test",
        }),
      ).toThrow("component_type");
    });
  });

  describe("fromJson", () => {
    it("should deserialize from a JSON string", () => {
      const serializer = new AgentSpecSerializer();
      const deserializer = new AgentSpecDeserializer();

      const agent = createAgent({
        name: "json-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const json = serializer.toJson(agent) as string;
      const result = deserializer.fromJson(json) as Record<string, unknown>;
      expect(result["componentType"]).toBe("Agent");
      expect(result["name"]).toBe("json-agent");
    });
  });

  describe("fromYaml", () => {
    it("should deserialize from a YAML string", () => {
      const serializer = new AgentSpecSerializer();
      const deserializer = new AgentSpecDeserializer();

      const agent = createAgent({
        name: "yaml-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const yaml = serializer.toYaml(agent) as string;
      const result = deserializer.fromYaml(yaml) as Record<string, unknown>;
      expect(result["componentType"]).toBe("Agent");
      expect(result["name"]).toBe("yaml-agent");
    });
  });

  describe("disaggregated components", () => {
    it("should deserialize disaggregated configs with importOnlyReferencedComponents", () => {
      const serializer = new AgentSpecSerializer();
      const deserializer = new AgentSpecDeserializer();

      const llmConfig = createVllmConfig({
        name: "shared-llm",
        url: "http://localhost:8000",
        modelId: "llama",
      });
      const agent = createAgent({
        name: "agent",
        llmConfig,
        systemPrompt: "Hello",
      });

      const [mainDict, disagDict] = serializer.toDict(agent, {
        disaggregatedComponents: [llmConfig],
        exportDisaggregatedComponents: true,
      }) as [Record<string, unknown>, Record<string, unknown>];

      // Load disaggregated components first
      const loadedComponents = deserializer.fromDict(disagDict, {
        importOnlyReferencedComponents: true,
      }) as Record<string, Record<string, unknown>>;
      expect(Object.keys(loadedComponents)).toHaveLength(1);

      // Create a registry from the loaded components
      const registry = new Map<string, Record<string, unknown>>();
      for (const [id, comp] of Object.entries(loadedComponents)) {
        registry.set(id, comp as any);
      }

      // Load the main component with the registry
      const result = deserializer.fromDict(mainDict, {
        componentsRegistry: registry as any,
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("Agent");
      expect(result["name"]).toBe("agent");
    });

    it("should throw when loading disaggregated without flag", () => {
      const deserializer = new AgentSpecDeserializer();
      expect(() =>
        deserializer.fromDict({
          $referenced_components: { "some-id": {} },
        }),
      ).toThrow("importOnlyReferencedComponents");
    });
  });
});
