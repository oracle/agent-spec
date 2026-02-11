import { describe, it, expect } from "vitest";
import {
  AgentSpecSerializer,
  createAgent,
  createOpenAiCompatibleConfig,
  createVllmConfig,
  createServerTool,
  stringProperty,
  CURRENT_VERSION,
  camelToSnake,
  snakeToCamel,
} from "../../src/index.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

describe("AgentSpecSerializer", () => {
  describe("toDict", () => {
    it("should serialize an agent to a dict", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "You are helpful.",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      expect(dict["component_type"]).toBe("Agent");
      expect(dict["name"]).toBe("test-agent");
      expect(dict["system_prompt"]).toBe("You are helpful.");
      expect(dict["agentspec_version"]).toBe(CURRENT_VERSION);
    });

    it("should include component_type field", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      expect(dict["component_type"]).toBe("Agent");
    });

    it("should convert camelCase to snake_case", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      expect("system_prompt" in dict).toBe(true);
      expect("systemPrompt" in dict).toBe(false);
      expect("llm_config" in dict).toBe(true);
      expect("llmConfig" in dict).toBe(false);
      expect("human_in_the_loop" in dict).toBe(true);
      expect("humanInTheLoop" in dict).toBe(false);
    });

    it("should order priority keys first (component_type, agentspec_version, id, name, description)", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      const keys = Object.keys(dict);
      expect(keys[0]).toBe("component_type");
      expect(keys[1]).toBe("agentspec_version");
      expect(keys[2]).toBe("id");
      expect(keys[3]).toBe("name");
    });

    it("should exclude sensitive fields (apiKey)", () => {
      const serializer = new AgentSpecSerializer();
      const llmConfig = createOpenAiCompatibleConfig({
        name: "test-llm",
        url: "http://localhost",
        modelId: "gpt-4",
        apiKey: "sk-secret",
      });
      const agent = createAgent({
        name: "test-agent",
        llmConfig,
        systemPrompt: "Hello",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      const llmDict = dict["llm_config"] as Record<string, unknown>;
      expect("api_key" in llmDict).toBe(false);
    });

    it("should serialize Property fields to their jsonSchema dict", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Help with {{topic}}",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      const inputs = dict["inputs"] as unknown[];
      expect(inputs).toHaveLength(1);
      expect((inputs[0] as Record<string, unknown>)["title"]).toBe("topic");
      expect((inputs[0] as Record<string, unknown>)["type"]).toBe("string");
    });

    it("should serialize nested components (llmConfig)", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      const llmDict = dict["llm_config"] as Record<string, unknown>;
      expect(llmDict["component_type"]).toBe("OpenAiCompatibleConfig");
      expect(llmDict["model_id"]).toBe("gpt-4");
    });

    it("should serialize tools array", () => {
      const serializer = new AgentSpecSerializer();
      const tool = createServerTool({
        name: "my-tool",
        inputs: [stringProperty({ title: "query" })],
      });
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
        tools: [tool],
      });
      const dict = serializer.toDict(agent) as Record<string, unknown>;
      const tools = dict["tools"] as unknown[];
      expect(tools).toHaveLength(1);
      const toolDict = tools[0] as Record<string, unknown>;
      expect(toolDict["component_type"]).toBe("ServerTool");
    });
  });

  describe("toJson", () => {
    it("should return a valid JSON string", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const json = serializer.toJson(agent) as string;
      const parsed = JSON.parse(json);
      expect(parsed["component_type"]).toBe("Agent");
      expect(parsed["name"]).toBe("test-agent");
    });

    it("should respect indent option", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const json = serializer.toJson(agent, { indent: 4 }) as string;
      // Default indent is 2, custom should have 4 spaces
      expect(json).toContain("    ");
    });
  });

  describe("toYaml", () => {
    it("should return a valid YAML string", () => {
      const serializer = new AgentSpecSerializer();
      const agent = createAgent({
        name: "test-agent",
        llmConfig: makeLlmConfig(),
        systemPrompt: "Hello",
      });
      const yaml = serializer.toYaml(agent) as string;
      expect(yaml).toContain("component_type: Agent");
      expect(yaml).toContain("name: test-agent");
    });
  });

  describe("disaggregated components", () => {
    it("should return a tuple when exportDisaggregatedComponents=true", () => {
      const serializer = new AgentSpecSerializer();
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
      const result = serializer.toDict(agent, {
        disaggregatedComponents: [llmConfig],
        exportDisaggregatedComponents: true,
      }) as [Record<string, unknown>, Record<string, unknown>];

      expect(Array.isArray(result)).toBe(true);
      expect(result).toHaveLength(2);

      const mainDict = result[0];
      const disaggDict = result[1];

      // Main dict should have $component_ref for the llm config
      const llmField = mainDict["llm_config"] as Record<string, unknown>;
      expect(llmField["$component_ref"]).toBe(llmConfig.id);

      // Disaggregated dict should have $referenced_components
      const refs = disaggDict["$referenced_components"] as Record<
        string,
        unknown
      >;
      expect(refs[llmConfig.id]).toBeDefined();
    });
  });
});

describe("camelToSnake", () => {
  it("should convert simple camelCase", () => {
    expect(camelToSnake("modelId")).toBe("model_id");
    expect(camelToSnake("systemPrompt")).toBe("system_prompt");
  });

  it("should convert humanInTheLoop", () => {
    expect(camelToSnake("humanInTheLoop")).toBe("human_in_the_loop");
  });

  it("should convert httpMethod", () => {
    expect(camelToSnake("httpMethod")).toBe("http_method");
  });

  it("should handle already snake_case", () => {
    expect(camelToSnake("already_snake")).toBe("already_snake");
  });

  it("should handle single word", () => {
    expect(camelToSnake("name")).toBe("name");
  });
});

describe("snakeToCamel", () => {
  it("should convert simple snake_case", () => {
    expect(snakeToCamel("model_id")).toBe("modelId");
    expect(snakeToCamel("system_prompt")).toBe("systemPrompt");
  });

  it("should convert human_in_the_loop", () => {
    expect(snakeToCamel("human_in_the_loop")).toBe("humanInTheLoop");
  });

  it("should handle single word", () => {
    expect(snakeToCamel("name")).toBe("name");
  });

  it("should handle already camelCase", () => {
    expect(snakeToCamel("alreadyCamel")).toBe("alreadyCamel");
  });
});
