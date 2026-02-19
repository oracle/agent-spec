import { describe, it, expect } from "vitest";
import {
  SerializationContext,
  AgentSpecSerializer,
  camelToSnake,
  snakeToCamel,
  createAgent,
  createOpenAiCompatibleConfig,
  createBuiltinTool,
  stringProperty,
  CURRENT_VERSION,
  AgentSpecVersion,
} from "../../src/index.js";
import { BuiltinsComponentSerializationPlugin } from "../../src/serialization/builtin-serialization-plugin.js";

function makeLlmConfig() {
  return createOpenAiCompatibleConfig({
    name: "test-llm",
    url: "http://localhost:8000",
    modelId: "gpt-4",
  });
}

function makeBuiltinPlugins() {
  return [new BuiltinsComponentSerializationPlugin()];
}

describe("SerializationContext", () => {
  describe("constructor", () => {
    it("should use CURRENT_VERSION when no version is specified", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.agentspecVersion).toBe(CURRENT_VERSION);
    });

    it("should accept a custom target version", () => {
      const ctx = new SerializationContext(
        makeBuiltinPlugins(),
        "0.4.0",
      );
      expect(ctx.agentspecVersion).toBe("0.4.0");
    });

    it("should default camelCase to false", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.camelCase).toBe(false);
    });

    it("should accept camelCase option", () => {
      const ctx = new SerializationContext(
        makeBuiltinPlugins(),
        undefined,
        undefined,
        undefined,
        true,
      );
      expect(ctx.camelCase).toBe(true);
    });

    it("should throw on duplicate plugin component types", () => {
      const plugins = [
        new BuiltinsComponentSerializationPlugin(),
        new BuiltinsComponentSerializationPlugin(),
      ];
      expect(() => new SerializationContext(plugins)).toThrow(
        "Multiple plugins handle serialization",
      );
    });
  });

  describe("dumpField", () => {
    it("should return null for null and undefined", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.dumpField(null)).toBeNull();
      expect(ctx.dumpField(undefined)).toBeNull();
    });

    it("should return primitives as-is", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.dumpField("hello")).toBe("hello");
      expect(ctx.dumpField(42)).toBe(42);
      expect(ctx.dumpField(true)).toBe(true);
    });

    it("should serialize arrays recursively", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.dumpField([1, "two", null])).toEqual([1, "two", null]);
    });

    it("should serialize Property to its jsonSchema", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const prop = stringProperty({ title: "query" });
      expect(ctx.dumpField(prop)).toEqual(prop.jsonSchema);
    });

    it("should serialize plain objects preserving keys", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const result = ctx.dumpField({ a: 1, b: "two" });
      expect(result).toEqual({ a: 1, b: "two" });
    });

    it("should strip dangerous keys from plain objects", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      // Use JSON.parse to create own properties for __proto__ and constructor
      const input = JSON.parse(
        '{"safe":"ok","__proto__":{"evil":true},"constructor":{"bad":true},"prototype":{"x":1}}',
      );
      const result = ctx.dumpField(input) as Record<string, unknown>;
      expect(result["safe"]).toBe("ok");
      expect(Object.getOwnPropertyNames(result)).not.toContain("__proto__");
      expect(Object.getOwnPropertyNames(result)).not.toContain("constructor");
      expect(Object.getOwnPropertyNames(result)).not.toContain("prototype");
    });

    it("should throw when depth exceeds maximum", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(() => ctx.dumpField("value", 101)).toThrow(
        "Serialization nesting depth exceeds maximum",
      );
    });
  });

  describe("dumpModelObject", () => {
    it("should convert keys to snake_case by default", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const result = ctx.dumpModelObject(
        { maxTokens: 1024, temperature: 0.7 },
        false,
      );
      expect(result).toEqual({ max_tokens: 1024, temperature: 0.7 });
    });

    it("should keep camelCase keys when camelCase mode is enabled", () => {
      const ctx = new SerializationContext(
        makeBuiltinPlugins(),
        undefined,
        undefined,
        undefined,
        true,
      );
      const result = ctx.dumpModelObject(
        { maxTokens: 1024, temperature: 0.7 },
        false,
      );
      expect(result).toEqual({ maxTokens: 1024, temperature: 0.7 });
    });

    it("should exclude null values when excludeNulls is true", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const result = ctx.dumpModelObject(
        { maxTokens: 1024, temperature: null, topP: undefined },
        true,
      );
      expect(result).toEqual({ max_tokens: 1024 });
    });

    it("should include null values when excludeNulls is false", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const result = ctx.dumpModelObject(
        { maxTokens: 1024, temperature: null },
        false,
      );
      expect(result).toEqual({ max_tokens: 1024, temperature: null });
    });

    it("should strip dangerous keys", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const input = JSON.parse(
        '{"maxTokens": 100, "__proto__": {"evil": true}, "constructor": {"bad": true}}',
      );
      const result = ctx.dumpModelObject(input, false);
      expect(Object.getOwnPropertyNames(result)).not.toContain("__proto__");
      expect(Object.getOwnPropertyNames(result)).not.toContain("constructor");
      expect(result["max_tokens"]).toBe(100);
    });
  });

  describe("toSerializedFieldName", () => {
    it("should convert camelCase to snake_case by default", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.toSerializedFieldName("systemPrompt")).toBe("system_prompt");
      expect(ctx.toSerializedFieldName("llmConfig")).toBe("llm_config");
    });

    it("should keep camelCase when camelCase mode is enabled", () => {
      const ctx = new SerializationContext(
        makeBuiltinPlugins(),
        undefined,
        undefined,
        undefined,
        true,
      );
      expect(ctx.toSerializedFieldName("systemPrompt")).toBe("systemPrompt");
    });

    it("should never transform reserved fields", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.toSerializedFieldName("$component_ref")).toBe(
        "$component_ref",
      );
      expect(ctx.toSerializedFieldName("component_type")).toBe(
        "component_type",
      );
      expect(ctx.toSerializedFieldName("agentspec_version")).toBe(
        "agentspec_version",
      );
    });
  });

  describe("isFieldVersionGated", () => {
    it("should return false for unknown component types", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.isFieldVersionGated("UnknownType", "someField")).toBe(false);
    });

    it("should return false for non-gated fields", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.isFieldVersionGated("Agent", "name")).toBe(false);
    });

    it("should return true for _self version gate at old version", () => {
      // BuiltinTool has _self: V25_4_2, so at an earlier version all fields are gated
      const ctx = new SerializationContext(
        makeBuiltinPlugins(),
        AgentSpecVersion.V25_4_1,
      );
      expect(ctx.isFieldVersionGated("BuiltinTool", "toolType")).toBe(true);
    });

    it("should return false for _self version gate at current version", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.isFieldVersionGated("BuiltinTool", "toolType")).toBe(false);
    });

    it("should return true for field-level version gate at old version", () => {
      const ctx = new SerializationContext(
        makeBuiltinPlugins(),
        AgentSpecVersion.V25_4_1,
      );
      expect(ctx.isFieldVersionGated("Agent", "toolboxes")).toBe(true);
    });
  });

  describe("isFieldSensitive", () => {
    it("should return true for sensitive fields", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.isFieldSensitive("OpenAiCompatibleConfig", "apiKey")).toBe(
        true,
      );
    });

    it("should return false for non-sensitive fields", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.isFieldSensitive("OpenAiCompatibleConfig", "modelId")).toBe(
        false,
      );
    });
  });

  describe("dumpComponentToDict", () => {
    it("should throw for unknown component type with no plugin", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      // Create a fake component-like object with an unknown type
      const fakeComponent = {
        componentType: "UnknownCustomType",
        id: "550e8400-e29b-41d4-a716-446655440000",
        name: "fake",
      };
      // dumpField detects it as a component (has componentType, id, name)
      // and calls dumpComponentToDict, which should fail
      expect(() => ctx.dumpField(fakeComponent)).toThrow(
        'No plugin to serialize component type "UnknownCustomType"',
      );
    });
  });

  describe("makeOrderedDict", () => {
    it("should order priority keys first", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const result = ctx.makeOrderedDict({
        tools: [],
        name: "test",
        component_type: "Agent",
        id: "abc",
      }) as Record<string, unknown>;
      const keys = Object.keys(result);
      expect(keys[0]).toBe("component_type");
      expect(keys[1]).toBe("id");
      expect(keys[2]).toBe("name");
    });

    it("should handle arrays by recursing into items", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const result = ctx.makeOrderedDict([
        { name: "first", component_type: "X" },
      ]) as Record<string, unknown>[];
      const keys = Object.keys(result[0]!);
      expect(keys[0]).toBe("component_type");
      expect(keys[1]).toBe("name");
    });

    it("should return primitives as-is", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      expect(ctx.makeOrderedDict("hello")).toBe("hello");
      expect(ctx.makeOrderedDict(42)).toBe(42);
      expect(ctx.makeOrderedDict(null)).toBeNull();
    });

    it("should bail out at max depth", () => {
      const ctx = new SerializationContext(makeBuiltinPlugins());
      const deepObj = { name: "test" };
      const result = ctx.makeOrderedDict(deepObj, 101);
      expect(result).toBe(deepObj);
    });
  });
});

