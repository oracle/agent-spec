import { describe, it, expect } from "vitest";
import {
  AgentSpecDeserializer,
  createServerTool,
  CURRENT_VERSION,
} from "../../src/index.js";
import { DeserializationContext } from "../../src/serialization/deserialization-context.js";
import { BuiltinsComponentDeserializationPlugin } from "../../src/serialization/builtin-deserialization-plugin.js";
import type { ComponentBase } from "../../src/component.js";

function makeBuiltinPlugins() {
  return [new BuiltinsComponentDeserializationPlugin()];
}

describe("DeserializationContext", () => {
  describe("constructor", () => {
    it("should throw on duplicate plugin component types", () => {
      expect(
        () =>
          new DeserializationContext([
            new BuiltinsComponentDeserializationPlugin(),
            new BuiltinsComponentDeserializationPlugin(),
          ]),
      ).toThrow("Multiple plugins handle deserialization");
    });

    it("should default camelCase to false", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(ctx.camelCase).toBe(false);
    });

    it("should accept camelCase option", () => {
      const ctx = new DeserializationContext(
        makeBuiltinPlugins(),
        undefined,
        true,
      );
      expect(ctx.camelCase).toBe(true);
    });
  });

  describe("getComponentType", () => {
    it("should read component_type in snake_case mode", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(
        ctx.getComponentType({ component_type: "Agent" }),
      ).toBe("Agent");
    });

    it("should read componentType in camelCase mode", () => {
      const ctx = new DeserializationContext(
        makeBuiltinPlugins(),
        undefined,
        true,
      );
      expect(
        ctx.getComponentType({ componentType: "Agent" }),
      ).toBe("Agent");
    });

    it("should throw for missing component_type", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(() => ctx.getComponentType({ name: "test" })).toThrow(
        "missing 'component_type'",
      );
    });

    it("should throw for non-string component_type", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(() =>
        ctx.getComponentType({ component_type: 42 }),
      ).toThrow("component_type is not a string");
    });
  });

  describe("loadField", () => {
    it("should return undefined for null and undefined", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(ctx.loadField(null)).toBeUndefined();
      expect(ctx.loadField(undefined)).toBeUndefined();
    });

    it("should return primitives as-is", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(ctx.loadField("hello")).toBe("hello");
      expect(ctx.loadField(42)).toBe(42);
      expect(ctx.loadField(true)).toBe(true);
    });

    it("should recursively load arrays", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(ctx.loadField([1, "two", null])).toEqual([1, "two", undefined]);
    });

    it("should load plain objects recursively, stripping dangerous keys", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const input = JSON.parse(
        '{"safe":"ok","__proto__":{"evil":true},"nested":{"value":1}}',
      );
      const result = ctx.loadField(input) as Record<string, unknown>;
      expect(result["safe"]).toBe("ok");
      expect(Object.getOwnPropertyNames(result)).not.toContain("__proto__");
      expect((result["nested"] as Record<string, unknown>)["value"]).toBe(1);
    });

    it("should resolve $component_ref references", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const refId = "550e8400-e29b-41d4-a716-446655440000";
      ctx.referencedComponents.set(refId, {
        component_type: "OpenAiCompatibleConfig",
        name: "llm",
        id: refId,
        url: "http://localhost",
        model_id: "gpt-4",
      });
      const result = ctx.loadField({ $component_ref: refId }) as Record<
        string,
        unknown
      >;
      expect(result["componentType"]).toBe("OpenAiCompatibleConfig");
    });

    it("should load nested component dicts", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const result = ctx.loadField({
        component_type: "ServerTool",
        name: "my-tool",
        id: "550e8400-e29b-41d4-a716-446655440001",
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
    });

    it("should detect nested components with componentType key in camelCase mode", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins(), undefined, true);
      const result = ctx.loadField({
        componentType: "ServerTool",
        name: "my-tool",
        id: "550e8400-e29b-41d4-a716-446655440001",
        metadata: {},
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
      expect(result["name"]).toBe("my-tool");
    });
  });

  describe("loadReference", () => {
    it("should throw for missing reference", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(() =>
        ctx.loadReference("00000000-0000-0000-0000-999999999999"),
      ).toThrow("Missing reference for ID");
    });

    it("should cache loaded references", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const refId = "550e8400-e29b-41d4-a716-446655440000";
      ctx.referencedComponents.set(refId, {
        component_type: "ServerTool",
        name: "cached-tool",
        id: refId,
      });
      const first = ctx.loadReference(refId);
      const second = ctx.loadReference(refId);
      expect(first).toBe(second);
    });
  });

  describe("loadComponentFromDict", () => {
    it("should throw for duplicate $referenced_components IDs", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const refId = "550e8400-e29b-41d4-a716-446655440000";
      // Pre-populate a reference
      ctx.referencedComponents.set(refId, {
        component_type: "ServerTool",
        name: "tool",
        id: refId,
      });
      // Try to load a dict that defines the same ref again
      expect(() =>
        ctx.loadComponentFromDict({
          component_type: "Agent",
          name: "agent",
          id: "550e8400-e29b-41d4-a716-446655440001",
          system_prompt: "hi",
          llm_config: {
            component_type: "OpenAiCompatibleConfig",
            name: "llm",
            id: "550e8400-e29b-41d4-a716-446655440002",
            url: "http://localhost",
            model_id: "gpt-4",
          },
          $referenced_components: {
            [refId]: {
              component_type: "ServerTool",
              name: "duplicate",
              id: refId,
            },
          },
        }),
      ).toThrow("appears multiple times");
    });

    it("should resolve $component_ref at top level", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const refId = "550e8400-e29b-41d4-a716-446655440000";
      ctx.referencedComponents.set(refId, {
        component_type: "ServerTool",
        name: "ref-tool",
        id: refId,
      });
      const result = ctx.loadComponentFromDict({
        $component_ref: refId,
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
      expect(result["name"]).toBe("ref-tool");
    });

    it("should throw for unknown component type", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(() =>
        ctx.loadComponentFromDict({
          component_type: "NonExistentType",
          name: "test",
          id: "550e8400-e29b-41d4-a716-446655440000",
        }),
      ).toThrow('No plugin to deserialize component type "NonExistentType"');
    });
  });

  describe("loadComponentRegistry", () => {
    it("should load external registry into loadedReferences", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const tool = createServerTool({ name: "ext-tool" });
      const registry = new Map<string, ComponentBase>();
      registry.set(tool.id, tool);
      ctx.loadComponentRegistry(registry);
      // Now the tool should be loadable as a reference
      const loaded = ctx.loadReference(tool.id);
      expect(loaded["name"]).toBe("ext-tool");
    });

    it("should handle undefined registry gracefully", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      expect(() => ctx.loadComponentRegistry(undefined)).not.toThrow();
    });
  });

  describe("loadConfigDict", () => {
    it("should handle prerelease agentspec version", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const result = ctx.loadConfigDict({
        agentspec_version: "25.4.0",
        component_type: "ServerTool",
        name: "tool",
        id: "550e8400-e29b-41d4-a716-446655440000",
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
      // Prerelease version 25.4.0 should be mapped to 25.4.1
      expect(ctx.agentspecVersion).toBe("25.4.1");
    });

    it("should handle legacy air_version field", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      const result = ctx.loadConfigDict({
        air_version: "25.4.1",
        component_type: "ServerTool",
        name: "tool",
        id: "550e8400-e29b-41d4-a716-446655440000",
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
      expect(ctx.agentspecVersion).toBe("25.4.1");
    });

    it("should default to CURRENT_VERSION when no version field", () => {
      const ctx = new DeserializationContext(makeBuiltinPlugins());
      ctx.loadConfigDict({
        component_type: "ServerTool",
        name: "tool",
        id: "550e8400-e29b-41d4-a716-446655440000",
      });
      expect(ctx.agentspecVersion).toBe(CURRENT_VERSION);
    });

    it("should read agentspecVersion key in camelCase mode", () => {
      const ctx = new DeserializationContext(
        makeBuiltinPlugins(),
        undefined,
        true,
      );
      const result = ctx.loadConfigDict({
        agentspecVersion: CURRENT_VERSION,
        componentType: "ServerTool",
        name: "tool",
        id: "550e8400-e29b-41d4-a716-446655440000",
      }) as Record<string, unknown>;
      expect(result["componentType"]).toBe("ServerTool");
      expect(ctx.agentspecVersion).toBe(CURRENT_VERSION);
    });
  });
});

