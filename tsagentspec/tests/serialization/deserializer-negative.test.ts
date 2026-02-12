import { describe, it, expect } from "vitest";
import { AgentSpecDeserializer } from "../../src/index.js";

describe("AgentSpecDeserializer negative tests", () => {
  const deserializer = new AgentSpecDeserializer();

  describe("missing component_type", () => {
    it("should throw for dict without component_type", () => {
      expect(() =>
        deserializer.fromDict({
          name: "test",
          id: "00000000-0000-0000-0000-000000000001",
        }),
      ).toThrow("missing 'component_type'");
    });

    it("should throw for JSON without component_type", () => {
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
        deserializer.fromDict({
          component_type: "NonExistentType",
          name: "test",
          id: "00000000-0000-0000-0000-000000000001",
        }),
      ).toThrow('No plugin to deserialize component type "NonExistentType"');
    });

    it("should throw when component_type is not a string", () => {
      expect(() =>
        deserializer.fromDict({
          component_type: 42,
          name: "test",
        }),
      ).toThrow("component_type is not a string");
    });
  });

  describe("missing references", () => {
    it("should throw for unresolved $component_ref", () => {
      expect(() =>
        deserializer.fromDict({
          component_type: "Agent",
          name: "test",
          id: "00000000-0000-0000-0000-000000000001",
          system_prompt: "hello",
          llm_config: {
            $component_ref: "00000000-0000-0000-0000-999999999999",
          },
        }),
      ).toThrow("Missing component references");
    });
  });

  describe("disaggregated component errors", () => {
    it("should throw when loading only $referenced_components without flag", () => {
      expect(() =>
        deserializer.fromDict({
          $referenced_components: {
            "id-1": {
              component_type: "Agent",
              name: "test",
            },
          },
        }),
      ).toThrow("Cannot deserialize: content only has '$referenced_components'");
    });

    it("should throw when importOnly but no $referenced_components", () => {
      expect(() =>
        deserializer.fromDict(
          {
            component_type: "Agent",
            name: "test",
          },
          { importOnlyReferencedComponents: true },
        ),
      ).toThrow("should have '$referenced_components' field");
    });

    it("should throw when importOnly but has extra fields", () => {
      expect(() =>
        deserializer.fromDict(
          {
            component_type: "Agent",
            name: "test",
            $referenced_components: {},
          },
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