describe("AgentSpecSerializer camelCase mode", () => {
  it("should serialize with camelCase keys when option is set", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, { camelCase: true }) as string;
    const dict = JSON.parse(json);
    expect("systemPrompt" in dict).toBe(true);
    expect("system_prompt" in dict).toBe(false);
    expect("llmConfig" in dict).toBe(true);
    expect("llm_config" in dict).toBe(false);
  });

  it("should serialize YAML with camelCase keys", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const yaml = serializer.toYaml(agent, { camelCase: true }) as string;
    expect(yaml).toContain("systemPrompt:");
    expect(yaml).not.toContain("system_prompt:");
  });

  it("should use componentType key instead of component_type in camelCase mode", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, { camelCase: true }) as string;
    const dict = JSON.parse(json);
    expect("componentType" in dict).toBe(true);
    expect("component_type" in dict).toBe(false);
    expect(dict["componentType"]).toBe("Agent");
  });

  it("should use agentspecVersion key instead of agentspec_version in camelCase mode", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, { camelCase: true }) as string;
    const dict = JSON.parse(json);
    expect("agentspecVersion" in dict).toBe(true);
    expect("agentspec_version" in dict).toBe(false);
    expect(dict["agentspecVersion"]).toBe(CURRENT_VERSION);
  });

  it("should use componentType on nested components in camelCase mode", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, { camelCase: true }) as string;
    const dict = JSON.parse(json);
    const llmDict = dict["llmConfig"] as Record<string, unknown>;
    expect("componentType" in llmDict).toBe(true);
    expect("component_type" in llmDict).toBe(false);
    expect(llmDict["componentType"]).toBe("OpenAiCompatibleConfig");
  });

  it("should order componentType and agentspecVersion first in camelCase mode", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "test-agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
    });
    const json = serializer.toJson(agent, { camelCase: true }) as string;
    const dict = JSON.parse(json);
    const keys = Object.keys(dict);
    expect(keys[0]).toBe("componentType");
    expect(keys[1]).toBe("agentspecVersion");
    expect(keys[2]).toBe("id");
    expect(keys[3]).toBe("name");
  });
});