describe("BuiltinsComponentDeserializationPlugin edge cases", () => {
  it("should reject property items without title in inputs array", () => {
    // Items without "title" are passed through as-is by the plugin (not
    // deserialized as Property), but the stricter PropertySchema now
    // rejects them at the factory level since title is required.
    const ctx = new DeserializationContext(makeBuiltinPlugins());
    const plugin = new BuiltinsComponentDeserializationPlugin();
    const data = {
      component_type: "ServerTool",
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "tool",
      metadata: {},
      inputs: [{ type: "string", description: "no title here" }],
      outputs: [],
    };
    expect(() => plugin.deserialize(data, ctx)).toThrow();
  });

  it("should preserve camelCase model object keys in camelCase mode", () => {
    // Line 147: when camelCase mode is enabled, defaultGenerationParameters
    // should be passed through without key conversion
    const deserializer = new AgentSpecDeserializer();
    const input = JSON.stringify({
      agentspecVersion: CURRENT_VERSION,
      componentType: "OpenAiCompatibleConfig",
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "llm",
      url: "http://localhost",
      modelId: "gpt-4",
      metadata: {},
      defaultGenerationParameters: { maxTokens: 512, temperature: 0.7 },
    });
    const result = deserializer.fromJson(input, {
      camelCase: true,
    }) as Record<string, unknown>;
    const genParams = result["defaultGenerationParameters"] as Record<
      string,
      unknown
    >;
    expect(genParams["maxTokens"]).toBe(512);
    expect(genParams["temperature"]).toBe(0.7);
  });
});

