import { describe, it, expect } from "vitest";
import { AgentSpecDeserializer } from "../../src/index.js";

describe("AgentSpecDeserializer negative tests", () => {
  const deserializer = new AgentSpecDeserializer();

  describe("missing component_type", () => {
    it("should throw for JSON without component_type", () => {
      expect(() =>
        deserializer.fromJson(JSON.stringify({
          name: "test",
          id: "00000000-0000-0000-0000-000000000001",
        })),
      ).toThrow("missing 'component_type'");
    });

    it("should throw for JSON string without component_type", () => {
      expect(() =>
        deserializer.fromJson(JSON.stringify({ name: "test" })),
      ).toThrow("missing 'component_type'");
    });

    it("should throw for YAML without component_type", () => {
      expect(() => deserializer.fromYaml("name: test\n")).toThrow(
        "missing 'component_type'",
      );
    });
  });

  describe("invalid component_type", () => {
    it("should throw for unknown component_type", () => {
      expect(() =>
        deserializer.fromJson(JSON.stringify({
          component_type: "NonExistentType",
          name: "test",
          id: "00000000-0000-0000-0000-000000000001",
        })),
      ).toThrow('No plugin to deserialize component type "NonExistentType"');
    });

    it("should throw when component_type is not a string", () => {
      expect(() =>
        deserializer.fromJson(JSON.stringify({
          component_type: 42,
          name: "test",
        })),
      ).toThrow("component_type is not a string");
    });
  });

  describe("missing references", () => {
    it("should throw for unresolved $component_ref", () => {
      expect(() =>
        deserializer.fromJson(JSON.stringify({
          component_type: "Agent",
          name: "test",
          id: "00000000-0000-0000-0000-000000000001",
          system_prompt: "hello",
          llm_config: {
            $component_ref: "00000000-0000-0000-0000-999999999999",
          },
        })),
      ).toThrow("Missing component references");
    });
  });

  describe("disaggregated component errors", () => {
    it("should throw when loading only $referenced_components without flag", () => {
      expect(() =>
        deserializer.fromJson(JSON.stringify({
          $referenced_components: {
            "id-1": {
              component_type: "Agent",
              name: "test",
            },
          },
        })),
      ).toThrow("Cannot deserialize: content only has '$referenced_components'");
    });

    it("should throw when importOnly but no $referenced_components", () => {
      expect(() =>
        deserializer.fromJson(
          JSON.stringify({
            component_type: "Agent",
            name: "test",
          }),
          { importOnlyReferencedComponents: true },
        ),
      ).toThrow("should have '$referenced_components' field");
    });

    it("should throw when importOnly but has extra fields", () => {
      expect(() =>
        deserializer.fromJson(
          JSON.stringify({
            component_type: "Agent",
            name: "test",
            $referenced_components: {},
          }),
          { importOnlyReferencedComponents: true },
        ),
      ).toThrow("should only have '$referenced_components' field");
    });
  });

  describe("input size limits", () => {
    it("should throw for JSON exceeding max input size", () => {
      const smallDeserializer = new AgentSpecDeserializer({
        maxInputSize: 100,
      });
      const largeJson = JSON.stringify({
        component_type: "Agent",
        name: "test",
        system_prompt: "x".repeat(200),
      });
      expect(() => smallDeserializer.fromJson(largeJson)).toThrow(
        "exceeds maximum",
      );
    });

    it("should throw for YAML exceeding max input size", () => {
      const smallDeserializer = new AgentSpecDeserializer({
        maxInputSize: 100,
      });
      const largeYaml = `component_type: Agent\nname: test\nsystem_prompt: ${"x".repeat(200)}`;
      expect(() => smallDeserializer.fromYaml(largeYaml)).toThrow(
        "exceeds maximum",
      );
    });
  });

  describe("depth limits", () => {
    it("should throw for deeply nested objects", () => {
      const shallowDeserializer = new AgentSpecDeserializer({
        maxDepth: 5,
      });
      // Build a deeply nested object
      let nested: Record<string, unknown> = { value: "leaf" };
      for (let i = 0; i < 10; i++) {
        nested = { inner: nested };
      }
      nested["component_type"] = "Agent";
      nested["name"] = "test";

      expect(() =>
        shallowDeserializer.fromJson(JSON.stringify(nested)),
      ).toThrow("nesting depth exceeds maximum");
    });

    it("should accept objects within depth limit", () => {
      const deserializer2 = new AgentSpecDeserializer({ maxDepth: 50 });
      // A normal agent JSON should not exceed depth 50
      const json = JSON.stringify({
        component_type: "Agent",
        name: "test-agent",
        id: "00000000-0000-0000-0000-000000000001",
        system_prompt: "Hello",
        llm_config: {
          component_type: "OpenAiCompatibleConfig",
          name: "llm",
          id: "00000000-0000-0000-0000-000000000002",
          url: "http://localhost",
          model_id: "gpt-4",
        },
      });
      expect(() => deserializer2.fromJson(json)).not.toThrow(
        "nesting depth exceeds maximum",
      );
    });
  });

  describe("prototype pollution prevention", () => {
    // Note: __proto__ in object literals is a prototype setter, not an own property,
    // so JSON.stringify loses it. We construct JSON via string manipulation to test
    // that __proto__ keys in untrusted input are properly stripped.

    it("should strip __proto__ keys during deserialization", () => {
      const baseJson = JSON.stringify({
        component_type: "Agent",
        name: "test-agent",
        id: "00000000-0000-0000-0000-000000000001",
        system_prompt: "hello",
        llm_config: {
          component_type: "OpenAiCompatibleConfig",
          name: "llm",
          id: "00000000-0000-0000-0000-000000000002",
          url: "http://localhost",
          model_id: "gpt-4",
        },
        metadata: { safe: "value" },
      });
      // Inject __proto__ into metadata via string manipulation
      const json = baseJson.replace(
        '"safe":"value"',
        '"safe":"value","__proto__":{"isAdmin":true}',
      );
      const result = deserializer.fromJson(json) as Record<string, unknown>;
      const meta = result["metadata"] as Record<string, unknown>;
      expect(meta["safe"]).toBe("value");
      // Must use getOwnPropertyNames — meta["__proto__"] returns the inherited prototype
      expect(Object.getOwnPropertyNames(meta)).not.toContain("__proto__");
      expect(({} as Record<string, unknown>)["isAdmin"]).toBeUndefined();
    });

    it("should strip constructor and prototype keys during deserialization", () => {
      // constructor/prototype in object literals DO create own properties (unlike __proto__)
      const json = JSON.stringify({
        component_type: "Agent",
        name: "test-agent",
        id: "00000000-0000-0000-0000-000000000001",
        system_prompt: "hello",
        llm_config: {
          component_type: "OpenAiCompatibleConfig",
          name: "llm",
          id: "00000000-0000-0000-0000-000000000002",
          url: "http://localhost",
          model_id: "gpt-4",
        },
        metadata: {
          constructor: { prototype: { polluted: true } },
          prototype: { evil: true },
          safe: "value",
        },
      });
      const result = deserializer.fromJson(json) as Record<string, unknown>;
      const meta = result["metadata"] as Record<string, unknown>;
      expect(meta["safe"]).toBe("value");
      // Must use getOwnPropertyNames — meta["constructor"] returns inherited Object constructor
      expect(Object.getOwnPropertyNames(meta)).not.toContain("constructor");
      expect(Object.getOwnPropertyNames(meta)).not.toContain("prototype");
    });

    it("should strip dangerous keys in nested objects", () => {
      const baseJson = JSON.stringify({
        component_type: "Agent",
        name: "test-agent",
        id: "00000000-0000-0000-0000-000000000001",
        system_prompt: "hello",
        llm_config: {
          component_type: "OpenAiCompatibleConfig",
          name: "llm",
          id: "00000000-0000-0000-0000-000000000002",
          url: "http://localhost",
          model_id: "gpt-4",
        },
        metadata: {
          nested: { safe: "ok", prototype: { evil: true } },
        },
      });
      // Also inject __proto__ into the nested object
      const json = baseJson.replace(
        '"safe":"ok"',
        '"safe":"ok","__proto__":{"isAdmin":true}',
      );
      const result = deserializer.fromJson(json) as Record<string, unknown>;
      const meta = result["metadata"] as Record<string, unknown>;
      const nested = meta["nested"] as Record<string, unknown>;
      expect(nested["safe"]).toBe("ok");
      expect(Object.getOwnPropertyNames(nested)).not.toContain("__proto__");
      expect(Object.getOwnPropertyNames(nested)).not.toContain("prototype");
    });
  });

  describe("circular reference detection", () => {
    it("should throw for self-referencing $component_ref", () => {
      const refId = "00000000-0000-0000-0000-000000000099";
      const json = JSON.stringify({
        component_type: "Agent",
        name: "test-agent",
        id: "00000000-0000-0000-0000-000000000001",
        system_prompt: "hello",
        llm_config: { $component_ref: refId },
        $referenced_components: {
          [refId]: {
            component_type: "Agent",
            name: "circular",
            id: refId,
            system_prompt: "loop",
            llm_config: { $component_ref: refId },
          },
        },
      });
      expect(() => deserializer.fromJson(json)).toThrow(
        "Circular dependency",
      );
    });
  });

  describe("backwards-compatible constructor", () => {
    it("should accept no arguments", () => {
      const d = new AgentSpecDeserializer();
      expect(d).toBeDefined();
    });

    it("should accept plugin array (legacy signature)", () => {
      const d = new AgentSpecDeserializer([]);
      expect(d).toBeDefined();
    });

    it("should accept options object (new signature)", () => {
      const d = new AgentSpecDeserializer({
        plugins: [],
        maxInputSize: 5000,
        maxDepth: 50,
      });
      expect(d).toBeDefined();
    });
  });
});