describe("AgentSpecSerializer version gating", () => {
  it("should exclude BuiltinTool fields when serializing at older version", () => {
    const serializer = new AgentSpecSerializer();
    const agent = createAgent({
      name: "agent",
      llmConfig: makeLlmConfig(),
      systemPrompt: "Hello",
      tools: [
        createBuiltinTool({ name: "bt", toolType: "code_execution" }),
      ],
    });
    const json = serializer.toJson(agent, {
      agentspecVersion: AgentSpecVersion.V25_4_1,
    }) as string;
    const dict = JSON.parse(json);
    // BuiltinTool has _self gate at V25_4_2, so its fields should be
    // version-gated (excluded) when serializing at V25_4_1
    const tool = dict["tools"][0];
    // component_type is added unconditionally outside the gating logic
    expect(tool["component_type"]).toBe("BuiltinTool");
    // tool_type should be excluded by the _self gate
    expect(tool["tool_type"]).toBeUndefined();
  });
});

describe("camelToSnake edge cases", () => {
  it("should handle abbreviation patterns like mTLS", () => {
    expect(camelToSnake("mTLS")).toBe("m_tls");
  });

  it("should handle consecutive uppercase like SSE", () => {
    expect(camelToSnake("SSETransport")).toBe("sse_transport");
  });

  it("should handle empty string", () => {
    expect(camelToSnake("")).toBe("");
  });
});

describe("snakeToCamel edge cases", () => {
  it("should handle numeric segments", () => {
    expect(snakeToCamel("version_2_name")).toBe("version2Name");
  });

  it("should handle empty string", () => {
    expect(snakeToCamel("")).toBe("");
  });
});