describe("camelCase deserialization from camelCase input", () => {
  it("should deserialize agent JSON with all camelCase keys", () => {
    const deserializer = new AgentSpecDeserializer();
    const input = JSON.stringify({
      agentspecVersion: CURRENT_VERSION,
      componentType: "Agent",
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "camel-agent",
      systemPrompt: "Hello {{topic}}",
      inputs: [{ title: "topic", type: "string" }],
      outputs: [],
      metadata: {},
      llmConfig: {
        componentType: "OpenAiCompatibleConfig",
        id: "550e8400-e29b-41d4-a716-446655440001",
        name: "llm",
        url: "http://localhost",
        modelId: "gpt-4",
        metadata: {},
        defaultGenerationParameters: { maxTokens: 512, temperature: 0.5 },
      },
      tools: [
        {
          componentType: "ServerTool",
          id: "550e8400-e29b-41d4-a716-446655440002",
          name: "tool",
          metadata: {},
          inputs: [{ title: "q", type: "string" }],
          outputs: [],
        },
      ],
    });
    const result = deserializer.fromJson(input, {
      camelCase: true,
    }) as Record<string, unknown>;
    expect(result["componentType"]).toBe("Agent");
    expect(result["name"]).toBe("camel-agent");
    expect(result["systemPrompt"]).toBe("Hello {{topic}}");
    const llm = result["llmConfig"] as Record<string, unknown>;
    expect(llm["componentType"]).toBe("OpenAiCompatibleConfig");
    expect(llm["modelId"]).toBe("gpt-4");
    const genParams = llm["defaultGenerationParameters"] as Record<
      string,
      unknown
    >;
    expect(genParams["maxTokens"]).toBe(512);
  });

  it("should deserialize agent YAML with camelCase keys", () => {
    const deserializer = new AgentSpecDeserializer();
    const yaml = `
agentspecVersion: "${CURRENT_VERSION}"
componentType: Agent
id: "550e8400-e29b-41d4-a716-446655440000"
name: yaml-camel
systemPrompt: Hello
metadata: {}
inputs: []
outputs: []
llmConfig:
  componentType: OpenAiCompatibleConfig
  id: "550e8400-e29b-41d4-a716-446655440001"
  name: llm
  url: "http://localhost"
  modelId: gpt-4
  metadata: {}
`;
    const result = deserializer.fromYaml(yaml, {
      camelCase: true,
    }) as Record<string, unknown>;
    expect(result["componentType"]).toBe("Agent");
    expect(result["name"]).toBe("yaml-camel");
  });
});
